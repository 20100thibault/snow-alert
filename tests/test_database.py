import os
import pytest
from datetime import date, datetime, timedelta

# Use test database
os.environ['DATABASE_PATH'] = 'test_snow_alert.db'

from app.database import (
    init_db, add_user, get_user_by_email, remove_user, get_all_active_users,
    get_users_with_snow_alerts, get_users_with_garbage_alerts, get_users_with_recycling_alerts,
    update_user_preferences, add_waste_zone, get_waste_zone, get_waste_zone_by_id,
    record_reminder_sent, was_reminder_sent, get_reminders_for_user
)
from app.models import Base, User, WasteZone, ReminderSent
from app.database import engine
from sqlalchemy.exc import IntegrityError


@pytest.fixture(autouse=True)
def setup_teardown():
    """Create fresh database for each test."""
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


# ============== User Preference Column Tests ==============

class TestUserPreferenceColumns:
    def test_snow_alerts_enabled_column_exists(self):
        """Verify snow_alerts_enabled column exists and defaults to True."""
        user = add_user('test@example.com', 'G1R2K8', 46.802926, -71.220034)
        assert hasattr(user, 'snow_alerts_enabled')
        assert user.snow_alerts_enabled is True

    def test_garbage_alerts_enabled_column_exists(self):
        """Verify garbage_alerts_enabled column exists and defaults to False."""
        user = add_user('test@example.com', 'G1R2K8', 46.802926, -71.220034)
        assert hasattr(user, 'garbage_alerts_enabled')
        assert user.garbage_alerts_enabled is False

    def test_recycling_alerts_enabled_column_exists(self):
        """Verify recycling_alerts_enabled column exists and defaults to False."""
        user = add_user('test@example.com', 'G1R2K8', 46.802926, -71.220034)
        assert hasattr(user, 'recycling_alerts_enabled')
        assert user.recycling_alerts_enabled is False

    def test_waste_zone_id_column_exists(self):
        """Verify waste_zone_id column exists and can be null."""
        user = add_user('test@example.com', 'G1R2K8', 46.802926, -71.220034)
        assert hasattr(user, 'waste_zone_id')
        assert user.waste_zone_id is None

    def test_add_user_with_custom_preferences(self):
        """Verify user can be created with custom preferences."""
        user = add_user(
            'test@example.com', 'G1R2K8', 46.0, -71.0,
            snow_alerts=False,
            garbage_alerts=True,
            recycling_alerts=True
        )
        assert user.snow_alerts_enabled is False
        assert user.garbage_alerts_enabled is True
        assert user.recycling_alerts_enabled is True


# ============== Add User Tests ==============

class TestAddUser:
    def test_add_user_success(self):
        user = add_user('test@example.com', 'G1R2K8', 46.802926, -71.220034)
        assert user is not None
        assert user.id is not None
        assert user.email == 'test@example.com'
        assert user.postal_code == 'G1R2K8'
        assert user.active is True

    def test_add_user_normalizes_email(self):
        user = add_user('  TEST@EXAMPLE.COM  ', 'G1R2K8', 46.0, -71.0)
        assert user.email == 'test@example.com'

    def test_add_user_normalizes_postal_code(self):
        user = add_user('test2@example.com', 'g1r 2k8', 46.0, -71.0)
        assert user.postal_code == 'G1R2K8'

    def test_add_user_with_waste_zone(self):
        zone_id = add_waste_zone('G1R2K8', 'monday', 'odd')
        user = add_user('test@example.com', 'G1R2K8', 46.0, -71.0, waste_zone_id=zone_id)
        assert user.waste_zone_id == zone_id


# ============== Get User Tests ==============

class TestGetUserByEmail:
    def test_get_existing_user(self):
        add_user('find@example.com', 'G1R2K8', 46.0, -71.0)
        user = get_user_by_email('find@example.com')
        assert user is not None
        assert user.email == 'find@example.com'

    def test_get_nonexistent_user(self):
        user = get_user_by_email('nobody@example.com')
        assert user is None

    def test_get_user_case_insensitive(self):
        add_user('case@example.com', 'G1R2K8', 46.0, -71.0)
        user = get_user_by_email('CASE@EXAMPLE.COM')
        assert user is not None


# ============== Remove User Tests ==============

class TestRemoveUser:
    def test_remove_existing_user(self):
        add_user('remove@example.com', 'G1R2K8', 46.0, -71.0)
        result = remove_user('remove@example.com')
        assert result is True
        assert get_user_by_email('remove@example.com') is None

    def test_remove_nonexistent_user(self):
        result = remove_user('nobody@example.com')
        assert result is False

    def test_remove_user_deletes_reminders(self):
        user = add_user('remove@example.com', 'G1R2K8', 46.0, -71.0)
        record_reminder_sent(user.id, 'snow', date.today())
        remove_user('remove@example.com')
        reminders = get_reminders_for_user(user.id)
        assert len(reminders) == 0


# ============== Get Users by Alert Type Tests ==============

