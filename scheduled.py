import schedule
import time
from src.meeting_surveyor import MeetingSurveyor
from src.calendar_api_wrapper import CalendarAPIWrapper
import os
from datetime import datetime

global stale_refresh
stale_refresh = True


def refresh_slack_users():
    print("Refreshing Slack Users!")
    ms = MeetingSurveyor()
    ms.populate_slack_users()


def refresh_events():
    global stale_refresh
    print("Refreshing upcoming events!")
    cal = CalendarAPIWrapper()
    new_events = cal.populate_events()
    ms = MeetingSurveyor()

    if not stale_refresh:
        for event in new_events:
            if event.organizer_id:
                ms.send_event_notification(event)
    stale_refresh = False


def send_survey_questions():
    # send any pending questions
    print("sending survey questions!")
    ms = MeetingSurveyor()
    ms.send_pending_questions()

def send_survey_result():
    # send any pending survey results.
    print("sending pending results!")
    ms = MeetingSurveyor()
    ms.send_pending_results()

refresh_slack_users()
schedule.every().hour.do(refresh_slack_users)
schedule.every(30).seconds.do(refresh_events)
schedule.every(30).seconds.do(send_survey_questions)
schedule.every(30).seconds.do(send_survey_result)

while True:
    schedule.run_pending()
    time.sleep(10)