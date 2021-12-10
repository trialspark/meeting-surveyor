from typing import List, Dict, Union, Optional
from db.database import get_session, Event, User
from datetime import datetime, date, timedelta
import os
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials


class CalendarAPIWrapper(object):
    """
    Class which handles all interaction with the Google APIs, retrieving events for users,
    getting details for events, and generating/storing OAuth
    """
    def __init__(self):
        self.session = get_session()
        self.scope = ['https://www.googleapis.com/auth/calendar.readonly']
        # raise NotImplementedError("Need to add google cloud pieces")

    def get_service(self, user_id: Optional[int] = None, email_address: Optional[str] = None):
        user = self._get_user(user_id, email_address)

        # TODO: Refresh token if token expired.

        tokens = {
            'access_token': user.access_token,
            'client_id': os.environ['GOOGLE_CLIENT_ID'],
            'client_secret':  os.environ['GOOGLE_CLIENT_SECRET'],
            'refresh_token': user.refresh_token
        }
        creds = Credentials.from_authorized_user_info(tokens, self.scope)
        if creds and creds.expired or not creds.valid():
            creds.refresh(Request())
        service = build('calendar', 'v3', credentials=creds)
        return service

    def get_event_attributes(self, event_id: str) -> Dict:
        """
        :param event_id:
        :return: Dict of event attributes
        """
        raise NotImplementedError()

    def get_events_for_user(self, user_id: Optional[int] = None, email_address: Optional[str] = None, min_attendees=2)\
            -> List[Dict]:
        """ Get list of upcoming events for a user """
        service = self.get_service(user_id, email_address)
        now = datetime.utcnow().isoformat() + 'Z'
        one_day = (datetime.utcnow() + timedelta(1)).isoformat() + 'Z'
        events = service.events().list(calendarId='primary', timeMin=now, timeMax=one_day, singleEvents=True,
                                       orderBy='startTime').execute()
        events = [e for e in events['items'] if len(e.get('attendees', [])) > min_attendees]
        return events

    def populate_events(self,
                        min_date: Optional[Union[datetime, date]]=None,
                        max_date: Optional[Union[datetime, date]]=None):
        raise NotImplementedError()

    def _get_user(self, user_id: Optional[int] = None, email_address: Optional[str] = None):
        if not user_id and not email_address:
            raise ValueError()

        if user_id:
            return self.session.query(User).filter_by(id=user_id).one()
        else:
            return self.session.query(User).filter_by(email_address=email_address).one()


if __name__ == '__main__':
    cal = CalendarAPIWrapper()
    events = cal.get_events_for_user(email_address='jklingelhofer@trialspark.com')
    print(events)