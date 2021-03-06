import os

import sqlalchemy.orm
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, DateTime, Integer, String, Boolean, ForeignKey, UniqueConstraint, JSON
from sqlalchemy import create_engine
from sqlalchemy_utils import create_database, database_exists
from sqlalchemy.orm import sessionmaker

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    slack_id = Column(String, nullable=False)
    email_address = Column(String, nullable=False)
    has_opted_out = Column(Boolean, default=False, nullable=False)
    refresh_token = Column(String, nullable=True)
    awaiting_response_on = Column(Integer, ForeignKey('events.id'), nullable=True)

    UniqueConstraint(email_address)
    UniqueConstraint(slack_id)


class SurveyResponse(Base):
    __tablename__ = 'survey_responses'

    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey('events.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    response = Column(String, nullable=False)


class Event(Base):
    __tablename__ = 'events'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    google_event_id = Column(String, nullable=False)
    organizer_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    organizer_email = Column(String, nullable=False)  # Backup/debug for when we can't find organizer id
    created_at_datetime = Column(DateTime(timezone=False))
    start_datetime = Column(DateTime(timezone=False))
    end_datetime = Column(DateTime(timezone=False))
    should_send_survey = Column(Boolean, default=True)
    survey_questions_sent = Column(Boolean, default=False)
    survey_results_sent = Column(Boolean, default=False)
    description = Column(String)
    source_user_id = Column(Integer, ForeignKey('users.id'), nullable=False)  # Who we were when we got this event info.
    num_attendees = Column(Integer, nullable=False)  # Who we were when we got this event info.


def get_session() -> sqlalchemy.orm.Session:
    engine = create_engine("sqlite:///db/meeting_surveyor.db")
    if not database_exists(engine.url):
        create_database(engine.url)
        Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


if __name__ == '__main__':
    if os.getcwd().endswith(os.sep + 'db'):
        os.chdir('..')
    get_session()

