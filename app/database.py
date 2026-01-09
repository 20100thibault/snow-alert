from typing import Optional, List
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base, User
from config import Config

engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
Session = sessionmaker(bind=engine)


def init_db():
    """Create all database tables."""
    Base.metadata.create_all(engine)


def get_session():
    """Get a new database session."""
    return Session()


def add_user(email: str, postal_code: str, lat: float, lon: float) -> User:
    """Add a new user to the database. Returns the created user."""
    session = get_session()
    try:
        user = User(
            email=email.lower().strip(),
            postal_code=postal_code.upper().replace(' ', ''),
            lat=lat,
            lon=lon,
            active=True
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def get_user_by_email(email: str) -> Optional[User]:
    """Get a user by email. Returns None if not found."""
    session = get_session()
    try:
        user = session.query(User).filter_by(email=email.lower().strip()).first()
        return user
    finally:
        session.close()


def get_all_active_users() -> List[User]:
    """Get all active users."""
    session = get_session()
    try:
        users = session.query(User).filter_by(active=True).all()
        return users
    finally:
        session.close()


def remove_user(email: str) -> bool:
    """Remove a user by email. Returns True if removed, False if not found."""
    session = get_session()
    try:
        user = session.query(User).filter_by(email=email.lower().strip()).first()
        if user:
            session.delete(user)
            session.commit()
            return True
        return False
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()