class TestGetUsersByAlertType:
    def test_get_active_users(self):
        add_user('active1@example.com', 'G1R2K8', 46.0, -71.0)
        add_user('active2@example.com', 'G1V1J8', 46.0, -71.0)
        users = get_all_active_users()
        assert len(users) == 2

    def test_empty_when_no_users(self):
        users = get_all_active_users()
        assert len(users) == 0

    def test_get_users_with_snow_alerts(self):
        add_user('snow1@example.com', 'G1R2K8', 46.0, -71.0, snow_alerts=True)
        add_user('snow2@example.com', 'G1R2K8', 46.0, -71.0, snow_alerts=True)
        add_user('nosnow@example.com', 'G1R2K8', 46.0, -71.0, snow_alerts=False)
        users = get_users_with_snow_alerts()
        assert len(users) == 2

    def test_get_users_with_garbage_alerts(self):
        add_user('garbage1@example.com', 'G1R2K8', 46.0, -71.0, garbage_alerts=True)
        add_user('nogarbage@example.com', 'G1R2K8', 46.0, -71.0, garbage_alerts=False)
        users = get_users_with_garbage_alerts()
        assert len(users) == 1
        assert users[0].email == 'garbage1@example.com'

    def test_get_users_with_recycling_alerts(self):
        add_user('recycling1@example.com', 'G1R2K8', 46.0, -71.0, recycling_alerts=True)
        add_user('norecycling@example.com', 'G1R2K8', 46.0, -71.0, recycling_alerts=False)
        users = get_users_with_recycling_alerts()
        assert len(users) == 1
        assert users[0].email == 'recycling1@example.com'


# ============== Update User Preferences Tests ==============

class TestUpdateUserPreferences:
    def test_update_snow_alerts(self):
        add_user('test@example.com', 'G1R2K8', 46.0, -71.0, snow_alerts=True)
        result = update_user_preferences('test@example.com', snow_alerts=False)
        assert result is True
        user = get_user_by_email('test@example.com')
        assert user.snow_alerts_enabled is False

    def test_update_garbage_alerts(self):
        add_user('test@example.com', 'G1R2K8', 46.0, -71.0, garbage_alerts=False)
        result = update_user_preferences('test@example.com', garbage_alerts=True)
        assert result is True
        user = get_user_by_email('test@example.com')
        assert user.garbage_alerts_enabled is True

    def test_update_recycling_alerts(self):
        add_user('test@example.com', 'G1R2K8', 46.0, -71.0, recycling_alerts=False)
        result = update_user_preferences('test@example.com', recycling_alerts=True)
        assert result is True
        user = get_user_by_email('test@example.com')
        assert user.recycling_alerts_enabled is True

    def test_update_waste_zone_id(self):
        add_user('test@example.com', 'G1R2K8', 46.0, -71.0)
        zone_id = add_waste_zone('G1R2K8', 'monday', 'odd')
        result = update_user_preferences('test@example.com', waste_zone_id=zone_id)
        assert result is True
        user = get_user_by_email('test@example.com')
        assert user.waste_zone_id == zone_id

    def test_update_multiple_preferences(self):
        add_user('test@example.com', 'G1R2K8', 46.0, -71.0)
        result = update_user_preferences(
            'test@example.com',
            snow_alerts=False,
            garbage_alerts=True,
            recycling_alerts=True
        )
        assert result is True
        user = get_user_by_email('test@example.com')
        assert user.snow_alerts_enabled is False
        assert user.garbage_alerts_enabled is True
        assert user.recycling_alerts_enabled is True

    def test_update_nonexistent_user_returns_false(self):
        result = update_user_preferences('nobody@example.com', snow_alerts=False)
        assert result is False

    def test_update_preserves_unspecified_preferences(self):
        add_user('test@example.com', 'G1R2K8', 46.0, -71.0,
                 snow_alerts=True, garbage_alerts=True, recycling_alerts=True)
        update_user_preferences('test@example.com', snow_alerts=False)
        user = get_user_by_email('test@example.com')
        assert user.snow_alerts_enabled is False
        assert user.garbage_alerts_enabled is True  # Unchanged
        assert user.recycling_alerts_enabled is True  # Unchanged


# ============== Waste Zone Tests ==============

