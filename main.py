from authlib.integrations.flask_client import OAuth
from flask import Flask, Response, url_for, session
from slackeventsapi import SlackEventAdapter
import os
from src.meeting_surveyor import MeetingSurveyor, SURVEY_RESPONSES

import json


app = Flask(__name__)
app.secret_key = os.getenv("APP_SECRET_KEY")
SLACK_SIGNING_SECRET = os.environ["SLACK_SIGNING_SECRET"]
meeting_surveyor = MeetingSurveyor()

# oAuth Setup
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    access_token_url='https://accounts.google.com/o/oauth2/token',
    access_token_params=None,
    authorize_url='https://accounts.google.com/o/oauth2/auth?access_type=offline',
    authorize_params=None,
    api_base_url='https://www.googleapis.com/oauth2/v1/',
    client_kwargs={'scope': 'email profile https://www.googleapis.com/auth/calendar.readonly'},
)
scope = [
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/calendar.readonly"
]

@app.route("/slack/events")
def event_hook(request):
    json_dict = json.loads(request.body.decode("utf-8"))
    if json_dict["token"] != os.environ['SLACK_VERIFICATION_TOKEN']:
        return {"status": 403}

    if "type" in json_dict:
        if json_dict["type"] == "url_verification":
            response_dict = {"challenge": json_dict["challenge"]}
            return response_dict
        return {"status": 500}
    return None


slack_events_adapter = SlackEventAdapter(
    SLACK_SIGNING_SECRET, "/slack/events", app
)


@slack_events_adapter.on("message")
def handle_message(event_data):
    if not event_data.get('event', {}).get('user'):
        return Response(status=200)

    text = event_data['event']['text'].lower().strip()

    fixed_user_commands = {
        'opt out': meeting_surveyor.opt_out,
        'opt in': meeting_surveyor.opt_in,
        'hello': meeting_surveyor.send_greeting,
        'hi': meeting_surveyor.send_greeting,
    }

    slack_id = event_data['event']['user']
    cleaned_text = ''.join(c for c in text.lower().strip() if c.isalpha())

    if cleaned_text in fixed_user_commands:
        fixed_user_commands[cleaned_text](slack_id)
    elif cleaned_text in SURVEY_RESPONSES:
        meeting_surveyor.handle_survey_submission(slack_id, cleaned_text)
    else:
        meeting_surveyor.send_error(slack_id, cleaned_text)

    return Response(status=200)


@app.route('/auth/google')
def handle_redirect():
    tokens = oauth.google.authorize_access_token()
    user_info = google.get('userinfo').json()
    meeting_surveyor.update_user(user_info, tokens)
    return 'Thank you! This page may now be closed.'


@app.route('/auth')
def login():
    google = oauth.create_client('google')  # create the google oauth client
    redirect_uri = url_for('handle_redirect', _external=True)
    return google.authorize_redirect(redirect_uri)


if __name__ == '__main__':
    app.run(port=3000)