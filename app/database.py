from contextlib import contextmanager
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from app.models import Base, User, WasteZone, ReminderSent
from config import Config

engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
Session = sessionmaker(bind=engine)


@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations."""
    session = Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db():
    """Create all database tables."""
    Base.metadata.create_all(engine)
    migrate_existing_users()


def migrate_existing_users():
    """
    Migrate existing users to have default preference values.
    Existing users get snow_alerts_enabled=True, waste alerts=False.
    """
    try:
        with session_scope() as session:
            result = session.execute(text(
                "SELECT COUNT(*) FROM users WHERE snow_alerts_enabled IS NULL"
            )).scalar()

            if result and result > 0:
                session.execute(text("""
                    UPDATE users
                    SET snow_alerts_enabled = 1,
                        garbage_alerts_enabled = 0,
                        recycling_alerts_enabled = 0
                    WHERE snow_alerts_enabled IS NULL
                """))
    except Exception:
        pass


def get_session():
    """Get a new database session."""
    return Session()


# ============== Helper Functions ==============

def _normalize_email(email: str) -> str:
    """Normalize email to lowercase without leading/trailing whitespace."""
    return email.lower().strip()


def _normalize_postal_code(postal_code: str) -> str:
    """Normalize postal code to uppercase without spaces."""
    return postal_code.upper().replace(' ', '')


# ============== User Functions ==============

def add_user(
    email: str,
    postal_code: str,
    lat: float,
    lon: float,
    snow_alerts: bool = True,
    garbage_alerts: bool = False,
    recycling_alerts: bool = False,
    waste_zone_id: Optional[int] = None
) -> User:
    """Add a new user to the database. Returns the created user."""
    session = get_session()
    try:
        user = User(
            email=_normalize_email(email),
            postal_code=_normalize_postal_code(postal_code),
            lat=lat,
            lon=lon,
            active=True,
            snow_alerts_enabled=snow_alerts,
            garbage_alerts_enabled=garbage_alerts,
            recycling_alerts_enabled=recycling_alerts,
            waste_zone_id=waste_zone_id
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
        return session.query(User).filter_by(email=_normalize_email(email)).first()
    finally:
        session.close()


def get_all_active_users() -> List[User]:
    """Get all active users."""
    session = get_session()
    try:
        return session.query(User).filter_by(active=True).all()
    finally:
        session.close()


def get_users_with_snow_alerts() -> List[User]:
    """Get all active users with snow alerts enabled."""
    session = get_session()
    try:
        return session.query(User).filter_by(active=True, snow_alerts_enabled=True).all()
    finally:
        session.close()


def get_users_with_garbage_alerts() -> List[User]:
    """Get all active users with garbage alerts enabled."""
    session = get_session()
    try:
        return session.query(User).filter_by(active=True, garbage_alerts_enabled=True).all()
    finally:
        session.close()


def get_users_with_recycling_alerts() -> List[User]:
    """Get all active users with recycling alerts enabled."""
    session = get_session()
    try:
        return session.query(User).filter_by(active=True, recycling_alerts_enabled=True).all()
    finally:
        session.close()


def remove_user(email: str) -> bool:
    """Remove a user by email. Returns True if removed, False if not found."""
    session = get_session()
    try:
        user = session.query(User).filter_by(email=_normalize_email(email)).first()
        if not user:
            return False
        session.query(ReminderSent).filter_by(user_id=user.id).delete()
        session.delete(user)
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def update_user_preferences(
    email: str,
    snow_alerts: Optional[bool] = None,
    garbage_alerts: Optional[bool] = None,
    recycling_alerts: Optional[bool] = None,
    waste_zone_id: Optional[int] = None,
    postal_code: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None
) -> bool:
    """
    Update user alert preferences.
    Only updates fields that are not None.
    Returns True on success, False if user not found.
    """
    session = get_session()
    try:
        user = session.query(User).filter_by(email=_normalize_email(email)).first()
        if not user:
            return False

        if snow_alerts is not None:
            user.snow_alerts_enabled = snow_alerts
        if garbage_alerts is not None:
            user.garbage_alerts_enabled = garbage_alerts
        if recycling_alerts is not None:
            user.recycling_alerts_enabled = recycling_alerts
        if waste_zone_id is not None:
            user.waste_zone_id = waste_zone_id
        if postal_code is not None:
            user.postal_code = _normalize_postal_code(postal_code)
        if lat is not None:
            user.lat = lat
        if lon is not None:
            user.lon = lon

        session.commit()
        return True
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


# ============== Waste Zone Functions ==============

def _zone_to_dict(zone: WasteZone) -> Dict[str, Any]:
    """Convert a WasteZone object to a dictionary."""
    return {
        'id': zone.id,
        'zone_code': zone.zone_code,
        'garbage_day': zone.garbage_day,
        'recycling_week': zone.recycling_week,
        'created_at': zone.created_at,
        'updated_at': zone.updated_at
    }


def add_waste_zone(zone_code: str, garbage_day: str, recycling_week: str) -> int:
    """Add or update a waste zone. Returns the zone id."""
    session = get_session()
    try:
        normalized_code = _normalize_postal_code(zone_code)
        existing = session.query(WasteZone).filter_by(zone_code=normalized_code).first()

        if existing:
            existing.garbage_day = garbage_day.lower()
            existing.recycling_week = recycling_week.lower()
            existing.updated_at = datetime.utcnow()
            session.commit()
            return existing.id

        zone = WasteZone(
            zone_code=normalized_code,
            garbage_day=garbage_day.lower() if garbage_day else 'unknown',
            recycling_week=recycling_week.lower() if recycling_week else 'unknown'
        )
        session.add(zone)
        session.commit()
        session.refresh(zone)
        return zone.id
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def get_waste_zone(zone_code: str) -> Optional[Dict[str, Any]]:
    """Get a waste zone by zone_code. Returns dict with zone data or None if not found."""
    session = get_session()
    try:
        zone = session.query(WasteZone).filter_by(
            zone_code=_normalize_postal_code(zone_code)
        ).first()
        return _zone_to_dict(zone) if zone else None
    finally:
        session.close()


def get_waste_zone_by_id(zone_id: int) -> Optional[Dict[str, Any]]:
    """Get a waste zone by id. Returns dict with zone data or None if not found."""
    session = get_session()
    try:
        zone = session.query(WasteZone).filter_by(id=zone_id).first()
        return _zone_to_dict(zone) if zone else None
    finally:
        session.close()


# ============== Reminder Functions ==============

def record_reminder_sent(user_id: int, reminder_type: str, reference_date: date) -> bool:
    """
    Record that a reminder was sent.
    Returns True on success.
    Raises IntegrityError if duplicate (same user, type, date).
    """
    session = get_session()
    try:
        reminder = ReminderSent(
            user_id=user_id,
            reminder_type=reminder_type.lower(),
            reference_date=reference_date
        )
        session.add(reminder)
        session.commit()
        return True
    except IntegrityError:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def was_reminder_sent(user_id: int, reminder_type: str, reference_date: date) -> bool:
    """Check if a reminder was already sent. Returns True if reminder exists."""
    session = get_session()
    try:
        reminder = session.query(ReminderSent).filter_by(
            user_id=user_id,
            reminder_type=reminder_type.lower(),
            reference_date=reference_date
        ).first()
        return reminder is not None
    finally:
        session.close()


def get_reminders_for_user(user_id: int) -> List[Dict[str, Any]]:
    """Get all reminders sent to a user."""
    session = get_session()
    try:
        reminders = session.query(ReminderSent).filter_by(user_id=user_id).all()
        return [
            {
                'id': r.id,
                'user_id': r.user_id,
                'reminder_type': r.reminder_type,
                'reference_date': r.reference_date,
                'sent_at': r.sent_at
            }
            for r in reminders
        ]
    finally:
        session.close()
