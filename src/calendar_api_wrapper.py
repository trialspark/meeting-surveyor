from typing import List, Dict, Union, Optional
from db.database import get_session, Event, User
from datetime import datetime, date, timedelta
import os
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import pytz
import logging

class CalendarAPIWrapper(object):
    """
    Class which handles all interaction with the Google APIs, retrieving events for users,
    getting details for events, and generating/storing OAuth
    """
    def __init__(self):
        self.session = get_session()
        self.scope = ['https://www.googleapis.com/auth/calendar.readonly']
        # raise NotImplementedError("Need to add google cloud pieces")

    def get_service(self, user: User):
        # TODO: Refresh token if token expired.

        tokens = {
            'client_id': os.environ['GOOGLE_CLIENT_ID'],
            'client_secret':  os.environ['GOOGLE_CLIENT_SECRET'],
            'refresh_token': user.refresh_token
        }
        creds = Credentials.from_authorized_user_info(tokens, self.scope)
        if creds and creds.expired or not creds.valid():
            creds.refresh(Request())
        service = build('calendar', 'v3', credentials=creds)
        return service

    def get_event(self, event_id: str) -> Event:
        """
        :param event_id:
        :return: Dict of event attributes
        """
        return self.session.query(Event).filter_by(event_id=event_id).one()

    def get_events_for_user(self, user: User, min_attendees=2, days_out: int = 1)\
            -> List[Dict]:
        """ Get list of upcoming events for a user """
        now = datetime.utcnow().isoformat() + 'Z'
        one_day = (datetime.utcnow() + timedelta(days_out)).isoformat() + 'Z'
        service = self.get_service(user)
        events = service.events().list(calendarId='primary', timeMin=now, timeMax=one_day, singleEvents=True,
                                       orderBy='startTime').execute()

        def convert(event: dict) -> dict:
            event['startTime'] = datetime.fromisoformat(event['start']['dateTime']).astimezone(pytz.utc)
            event['endTime'] = datetime.fromisoformat(event['end']['dateTime']).astimezone(pytz.utc)
            return event

        events = [convert(e) for e in events['items'] if len(e.get('attendees', [])) > min_attendees
                  and e['start'].get('dateTime') and e.get('organizer')]

        return events

    def populate_events(self, days_out: int = 1):
        """ Get the upcoming events for all users. """
        users = self.session.query(User).filter(User.refresh_token).all()
        new_events = []
        for user in users:
            events = self.get_events_for_user(user, days_out=days_out)
            for event in events:
                organizer_email = event['organizer']['email'].lower()
                organizer = self.session.query(User).filter_by(email_address=organizer_email).one_or_none()

                existing_event = self.session.query(Event).filter_by(google_event_id=event['id']).one_or_none()
                if existing_event:
                    existing_event.start_datetime = event['startTime']
                    existing_event.end_datetime = event['endTime']
                    existing_event.organizer_email = organizer_email
                    self.session.commit()
                else:
                    new_events.append(
                        Event(
                            google_event_id=event['id'],
                            name=event['summary'],
                            organizer_id=organizer.id if organizer else None,
                            organizer_email=organizer_email,
                            start_datetime=event['startTime'],
                            end_datetime=event['endTime'],
                            survey_sent=False
                        )
                    )
        self.session.bulk_save_objects(new_events)
        self.session.commit()
        logging.info(f"{len(new_events)} events added!")


if __name__ == '__main__':
    cal = CalendarAPIWrapper()
    events = cal.populate_events()