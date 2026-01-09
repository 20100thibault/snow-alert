"""
End-to-end tests for the complete subscription and reminder flow.
"""

import pytest
import os
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

# Set test environment before imports
os.environ['EMAIL_ENABLED'] = 'false'
os.environ['DATABASE_PATH'] = 'test_e2e.db'


class TestE2ESubscriptionFlow:
    """Tests for Task 6.1: End-to-end subscription flow."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test database and app."""
        from app import create_app
        from app.database import init_db, get_session
        from app.models import Base, User, WasteZone, ReminderSent

        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

        # Initialize fresh database
        init_db()

        yield

        # Clean up
        session = get_session()
        try:
            session.query(ReminderSent).delete()
            session.query(User).delete()
            session.query(WasteZone).delete()
            session.commit()
        except:
            session.rollback()
        finally:
            session.close()

    def test_user_can_subscribe_with_all_three_alerts(self):
        """Verify user can subscribe with all three alerts enabled."""
        with patch('app.routes.geocode_postal_code') as mock_geocode:
            mock_geocode.return_value = {'lat': 46.8139, 'lon': -71.2080}

            with patch('app.routes.get_schedule') as mock_schedule:
                mock_schedule.return_value = {
                    'garbage_day': 'monday',
                    'recycling_week': 'even',
                    'zone_id': 1
                }

                response = self.client.post('/subscribe', json={
                    'email': 'e2e_test@example.com',
                    'postal_code': 'G1R 2K8',
                    'preferences': {
                        'snow_alerts': True,
                        'garbage_alerts': True,
                        'recycling_alerts': True
                    }
                })

                assert response.status_code == 201
                data = response.get_json()
                assert data['success'] is True
                assert 'next_events' in data

    def test_schedule_is_scraped_and_cached_on_subscription(self):
        """Verify schedule is scraped when waste alerts enabled."""
        with patch('app.routes.geocode_postal_code') as mock_geocode:
            mock_geocode.return_value = {'lat': 46.8139, 'lon': -71.2080}

            with patch('app.routes.get_schedule') as mock_schedule:
                mock_schedule.return_value = {
                    'garbage_day': 'tuesday',
                    'recycling_week': 'odd',
                    'zone_id': 1
                }

                response = self.client.post('/subscribe', json={
                    'email': 'e2e_cache@example.com',
                    'postal_code': 'G1R 2K8',
                    'preferences': {
                        'snow_alerts': False,
                        'garbage_alerts': True,
                        'recycling_alerts': True
                    }
                })

                assert response.status_code == 201
                mock_schedule.assert_called_once()

                data = response.get_json()
                assert 'waste_schedule' in data
                assert data['waste_schedule']['garbage_day'] == 'tuesday'
                assert data['waste_schedule']['recycling_week'] == 'odd'

    def test_user_record_has_correct_preferences(self):
        """Verify user record is stored with correct preferences."""
        from app.database import get_user_by_email

        with patch('app.routes.geocode_postal_code') as mock_geocode:
            mock_geocode.return_value = {'lat': 46.8139, 'lon': -71.2080}

            with patch('app.routes.get_schedule') as mock_schedule:
                mock_schedule.return_value = {
                    'garbage_day': 'wednesday',
                    'recycling_week': 'even',
                    'zone_id': 2
                }

                self.client.post('/subscribe', json={
                    'email': 'e2e_prefs@example.com',
                    'postal_code': 'G1R 3A5',
                    'preferences': {
                        'snow_alerts': True,
                        'garbage_alerts': True,
                        'recycling_alerts': False
                    }
                })

                user = get_user_by_email('e2e_prefs@example.com')
                assert user is not None
                assert user.snow_alerts_enabled is True
                assert user.garbage_alerts_enabled is True
                assert user.recycling_alerts_enabled is False
                assert user.postal_code == 'G1R3A5'

    def test_snow_alerts_work_for_enabled_users(self):
        """Verify snow alert check works for users with snow alerts enabled."""
        from app.database import add_user, get_users_with_snow_alerts

        # Add user with snow alerts enabled
        add_user(
            email='snow_e2e@example.com',
            postal_code='G1R2K8',
            lat=46.8139,
            lon=-71.2080,
            snow_alerts=True,
            garbage_alerts=False,
            recycling_alerts=False
        )

        users = get_users_with_snow_alerts()
        emails = [u.email for u in users]
        assert 'snow_e2e@example.com' in emails

    def test_waste_reminders_work_for_enabled_users(self):
        """Verify waste reminder processing works for enabled users."""
        from app.database import add_user, add_waste_zone
        from app.waste_service import process_waste_reminders

        # Create waste zone
        zone_id = add_waste_zone('G1R2K8', 'tuesday', 'even')

        # Add user with garbage alerts enabled
        add_user(
            email='waste_e2e@example.com',
            postal_code='G1R2K8',
            lat=46.8139,
            lon=-71.2080,
            snow_alerts=False,
            garbage_alerts=True,
            recycling_alerts=True,
            waste_zone_id=zone_id
        )

        # Mock the email sending
        with patch('app.email_service.send_garbage_reminder', return_value=True):
            with patch('app.email_service.send_recycling_reminder', return_value=True):
                # Process reminders for a Monday (so Tuesday = tomorrow = garbage day)
                # Jan 6, 2025 is Monday
                result = process_waste_reminders(date(2025, 1, 6))

                # Should have processed without errors
                assert 'garbage_sent' in result
                assert 'recycling_sent' in result
                assert 'errors' in result

    def test_complete_flow_subscribe_check_unsubscribe(self):
        """Verify complete flow: subscribe, check status, unsubscribe."""
        with patch('app.routes.geocode_postal_code') as mock_geocode:
            mock_geocode.return_value = {'lat': 46.8139, 'lon': -71.2080}

            with patch('app.routes.get_schedule') as mock_schedule:
                mock_schedule.return_value = {
                    'garbage_day': 'friday',
                    'recycling_week': 'odd',
                    'zone_id': 3
                }

                # Step 1: Subscribe
                subscribe_response = self.client.post('/subscribe', json={
                    'email': 'complete_flow@example.com',
                    'postal_code': 'G1R 2K8',
                    'preferences': {
                        'snow_alerts': True,
                        'garbage_alerts': True,
                        'recycling_alerts': True
                    }
                })
                assert subscribe_response.status_code == 201

                # Step 2: Check status
                status_response = self.client.get('/subscriber/complete_flow@example.com')
                assert status_response.status_code == 200
                status_data = status_response.get_json()
                assert status_data['preferences']['snow_alerts'] is True
                assert status_data['preferences']['garbage_alerts'] is True
                assert status_data['preferences']['recycling_alerts'] is True

                # Step 3: Unsubscribe
                unsub_response = self.client.post('/unsubscribe', json={
                    'email': 'complete_flow@example.com'
                })
                assert unsub_response.status_code == 200

                # Step 4: Verify unsubscribed
                verify_response = self.client.get('/subscriber/complete_flow@example.com')
                assert verify_response.status_code == 404


