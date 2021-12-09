import os

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy import create_engine
from sqlalchemy_utils import create_database, database_exists
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    slack_id = Column(String, nullable=False)
    email_address = Column(String, nullable=False)
    has_opted_out = Column(Boolean, nullable=False)
    oauth_token = Column(String)


class Survey(Base):
    __tablename__ = 'surveys'

    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey('events.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)

    # TODO: Ratings for surveys.


class Event(Base):
    __tablename__ = 'events'

    id = Column(Integer, primary_key=True)
    google_event_id = Column(String, nullable=False)
    organizer_id = Column(Integer, ForeignKey('users.id'), nullable=False)


def get_session():
    engine = create_engine("sqlite:///db/meeting_surveyor.db")
    if not database_exists(engine.url):
        create_database(engine.url)
        Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


if __name__ == '__main__':
    if os.getcwd().endswith(os.sep + 'db'):
        os.chdir('..')
    get_session()
