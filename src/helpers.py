from db.database import User
from sqlalchemy.orm import session as SessionType
from typing import Optional


def get_user(session: SessionType, user_id: Optional[int] = None, email_address: Optional[str] = None):
    if not user_id and not email_address:
        raise ValueError()

    if user_id:
        return session.query(User).filter_by(id=user_id).one()
    else:
        return session.query(User).filter_by(email_address=email_address).one()

