from collections import Counter
from slack_sdk import WebClient
import datetime
import os
import logging
from typing import Any
from src.calendar_api_wrapper import CalendarAPIWrapper
from db.database import get_session, User, SurveyResponse, Event
from sqlalchemy import update, and_
from typing import List
from src.helpers import get_user

# Minimum number of non-organizer trialspark employees in a meeting for a survey to be sent.
MIN_SURVEYABLE = 1 # TODO change to 3
DEMO = True

SURVEY_RESPONSES = ['yes', 'no', 'maybe']

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
    def handle_survey_submission(self, slack_id: str, response: str):
        """ Store the rating(s) for a survey in the DB """
        response = ''.join(r for r in response if r.isalpha())
        user = self._slack_id_to_user(slack_id)
        if not user.awaiting_response_on:
            self.client.chat_postMessage(
                channel=slack_id,
                text=f"Sorry, I'm not sure what meeting to assign this rating to."
            )
        event = self.calendar.get_event(user.awaiting_response_on)
        if response not in SURVEY_RESPONSES:
            self.client.chat_postMessage(
                channel=slack_id,
                text=f"Sorry, I'm only expecting responses of {', '.join(SURVEY_RESPONSES[:1])} or "
                     f"{SURVEY_RESPONSES[-1]}"
            )
        existing_response = self.session.query(SurveyResponse).filter_by(
            id=user.awaiting_response_on,
            user_id=user.id
        ).one_or_none()
        if existing_response:
            existing_response.response = response
            self.client.chat_postMessage(
                channel=slack_id,
                text=f"Updated your rating for meeting {event.name}."
            )
        else:
            new_response = SurveyResponse(
                event_id=event.id,
                user_id=user.id,
                response=response
            )
            self.session.add(new_response)
            self.client.chat_postMessage(
                channel=slack_id,
                text=f"Thanks! I've set your rating for meeting {event.name}."
            )
        self.session.commit()

        event_details = self.calendar.get_event_google_details(user.awaiting_response_on)
        num_responses = len(self.session.query(SurveyResponse).filter_by(event_id=event.id).all())
        surveyable_attendees = self._get_surveyable_attendees(event, event_details)
        if DEMO or num_responses == len(surveyable_attendees):
            self.send_survey_results(event.id)

    def send_survey_results(self, event_id):
        """ Send survey results to the owner """
        # Query db to get averages for event, sent results to user.
        event = self.calendar.get_event(event_id)
        if not event.organizer_id:
            return

        organizer = self.session.query(User).filter_by(id=event.organizer_id).one()
        survey_responses = self.session.query(SurveyResponse).filter_by(event_id=event_id)
        responses = Counter([s.response for s in survey_responses]).most_common()
        if not responses:
            return

        message = f'Here are the survey responses for meeting {event.name}:'
        for response, count in responses:
            message += f'\n - {count} attendees said "{response}"'

        self.client.chat_postMessage(
            channel=organizer.slack_id,
            text=message
        )

        event = self.session.query(Event).filter_by(id=event_id).first()
        event.survey_results_sent=True
        self.session.commit()

    def send_survey_question(self, event_id: int) -> None:
        """
        Send a survey to the attendees if standards/requirements met, otherwise updating
        should_send_survey flag.
        """
        event = self.calendar.get_event(event_id)
        event_details = self.calendar.get_event_google_details(event_id)
        surveyable_attendees = self._get_surveyable_attendees(event, event_details)

        if len(surveyable_attendees) < MIN_SURVEYABLE:
            update(Event).where(Event.id == event_id).values(should_send_survey=False)
            return

        survey_message = f"Was the meeting \"{event_details['summary']}\" effective? " \
                         f"Response with \"yes\", \"no\", or \"maybe\"."

        for attendee in surveyable_attendees:
            if attendee.has_opted_out:
                continue

            message = survey_message

            if not attendee.refresh_token:
                oauth_link = os.environ['HOST'] + '/auth'
                message += f"\n\n(By the way, if you want to include these surveys on all future meetings just sign up" \
                           f"here, or reply OPT OUT to opt out of future messages: {oauth_link})"

            self.client.chat_postMessage(
                channel=attendee.slack_id,
                text=survey_message
            )
            attendee.awaiting_response_on = event_id

        event = self.session.query(Event).filter_by(id=event_id).first()
        event.survey_questions_sent = True
        self.session.commit()

    def opt_out(self, slack_id: str):
        """ Set the user's opted-out state to True"""
        user = self._slack_id_to_user(slack_id)
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
        user = self._slack_id_to_user(slack_id)
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

    def send_greeting(self, slack_id: str) -> None:
        """ Send a greeting to a user with a link to sign-up. """
        user = self._slack_id_to_user(slack_id)
        oauth_link = os.environ['HOST'] + '/auth'
        message = "Hello! I send out surveys about meeting value. You'll get a link if you or anyone in your " \
                  "meeting has opted-in to these surveys. Feel free to say 'opt out' at any time to opt out "

        if user and not user.refresh_token:
            message += f"\n\nIf you want to include these surveys on all your future meetings just sign up here, " \
                       f" {oauth_link}"
        self.client.chat_postMessage(
            channel=user.slack_id,
            text=message
        )
        
    def send_error(self, slack_id: str, user_message: str) -> None:
        """ Send an error on an unhandled submission """
        user = self._slack_id_to_user(slack_id)
        if user:
            self.client.chat_postMessage(
                channel=slack_id,
                text=f"Sorry, I don't know how to respond to \"{user_message}\"."
            )

    def send_event_notification(self, event: Event):
        """ Send a message to the owner about their event """
        organizer = self.session.query(User).filter_by(id=event.organizer_id).one()
        if organizer.refresh_token and not organizer.has_opted_out:  # Only for organizers who have opted in

            text = f'Some information for your upcoming meeting {event.name}:'

            if not event.description:
                words_in_description = 0
            else:
                zoom_break = '──────'  # Not in regular messages, before zoom section of description.
                words_in_description = len([v for v in event.description.split(zoom_break)[0].strip().split(' ')
                                           if v.strip().isalpha()])

            if not words_in_description:
                text += '\n - It looks like this event doesn\'t have a description, please add one!'
            elif words_in_description < 12:
                text += f'\n - I only see {words_in_description} words in this description, consider adding more ' \
                        f'detail before the meeting starts!'

            average_salary = 106723.00  # average for tech workers, going lower bound than NYC average to be conservative
            cost_per_hour = event.num_attendees * (average_salary / 261 / 8)
            meeting_length = event.end_datetime - event.start_datetime
            meeting_cost = (meeting_length.total_seconds()/3600) * cost_per_hour

            text += f'\n - With {event.num_attendees} people invited, based off market averages this meeting ' \
                    f'costs ${round(meeting_cost, 2)}. '

            self.client.chat_postMessage(
                channel=organizer.slack_id,
                text=text
            )

    def _slack_id_to_user(self, slack_id: str):
        return self.session.query(User).filter_by(slack_id=slack_id).first()

    def _get_surveyable_attendees(self, event: Event, event_details: dict) -> List[User]:
        attendee_emails = [a['email'].lower() for a in event_details['attendees'] if
                           (a['email'] == event.organizer_email if DEMO else a['email'] != event.organizer_email)
                           and a['responseStatus'] != 'declined']
        surveyable_attendees = self.session.query(User).filter(
            User.email_address.in_(attendee_emails)
        ).all()
        return surveyable_attendees

    def send_pending_questions(self):
        pending_events = self.session.query(Event).filter(
            and_(
                # Event.end_datetime < datetime.datetime.utcnow(),
                not Event.survey_questions_sent,
                Event.should_send_survey
            )
        ).all()
        for event in pending_events:
            self.send_survey_question(event.id)

    def send_pending_results(self):
        pending_events = self.session.query(Event).filter(
            and_(
                Event.end_datetime < datetime.datetime.utcnow() + datetime.timedelta(0, 3600),  # one hour after over
                Event.survey_questions_sent,
                Event.survey_results_sent
            )
        ).all()
        for event in pending_events:
            self.send_survey_results(event.id)


if __name__ == '__main__':
    ms = MeetingSurveyor()
    ms.send_survey_question(2)
    # ms.send_survey_results(2)
