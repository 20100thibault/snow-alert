from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()


class WasteZone(Base):
    """Waste collection zone with schedule information."""
    __tablename__ = 'waste_zones'

    id = Column(Integer, primary_key=True, autoincrement=True)
    zone_code = Column(String(10), unique=True, nullable=False, index=True)
    garbage_day = Column(String(10), nullable=False)  # 'monday', 'tuesday', etc.
    recycling_week = Column(String(10), nullable=False)  # 'odd' or 'even'
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    users = relationship("User", back_populates="waste_zone")

    def __repr__(self):
        return f"<WasteZone {self.zone_code} - {self.garbage_day}/{self.recycling_week}>"


class User(Base):
    """User subscribed to alerts."""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    postal_code = Column(String(7), nullable=False)  # Format: G1R2K8 or G1R 2K8
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Alert preferences
    snow_alerts_enabled = Column(Boolean, default=True, nullable=False)
    garbage_alerts_enabled = Column(Boolean, default=False, nullable=False)
    recycling_alerts_enabled = Column(Boolean, default=False, nullable=False)

    # Link to waste zone
    waste_zone_id = Column(Integer, ForeignKey('waste_zones.id'), nullable=True)
    waste_zone = relationship("WasteZone", back_populates="users")

    def __repr__(self):
        return f"<User {self.email} - {self.postal_code}>"


class ReminderSent(Base):
    """Track sent reminders to prevent duplicates."""
    __tablename__ = 'reminders_sent'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    reminder_type = Column(String(20), nullable=False)  # 'snow', 'garbage', 'recycling'
    reference_date = Column(Date, nullable=False)
    sent_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User")

    __table_args__ = (
        UniqueConstraint('user_id', 'reminder_type', 'reference_date', name='uix_reminder_unique'),
    )

    def __repr__(self):
        return f"<ReminderSent {self.user_id} - {self.reminder_type} - {self.reference_date}>"
