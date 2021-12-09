from slack_sdk import WebClient
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
import os
from typing import Any
from src.calendar_api_wrapper import CalendarAPIWrapper


class MeetingSurveyor(object):
    """
    Class which handles sending and receiving surveys, messages to the users all flow through this point
    """

    def __init__(self):
        # Client used in sending messages.
        engine = create_engine('sqlite:///db/meeting_surveyor.db')
        self.session = sessionmaker(bind=engine)()
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

    def send_survey(self, event_id):
        """ Send a survey to the attendees """
        event_details = self.calendar.get_event_attributes(event_id)
        for attendee in event_details['attendees']:
            if attendee['email'] != event_details['organizer']['email']:
                """
                If the user already exists in the DB, send the survey 

                If the user has opted out, do nothing.

                If user has not yet gotten their oauth in place, send link
                """
                pass

        raise NotImplementedError()

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
