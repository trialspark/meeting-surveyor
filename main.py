from flask import Flask, Response
from slackeventsapi import SlackEventAdapter
import os
from src.meeting_surveyor import MeetingSurveyor

import json


app = Flask(__name__)
SLACK_SIGNING_SECRET = os.environ["SLACK_SIGNING_SECRET"]
meeting_surveyor = MeetingSurveyor()


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
    text = event_data['event']['text'].lower().strip()

    fixed_user_commands = {
        'opt out': meeting_surveyor.opt_out,
        'opt in': meeting_surveyor.opt_in
    }

    if text.strip() in fixed_user_commands:
        fixed_user_commands[text](event_data['event']['user'])

    # TODO: Check if in thread and if so find corresponding meeting, submit rating if appropriate.
    return Response(status=200)


if __name__ == '__main__':
    app.run(port=3000)