class TestE2EPreferencesUpdate:
    """Tests for preferences update flow."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test database and app."""
        from app import create_app
        from app.database import init_db, get_session
        from app.models import User, WasteZone, ReminderSent

        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

        init_db()

        yield

        session = get_session()
        try:
            session.query(ReminderSent).delete()
            session.query(User).delete()
            session.query(WasteZone).delete()
            session.commit()
        except:
            session.rollback()
        finally:
            session.close()

    def test_can_update_preferences_after_subscription(self):
        """Verify user can update preferences after initial subscription."""
        with patch('app.routes.geocode_postal_code') as mock_geocode:
            mock_geocode.return_value = {'lat': 46.8139, 'lon': -71.2080}

            with patch('app.routes.get_schedule') as mock_schedule:
                mock_schedule.return_value = {
                    'garbage_day': 'monday',
                    'recycling_week': 'even',
                    'zone_id': 1
                }

                # Initial subscription with only snow alerts
                self.client.post('/subscribe', json={
                    'email': 'update_prefs@example.com',
                    'postal_code': 'G1R 2K8',
                    'preferences': {
                        'snow_alerts': True,
                        'garbage_alerts': False,
                        'recycling_alerts': False
                    }
                })

                # Update to add waste alerts
                update_response = self.client.put('/preferences', json={
                    'email': 'update_prefs@example.com',
                    'snow_alerts': True,
                    'garbage_alerts': True,
                    'recycling_alerts': True
                })

                assert update_response.status_code == 200

                # Verify update
                status_response = self.client.get('/subscriber/update_prefs@example.com')
                data = status_response.get_json()
                assert data['preferences']['garbage_alerts'] is True
                assert data['preferences']['recycling_alerts'] is True
