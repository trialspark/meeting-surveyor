from src.meeting_surveyor import MeetingSurveyor
from src.calendar_api_wrapper import CalendarAPIWrapper
import os

if os.getcwd().endswith('/db'):
    os.chdir('..')

ms = MeetingSurveyor()
ms.populate_slack_users()
# Log in then run this again
cs = CalendarAPIWrapper()
cs.populate_events()