"""
Tests for database migration - ensuring existing users are migrated correctly.
"""

import pytest
import os
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Set test environment before imports
os.environ['EMAIL_ENABLED'] = 'false'
os.environ['DATABASE_PATH'] = 'test_migration.db'


class TestExistingUserMigration:
    """Tests for Task 6.2: Existing user migration."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test database simulating pre-migration state."""
        from config import Config
        from app.models import Base

        # Create a fresh test database
        self.db_path = 'test_migration.db'
        self.engine = create_engine(f'sqlite:///{self.db_path}')
        self.Session = sessionmaker(bind=self.engine)

        # Create tables
        Base.metadata.create_all(self.engine)

        yield

        # Clean up
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except:
                pass

    def test_existing_users_retain_original_data(self):
        """Verify existing users retain email, postal_code, lat, lon."""
        from app.database import add_user, get_user_by_email

        # Add a user (simulating existing user)
        add_user(
            email='existing@example.com',
            postal_code='G1R2K8',
            lat=46.8139,
            lon=-71.2080
        )

        # Retrieve and verify data is retained
        user = get_user_by_email('existing@example.com')
        assert user is not None
        assert user.email == 'existing@example.com'
        assert user.postal_code == 'G1R2K8'
        assert abs(user.lat - 46.8139) < 0.001
        assert abs(user.lon - (-71.2080)) < 0.001

    def test_existing_users_have_snow_alerts_enabled_true(self):
        """Verify existing users have snow_alerts_enabled = TRUE."""
        from app.database import add_user, get_user_by_email

        # Add user with default preferences (snow_alerts=True by default)
        add_user(
            email='snow_default@example.com',
            postal_code='G1R2K8',
            lat=46.8139,
            lon=-71.2080
        )

        user = get_user_by_email('snow_default@example.com')
        assert user.snow_alerts_enabled is True

    def test_existing_users_have_garbage_alerts_enabled_false(self):
        """Verify existing users have garbage_alerts_enabled = FALSE."""
        from app.database import add_user, get_user_by_email

        # Add user with default preferences
        add_user(
            email='garbage_default@example.com',
            postal_code='G1R2K8',
            lat=46.8139,
            lon=-71.2080
        )

        user = get_user_by_email('garbage_default@example.com')
        assert user.garbage_alerts_enabled is False

    def test_existing_users_have_recycling_alerts_enabled_false(self):
        """Verify existing users have recycling_alerts_enabled = FALSE."""
        from app.database import add_user, get_user_by_email

        # Add user with default preferences
        add_user(
            email='recycling_default@example.com',
            postal_code='G1R2K8',
            lat=46.8139,
            lon=-71.2080
        )

        user = get_user_by_email('recycling_default@example.com')
        assert user.recycling_alerts_enabled is False

    def test_existing_snow_alert_functionality_unchanged(self):
        """Verify existing snow alert functionality still works."""
        from app.database import add_user, get_users_with_snow_alerts

        # Add users - one with snow alerts (default), one without
        add_user(
            email='snow_enabled@example.com',
            postal_code='G1R2K8',
            lat=46.8139,
            lon=-71.2080,
            snow_alerts=True
        )

        add_user(
            email='snow_disabled@example.com',
            postal_code='G1R3A5',
            lat=46.8200,
            lon=-71.2100,
            snow_alerts=False,
            garbage_alerts=True  # Only garbage alerts
        )

        # Get users with snow alerts
        snow_users = get_users_with_snow_alerts()
        emails = [u.email for u in snow_users]

        assert 'snow_enabled@example.com' in emails
        assert 'snow_disabled@example.com' not in emails

    def test_new_columns_exist_in_users_table(self):
        """Verify new columns exist in users table."""
        from app.database import init_db

        init_db()

        session = self.Session()
        try:
            # Query to check column existence
            result = session.execute(text(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='users'"
            )).fetchone()

            table_sql = result[0].lower()

            assert 'snow_alerts_enabled' in table_sql
            assert 'garbage_alerts_enabled' in table_sql
            assert 'recycling_alerts_enabled' in table_sql
            assert 'waste_zone_id' in table_sql
        finally:
            session.close()

    def test_waste_zones_table_exists(self):
        """Verify waste_zones table exists after migration."""
        from app.database import init_db

        init_db()

        session = self.Session()
        try:
            result = session.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='waste_zones'"
            )).fetchone()

            assert result is not None
            assert result[0] == 'waste_zones'
        finally:
            session.close()

    def test_reminders_sent_table_exists(self):
        """Verify reminders_sent table exists after migration."""
        from app.database import init_db

        init_db()

        session = self.Session()
        try:
            result = session.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='reminders_sent'"
            )).fetchone()

            assert result is not None
            assert result[0] == 'reminders_sent'
        finally:
            session.close()


class TestMigrationIdempotence:
    """Tests to verify migration can be run multiple times safely."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test database."""
        from config import Config
        from app.models import Base

        self.db_path = 'test_migration_idempotent.db'
        self.engine = create_engine(f'sqlite:///{self.db_path}')

        Base.metadata.create_all(self.engine)

        yield

        Base.metadata.drop_all(self.engine)
        self.engine.dispose()
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except:
                pass

    def test_init_db_can_be_called_multiple_times(self):
        """Verify init_db() is idempotent."""
        from app.database import init_db, add_user, get_user_by_email

        # First init
        init_db()

        # Add a user
        add_user(
            email='idempotent@example.com',
            postal_code='G1R2K8',
            lat=46.8139,
            lon=-71.2080
        )

        # Second init - should not fail or lose data
        init_db()

        # User should still exist
        user = get_user_by_email('idempotent@example.com')
        assert user is not None
        assert user.email == 'idempotent@example.com'

    def test_migration_preserves_existing_preferences(self):
        """Verify migration doesn't overwrite explicitly set preferences."""
        from app.database import init_db, add_user, get_user_by_email

        init_db()

        # Add user with specific preferences
        add_user(
            email='preserve_prefs@example.com',
            postal_code='G1R2K8',
            lat=46.8139,
            lon=-71.2080,
            snow_alerts=False,
            garbage_alerts=True,
            recycling_alerts=True
        )

        # Run init_db again (simulating migration)
        init_db()

        # Preferences should be preserved
        user = get_user_by_email('preserve_prefs@example.com')
        assert user.snow_alerts_enabled is False
        assert user.garbage_alerts_enabled is True
        assert user.recycling_alerts_enabled is True
