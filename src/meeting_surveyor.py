from slack_sdk import WebClient
import os
from typing import Any
from src.calendar_api_wrapper import CalendarAPIWrapper
from db.database import get_session, User, Survey, Event
import logging

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
        event_details = self.calendar.get_event_attributes(event_id)
        organizer_email = event_details['organizer']['email']
        # Query users model to get organizer details and channel
        # self.client.chat_postMessage()
        raise NotImplementedError()

    def send_survey(self, event_id) -> None:
        """ Send a survey to the attendees if standards/requirements met, otherwise updating is_surveyable flag. """
        event_details = self.calendar.get_event_attributes(event_id)

        organizer_email = event_details['organizer']['email']
        attendee_emails = [a['email'].lower() for a in event_details if a['email'] != organizer_email]
        surveyable_attendees = self.session.query(User).filter(
            User.email_address.in_(attendee_emails)
        ).all()

        if len(surveyable_attendees) < MIN_SURVEYABLE:
            Event.update().where(Event.id == event_id).values(should_send_survey=False)
            return

        for attendee in surveyable_attendees:
            if attendee.has_opted_out:
                continue

            if attendee.oauth_token:
                # TODO: Send survey
                pass
            else:
                # TODO: Send survey with link to oauth to opt-in to surveys on future attended emails.
                pass

        Event.update().where(Event.id == event_id).values(survey_sent=True)

    def send_oauth_message(self, email: str, event_name: str):
        """ Send the introductory message with Oauth, and add an entry for this user to the DB """
        users = self.client.users_list()

    def oauth_followup(self):
        """
        The OAuth process should include some kind of a redirect or side-effect which will then prompt the user to
        complete the survey that they were originally meant to be completing when the oauth message was sent
        """
        raise NotImplementedError()

    def opt_out(self, user_slack_id: str):
        """ Set the user's opted-out state to True"""
        raise NotImplementedError()

    def opt_in(self, user_slack_id: str):
        """ If a user opts back into the messages set their opted-out state to False """
        raise NotImplementedError()

    def update_slack_users(self):
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