class TestWasteZones:
    def test_waste_zones_table_exists(self):
        """Verify waste_zones table is created."""
        zone_id = add_waste_zone('G1R2K8', 'monday', 'odd')
        assert zone_id is not None
        assert zone_id > 0

    def test_add_waste_zone_creates_new(self):
        zone_id = add_waste_zone('G1R2K8', 'tuesday', 'even')
        zone = get_waste_zone('G1R2K8')
        assert zone is not None
        assert zone['id'] == zone_id
        assert zone['garbage_day'] == 'tuesday'
        assert zone['recycling_week'] == 'even'

    def test_add_waste_zone_updates_existing(self):
        zone_id1 = add_waste_zone('G1R2K8', 'monday', 'odd')
        zone_id2 = add_waste_zone('G1R2K8', 'wednesday', 'even')
        assert zone_id1 == zone_id2  # Same zone, updated
        zone = get_waste_zone('G1R2K8')
        assert zone['garbage_day'] == 'wednesday'
        assert zone['recycling_week'] == 'even'

    def test_add_waste_zone_normalizes_zone_code(self):
        zone_id = add_waste_zone('g1r 2k8', 'monday', 'odd')
        zone = get_waste_zone('G1R2K8')
        assert zone is not None
        assert zone['zone_code'] == 'G1R2K8'

    def test_add_waste_zone_normalizes_case(self):
        add_waste_zone('G1R2K8', 'MONDAY', 'ODD')
        zone = get_waste_zone('G1R2K8')
        assert zone['garbage_day'] == 'monday'
        assert zone['recycling_week'] == 'odd'

    def test_get_waste_zone_nonexistent(self):
        zone = get_waste_zone('XXXXXX')
        assert zone is None

    def test_get_waste_zone_by_id(self):
        zone_id = add_waste_zone('G1R2K8', 'monday', 'odd')
        zone = get_waste_zone_by_id(zone_id)
        assert zone is not None
        assert zone['zone_code'] == 'G1R2K8'

    def test_get_waste_zone_by_id_nonexistent(self):
        zone = get_waste_zone_by_id(99999)
        assert zone is None

    def test_zone_code_unique_constraint(self):
        """Zone code should be unique."""
        add_waste_zone('G1R2K8', 'monday', 'odd')
        # Second add should update, not create duplicate
        add_waste_zone('G1R2K8', 'tuesday', 'even')
        # This should work without error, as it updates existing


# ============== Reminders Sent Tests ==============

class TestRemindersSent:
    def test_reminders_sent_table_exists(self):
        """Verify reminders_sent table is created."""
        user = add_user('test@example.com', 'G1R2K8', 46.0, -71.0)
        result = record_reminder_sent(user.id, 'snow', date.today())
        assert result is True

    def test_record_reminder_sent(self):
        user = add_user('test@example.com', 'G1R2K8', 46.0, -71.0)
        today = date.today()
        record_reminder_sent(user.id, 'garbage', today)
        assert was_reminder_sent(user.id, 'garbage', today) is True

    def test_was_reminder_sent_false_when_not_sent(self):
        user = add_user('test@example.com', 'G1R2K8', 46.0, -71.0)
        assert was_reminder_sent(user.id, 'snow', date.today()) is False

    def test_duplicate_reminder_raises_integrity_error(self):
        user = add_user('test@example.com', 'G1R2K8', 46.0, -71.0)
        today = date.today()
        record_reminder_sent(user.id, 'snow', today)
        with pytest.raises(IntegrityError):
            record_reminder_sent(user.id, 'snow', today)

    def test_different_types_same_date_allowed(self):
        user = add_user('test@example.com', 'G1R2K8', 46.0, -71.0)
        today = date.today()
        record_reminder_sent(user.id, 'snow', today)
        record_reminder_sent(user.id, 'garbage', today)
        record_reminder_sent(user.id, 'recycling', today)
        # Should not raise - different types are allowed

    def test_same_type_different_dates_allowed(self):
        user = add_user('test@example.com', 'G1R2K8', 46.0, -71.0)
        today = date.today()
        tomorrow = today + timedelta(days=1)
        record_reminder_sent(user.id, 'snow', today)
        record_reminder_sent(user.id, 'snow', tomorrow)
        # Should not raise - different dates are allowed

    def test_reminder_type_normalized_to_lowercase(self):
        user = add_user('test@example.com', 'G1R2K8', 46.0, -71.0)
        today = date.today()
        record_reminder_sent(user.id, 'SNOW', today)
        assert was_reminder_sent(user.id, 'snow', today) is True

    def test_get_reminders_for_user(self):
        user = add_user('test@example.com', 'G1R2K8', 46.0, -71.0)
        today = date.today()
        record_reminder_sent(user.id, 'snow', today)
        record_reminder_sent(user.id, 'garbage', today)
        reminders = get_reminders_for_user(user.id)
        assert len(reminders) == 2
        types = {r['reminder_type'] for r in reminders}
        assert types == {'snow', 'garbage'}

    def test_get_reminders_for_user_empty(self):
        user = add_user('test@example.com', 'G1R2K8', 46.0, -71.0)
        reminders = get_reminders_for_user(user.id)
        assert len(reminders) == 0


# ============== Foreign Key Relationship Tests ==============

class TestForeignKeyRelationships:
    def test_user_waste_zone_relationship(self):
        """Verify user can be linked to waste zone."""
        zone_id = add_waste_zone('G1R2K8', 'monday', 'odd')
        user = add_user('test@example.com', 'G1R2K8', 46.0, -71.0, waste_zone_id=zone_id)
        assert user.waste_zone_id == zone_id
        zone = get_waste_zone_by_id(zone_id)
        assert zone is not None
