from slack_sdk import WebClient
import datetime
import os
import logging
from typing import Any
from src.calendar_api_wrapper import CalendarAPIWrapper
from db.database import get_session, User, SurveyResponses, Event
from sqlalchemy import update
from src.helpers import get_user

# Minimum number of non-organizer trialspark employees in a meeting for a survey to be sent.
MIN_SURVEYABLE = 3


class MeetingSurveyor(object):
    """
    Class which handles sending and receiving surveys, messages to the users all flow through this point
    """

    def __init__(self):
        # Client used in sending messages.
        self.session = get_session()
        self.client = WebClient(token=os.environ["SLACK_OAUTH_TOKEN"])
        self.calendar = CalendarAPIWrapper()

    # Kinds/number of ratings preserved will be determined by output of survey?
    def handle_survey_submission(self, user_slack_id: str, event_id: str, ratings: Any):
        """ Store the rating(s) for a survey in the DB """
        raise NotImplementedError()

    def send_survey_results(self, event_id):
        """ Send survey results to the owner """
        # Query db to get averages for event, sent results to user.
        event_details = self.calendar.get_event(event_id)
        organizer_email = event_details['organizer']['email']
        # Query users model to get organizer details and channel
        # self.client.chat_postMessage()
        raise NotImplementedError()

    def send_survey(self, event_id) -> None:
        """ Send a survey to the attendees if standards/requirements met, otherwise updating is_surveyable flag. """
        event_details = self.calendar.get_event(event_id)

        organizer_email = event_details['organizer']['email']
        attendee_emails = [a['email'].lower() for a in event_details['attendees'] if a['email'] != organizer_email]
        surveyable_attendees = self.session.query(User).filter(
            User.email_address.in_(attendee_emails)
        ).all()

        if len(surveyable_attendees) < MIN_SURVEYABLE:
            update(Event).where(Event.id == event_id).values(should_send_survey=False)
            return

        survey_message = f"How useful/productive was the meeting \"{event_details['summary']}\"? " \
                         f"Response with a 1-5 below!"

        for attendee in surveyable_attendees:
            if attendee.has_opted_out:
                continue

            message = survey_message

            if not attendee.oauth_token:
                oauth_link = os.environ['HOST'] + '/auth'
                message += f"\n\n(By the way, if you want to include these surveys on all future meetings just sign up" \
                           f"here, or reply OPT OUT to opt out of future messages: {oauth_link})"

            self.client.chat_postMessage(
                channel=attendee.slack_id,
                text=survey_message
            )

        update(Event).where(Event.id == event_id).values(survey_sent=True)

    def send_oauth_message(self, email: str, event_name: str):
        """ Send the introductory message with Oauth, and add an entry for this user to the DB """
        users = self.client.users_list()

    def oauth_followup(self):
        """
        The OAuth process should include some kind of a redirect or side-effect which will then prompt the user to
        complete the survey that they were originally meant to be completing when the oauth message was sent
        """
        raise NotImplementedError()

    def opt_out(self, slack_id: str):
        """ Set the user's opted-out state to True"""
        user = self.session.query(User).filter_by(slack_id=slack_id).first()
        user.has_opted_out = True
        self.session.commit()
        self.client.chat_postMessage(
            channel=user.slack_id,
            text="You've successfully opted out of meeting surveys. If you every want to receive them again in the "
                 "future, just say OPT IN!"
        )

    def opt_in(self, slack_id: str):
        """ If a user opts back into the messages set their opted-out state to False """
        """ Set the user's opted-out state to True"""
        user = self.session.query(User).filter_by(slack_id=slack_id).first()
        user.has_opted_out = False
        self.session.commit()
        self.client.chat_postMessage(
            channel=user.slack_id,
            text="You've successfully opted back into meeting surveys! If you every want to stop getting them in the "
                 "future, just say OPT OUT."
        )

    def populate_slack_users(self):
        """
        An method to be executed periodically, gets slack users and adds them to the table so that they may
        receive invitations to surveys.
        """
        response = self.client.users_list()
        existing_ids = set(v[0] for v in self.session.query(User.slack_id))
        slack_team_members = [
            m for m in response.data['members']
            if not m['is_bot'] and not m['deleted'] and m.get('profile') and m['profile'].get('email')
               and m['id'] not in existing_ids
        ]

        if not slack_team_members:
            return

        new_users = []
        for m in slack_team_members:
            new_users.append(
                User(
                    slack_id=m['id'],
                    email_address=m['profile']['email'].lower(),
                )
            )

        self.session.bulk_save_objects(new_users)
        self.session.commit()

        logging.info(f"{len(new_users)} new slack users added to users table!")

    def update_user(self, user_info: dict, tokens: dict):
        user = self.session.query(User).where(User.email_address == user_info['email']).one_or_none()

        if user:
            if tokens.get('refresh_token'):
                user.refresh_token = tokens['refresh_token']
            self.session.commit()
        else:
            raise Exception("Attempted to update user who does not exist in the table. All users with slack accounts"
                            " are expected to exist in periodically updated table, this is an unforeseen state.")


    def send_greeting(self, user: User) -> None:
        """ Send a greeting to a user with a link to sign-up. """
        oauth_link = os.environ['HOST'] + '/auth'
        message = "**Hello!** I send out surveys about meeting value. You'll get a link if you or anyone in your" \
                  "meeting has opted-in to these surveys.\n\n"
        message += f"If you want to include these surveys on all your future meetings just sign up here, or " \
                   f"reply OPT OUT to opt out of future messages: {oauth_link}"
        self.client.chat_postMessage(
            channel=user.slack_id,
            text=message
        )


if __name__ == '__main__':
    ms = MeetingSurveyor()
    session = ms.session
    user = get_user(session, email_address='jklingelhofer@trialspark.com')
    ms.send_greeting(user)
