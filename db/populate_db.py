from src.meeting_surveyor import MeetingSurveyor
import os

if os.getcwd().endswith('/db'):
    os.chdir('..')

ms = MeetingSurveyor()
ms.update_slack_users()