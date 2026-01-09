import pytest
import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Use test database
os.environ['DATABASE_PATH'] = 'test_routes.db'
os.environ['EMAIL_ENABLED'] = 'false'

from app import create_app
from app.database import init_db, remove_user, get_user_by_email
from app.models import Base
from app.database import engine


@pytest.fixture
def app():
    """Create test app."""
    application = create_app()
    application.config['TESTING'] = True
    return application


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture(autouse=True)
def setup_teardown():
    """Create fresh database for each test."""
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


class TestIndex:
    def test_index_returns_200(self, client):
        response = client.get('/')
        assert response.status_code == 200

    def test_index_returns_html(self, client):
        response = client.get('/')
        assert b'Snow Alert' in response.data


class TestSubscribe:
    @patch('app.routes.geocode_postal_code')
    @patch('app.routes.send_welcome_email')
    def test_subscribe_success(self, mock_email, mock_geocode, client):
        mock_geocode.return_value = {'lat': 46.8, 'lon': -71.2}
        mock_email.return_value = True

        response = client.post('/subscribe', json={
            'email': 'test@example.com',
            'postal_code': 'G1R2K8'
        })

        assert response.status_code == 201
        assert response.json['success'] is True

    def test_subscribe_missing_email(self, client):
        response = client.post('/subscribe', json={
            'postal_code': 'G1R2K8'
        })

        assert response.status_code == 400
        assert 'Email is required' in response.json['error']

    def test_subscribe_invalid_email(self, client):
        response = client.post('/subscribe', json={
            'email': 'not-an-email',
            'postal_code': 'G1R2K8'
        })

        assert response.status_code == 400
        assert 'Invalid email' in response.json['error']

    def test_subscribe_missing_postal_code(self, client):
        response = client.post('/subscribe', json={
            'email': 'test@example.com'
        })

        assert response.status_code == 400
        assert 'Postal code is required' in response.json['error']

    def test_subscribe_invalid_postal_code(self, client):
        response = client.post('/subscribe', json={
            'email': 'test@example.com',
            'postal_code': '12345'
        })

        assert response.status_code == 400
        assert 'Invalid postal code' in response.json['error']

    @patch('app.routes.geocode_postal_code')
    @patch('app.routes.send_welcome_email')
    def test_subscribe_existing_email_updates_preferences(self, mock_email, mock_geocode, client):
        """Existing email should update preferences, not reject."""
        mock_geocode.return_value = {'lat': 46.8, 'lon': -71.2}
        mock_email.return_value = True

        # First subscription
        client.post('/subscribe', json={
            'email': 'duplicate@example.com',
            'postal_code': 'G1R2K8'
        })

        # Second subscription updates instead of rejecting
        response = client.post('/subscribe', json={
            'email': 'duplicate@example.com',
            'postal_code': 'G1V1J8'
        })

        assert response.status_code == 200  # Update, not error
        assert response.json['success'] is True


# ============== Task 3.1: Subscribe with Preferences Tests ==============

class TestSubscribeWithPreferences:
    """Test /subscribe endpoint accepts preferences (Task 3.1)"""

    @patch('app.routes.geocode_postal_code')
    @patch('app.routes.send_welcome_email')
    def test_subscribe_accepts_preferences_object(self, mock_email, mock_geocode, client):
        """Verify /subscribe accepts preferences object in JSON body."""
        mock_geocode.return_value = {'lat': 46.8, 'lon': -71.2}

        response = client.post('/subscribe', json={
            'email': 'pref1@example.com',
            'postal_code': 'G1R2K8',
            'preferences': {
                'snow_alerts': True,
                'garbage_alerts': True,
                'recycling_alerts': False
            }
        })

        assert response.status_code == 201
        data = response.get_json()
        assert data['success'] is True
        assert 'preferences' in data

    @patch('app.routes.geocode_postal_code')
    @patch('app.routes.send_welcome_email')
    def test_subscribe_stores_snow_alerts_preference(self, mock_email, mock_geocode, client):
        """Verify snow_alerts_enabled is stored correctly."""
        mock_geocode.return_value = {'lat': 46.8, 'lon': -71.2}

        client.post('/subscribe', json={
            'email': 'pref2@example.com',
            'postal_code': 'G1R2K8',
            'preferences': {
                'snow_alerts': False,
                'garbage_alerts': True,
                'recycling_alerts': False
            }
        })

        user = get_user_by_email('pref2@example.com')
        assert user.snow_alerts_enabled is False

    @patch('app.routes.geocode_postal_code')
    @patch('app.routes.send_welcome_email')
    def test_subscribe_stores_garbage_alerts_preference(self, mock_email, mock_geocode, client):
        """Verify garbage_alerts_enabled is stored correctly."""
        mock_geocode.return_value = {'lat': 46.8, 'lon': -71.2}

        client.post('/subscribe', json={
            'email': 'pref3@example.com',
            'postal_code': 'G1R2K8',
            'preferences': {
                'snow_alerts': True,
                'garbage_alerts': True,
                'recycling_alerts': False
            }
        })

        user = get_user_by_email('pref3@example.com')
        assert user.garbage_alerts_enabled is True

    @patch('app.routes.geocode_postal_code')
    @patch('app.routes.send_welcome_email')
    def test_subscribe_stores_recycling_alerts_preference(self, mock_email, mock_geocode, client):
        """Verify recycling_alerts_enabled is stored correctly."""
        mock_geocode.return_value = {'lat': 46.8, 'lon': -71.2}

        client.post('/subscribe', json={
            'email': 'pref4@example.com',
            'postal_code': 'G1R2K8',
            'preferences': {
                'snow_alerts': True,
                'garbage_alerts': False,
                'recycling_alerts': True
            }
        })

        user = get_user_by_email('pref4@example.com')
        assert user.recycling_alerts_enabled is True

    @patch('app.routes.geocode_postal_code')
    @patch('app.routes.send_welcome_email')
    def test_subscribe_defaults_snow_true_when_no_preferences(self, mock_email, mock_geocode, client):
        """Verify snow_alerts defaults to true if no preferences provided."""
        mock_geocode.return_value = {'lat': 46.8, 'lon': -71.2}

        client.post('/subscribe', json={
            'email': 'pref5@example.com',
            'postal_code': 'G1R2K8'
        })

        user = get_user_by_email('pref5@example.com')
        assert user.snow_alerts_enabled is True

    @patch('app.routes.geocode_postal_code')
    @patch('app.routes.send_welcome_email')
    def test_subscribe_defaults_garbage_false_when_no_preferences(self, mock_email, mock_geocode, client):
        """Verify garbage_alerts defaults to false if no preferences provided."""
        mock_geocode.return_value = {'lat': 46.8, 'lon': -71.2}

        client.post('/subscribe', json={
            'email': 'pref6@example.com',
            'postal_code': 'G1R2K8'
        })

        user = get_user_by_email('pref6@example.com')
        assert user.garbage_alerts_enabled is False

    @patch('app.routes.geocode_postal_code')
    @patch('app.routes.send_welcome_email')
    def test_subscribe_defaults_recycling_false_when_no_preferences(self, mock_email, mock_geocode, client):
        """Verify recycling_alerts defaults to false if no preferences provided."""
        mock_geocode.return_value = {'lat': 46.8, 'lon': -71.2}

        client.post('/subscribe', json={
            'email': 'pref7@example.com',
            'postal_code': 'G1R2K8'
        })

        user = get_user_by_email('pref7@example.com')
        assert user.recycling_alerts_enabled is False

    @patch('app.routes.geocode_postal_code')
    @patch('app.routes.send_welcome_email')
    def test_subscribe_returns_preferences_in_response(self, mock_email, mock_geocode, client):
        """Verify response includes preferences object."""
        mock_geocode.return_value = {'lat': 46.8, 'lon': -71.2}

        response = client.post('/subscribe', json={
            'email': 'pref8@example.com',
            'postal_code': 'G1R2K8',
            'preferences': {
                'snow_alerts': True,
                'garbage_alerts': True,
                'recycling_alerts': True
            }
        })

        data = response.get_json()
        assert data['preferences']['snow_alerts'] is True
        assert data['preferences']['garbage_alerts'] is True
        assert data['preferences']['recycling_alerts'] is True

    @patch('app.routes.geocode_postal_code')
    def test_subscribe_requires_at_least_one_alert_type(self, mock_geocode, client):
        """Verify /subscribe returns 400 when no alert types are enabled."""
        mock_geocode.return_value = {'lat': 46.8, 'lon': -71.2}

        response = client.post('/subscribe', json={
            'email': 'noalerts@example.com',
            'postal_code': 'G1R2K8',
            'preferences': {
                'snow_alerts': False,
                'garbage_alerts': False,
                'recycling_alerts': False
            }
        })

        assert response.status_code == 400
        assert 'At least one alert type must be enabled' in response.json['error']


# ============== Task 3.4: Existing User Re-subscription Tests ==============

class TestExistingUserResubscription:
    """Test handling of existing user re-subscription (Task 3.4)"""

    @patch('app.routes.geocode_postal_code')
    @patch('app.routes.send_welcome_email')
    def test_subscribe_updates_existing_user(self, mock_email, mock_geocode, client):
        """Verify existing user preferences are updated, not duplicated."""
        mock_geocode.return_value = {'lat': 46.8, 'lon': -71.2}

        # First subscription
        client.post('/subscribe', json={
            'email': 'resub1@example.com',
            'postal_code': 'G1R2K8',
            'preferences': {
                'snow_alerts': True,
                'garbage_alerts': False,
                'recycling_alerts': False
            }
        })

        # Second subscription with different preferences
        response = client.post('/subscribe', json={
            'email': 'resub1@example.com',
            'postal_code': 'G1R2K8',
            'preferences': {
                'snow_alerts': False,
                'garbage_alerts': True,
                'recycling_alerts': True
            }
        })

        assert response.status_code == 200  # Update, not create

        user = get_user_by_email('resub1@example.com')
        assert user.snow_alerts_enabled is False
        assert user.garbage_alerts_enabled is True
        assert user.recycling_alerts_enabled is True

    @patch('app.routes.geocode_postal_code')
    @patch('app.routes.send_welcome_email')
    def test_subscribe_returns_200_for_update(self, mock_email, mock_geocode, client):
        """Verify 200 status for update, 201 for new subscription."""
        mock_geocode.return_value = {'lat': 46.8, 'lon': -71.2}

        # First subscription - should return 201
        response1 = client.post('/subscribe', json={
            'email': 'resub2@example.com',
            'postal_code': 'G1R2K8'
        })
        assert response1.status_code == 201

        # Second subscription - should return 200
        response2 = client.post('/subscribe', json={
            'email': 'resub2@example.com',
            'postal_code': 'G1R2K8',
            'preferences': {'garbage_alerts': True}
        })
        assert response2.status_code == 200

    @patch('app.routes.geocode_postal_code')
    @patch('app.routes.send_welcome_email')
    def test_subscribe_updates_postal_code_for_existing_user(self, mock_email, mock_geocode, client):
        """Verify postal code can be updated for existing user."""
        mock_geocode.return_value = {'lat': 46.8, 'lon': -71.2}

        # First subscription
        client.post('/subscribe', json={
            'email': 'resub3@example.com',
            'postal_code': 'G1R2K8'
        })

        # Update with different postal code
        mock_geocode.return_value = {'lat': 46.9, 'lon': -71.3}
        client.post('/subscribe', json={
            'email': 'resub3@example.com',
            'postal_code': 'G1V3H5'
        })

        user = get_user_by_email('resub3@example.com')
        assert user.postal_code == 'G1V3H5'


# ============== Task 3.2: Waste Schedule Scrape on Subscription Tests ==============

class TestWasteScrapeOnSubscription:
    """Test waste schedule scraping when waste alerts enabled (Task 3.2)"""

    @patch('app.routes.get_schedule')
    @patch('app.routes.geocode_postal_code')
    @patch('app.routes.send_welcome_email')
    def test_scrapes_schedule_when_garbage_alerts_enabled(self, mock_email, mock_geocode, mock_scrape, client):
        """Verify schedule is scraped when garbage_alerts=true."""
        mock_geocode.return_value = {'lat': 46.8, 'lon': -71.2}
        mock_scrape.return_value = {
            'garbage_day': 'monday',
            'recycling_week': 'odd',
            'zone_id': 1
        }

        client.post('/subscribe', json={
            'email': 'waste1@example.com',
            'postal_code': 'G1R2K8',
            'preferences': {
                'snow_alerts': False,
                'garbage_alerts': True,
                'recycling_alerts': False
            }
        })

        mock_scrape.assert_called_once_with('G1R2K8')

    @patch('app.routes.get_schedule')
    @patch('app.routes.geocode_postal_code')
    @patch('app.routes.send_welcome_email')
    def test_scrapes_schedule_when_recycling_alerts_enabled(self, mock_email, mock_geocode, mock_scrape, client):
        """Verify schedule is scraped when recycling_alerts=true."""
        mock_geocode.return_value = {'lat': 46.8, 'lon': -71.2}
        mock_scrape.return_value = {
            'garbage_day': 'tuesday',
            'recycling_week': 'even',
            'zone_id': 2
        }

        client.post('/subscribe', json={
            'email': 'waste2@example.com',
            'postal_code': 'G1R2K8',
            'preferences': {
                'snow_alerts': True,
                'garbage_alerts': False,
                'recycling_alerts': True
            }
        })

        mock_scrape.assert_called_once_with('G1R2K8')

    @patch('app.routes.get_schedule')
    @patch('app.routes.geocode_postal_code')
    @patch('app.routes.send_welcome_email')
    def test_does_not_scrape_when_waste_alerts_disabled(self, mock_email, mock_geocode, mock_scrape, client):
        """Verify schedule is NOT scraped when both waste alerts are false."""
        mock_geocode.return_value = {'lat': 46.8, 'lon': -71.2}

        client.post('/subscribe', json={
            'email': 'waste3@example.com',
            'postal_code': 'G1R2K8',
            'preferences': {
                'snow_alerts': True,
                'garbage_alerts': False,
                'recycling_alerts': False
            }
        })

        mock_scrape.assert_not_called()

    @patch('app.routes.get_schedule')
    @patch('app.routes.geocode_postal_code')
    @patch('app.routes.send_welcome_email')
    def test_links_user_to_waste_zone_after_scrape(self, mock_email, mock_geocode, mock_scrape, client):
        """Verify user is linked to waste_zone_id after scrape."""
        mock_geocode.return_value = {'lat': 46.8, 'lon': -71.2}
        mock_scrape.return_value = {
            'garbage_day': 'wednesday',
            'recycling_week': 'odd',
            'zone_id': 5
        }

        client.post('/subscribe', json={
            'email': 'waste4@example.com',
            'postal_code': 'G1R2K8',
            'preferences': {
                'snow_alerts': True,
                'garbage_alerts': True,
                'recycling_alerts': True
            }
        })

        user = get_user_by_email('waste4@example.com')
        assert user.waste_zone_id == 5

    @patch('app.routes.get_schedule')
    @patch('app.routes.geocode_postal_code')
    @patch('app.routes.send_welcome_email')
    def test_returns_waste_schedule_in_response(self, mock_email, mock_geocode, mock_scrape, client):
        """Verify response includes waste schedule when scraped."""
        mock_geocode.return_value = {'lat': 46.8, 'lon': -71.2}
        mock_scrape.return_value = {
            'garbage_day': 'thursday',
            'recycling_week': 'even',
            'zone_id': 3
        }

        response = client.post('/subscribe', json={
            'email': 'waste5@example.com',
            'postal_code': 'G1R2K8',
            'preferences': {
                'snow_alerts': False,
                'garbage_alerts': True,
                'recycling_alerts': True
            }
        })

        data = response.get_json()
        assert 'waste_schedule' in data
        assert data['waste_schedule']['garbage_day'] == 'thursday'
        assert data['waste_schedule']['recycling_week'] == 'even'

    @patch('app.routes.get_schedule')
    @patch('app.routes.geocode_postal_code')
    @patch('app.routes.send_welcome_email')
    def test_subscription_succeeds_even_if_scrape_fails(self, mock_email, mock_geocode, mock_scrape, client):
        """Verify subscription succeeds even if waste scrape fails."""
        mock_geocode.return_value = {'lat': 46.8, 'lon': -71.2}
        mock_scrape.return_value = None  # Scrape failed

        response = client.post('/subscribe', json={
            'email': 'waste6@example.com',
            'postal_code': 'G1R2K8',
            'preferences': {
                'snow_alerts': True,
                'garbage_alerts': True,
                'recycling_alerts': False
            }
        })

        assert response.status_code == 201
        assert response.get_json()['success'] is True

        user = get_user_by_email('waste6@example.com')
        assert user is not None
        assert user.waste_zone_id is None  # No zone linked

    @patch('app.routes.get_schedule')
    @patch('app.routes.geocode_postal_code')
    @patch('app.routes.send_welcome_email')
    def test_subscription_succeeds_even_if_scrape_raises_exception(self, mock_email, mock_geocode, mock_scrape, client):
        """Verify subscription succeeds even if waste scrape raises exception."""
        mock_geocode.return_value = {'lat': 46.8, 'lon': -71.2}
        mock_scrape.side_effect = Exception("Network error")

        response = client.post('/subscribe', json={
            'email': 'waste7@example.com',
            'postal_code': 'G1R2K8',
            'preferences': {
                'snow_alerts': True,
                'garbage_alerts': True,
                'recycling_alerts': True
            }
        })

        assert response.status_code == 201
        assert response.get_json()['success'] is True

    @patch('app.routes.get_schedule')
    @patch('app.routes.geocode_postal_code')
    @patch('app.routes.send_welcome_email')
    def test_updates_existing_user_waste_zone(self, mock_email, mock_geocode, mock_scrape, client):
        """Verify existing user's waste_zone_id is updated when enabling waste alerts."""
        mock_geocode.return_value = {'lat': 46.8, 'lon': -71.2}

        # First subscription without waste alerts
        client.post('/subscribe', json={
            'email': 'waste8@example.com',
            'postal_code': 'G1R2K8',
            'preferences': {
                'snow_alerts': True,
                'garbage_alerts': False,
                'recycling_alerts': False
            }
        })

        user = get_user_by_email('waste8@example.com')
        assert user.waste_zone_id is None

        # Update to enable waste alerts
        mock_scrape.return_value = {
            'garbage_day': 'friday',
            'recycling_week': 'odd',
            'zone_id': 10
        }

        client.post('/subscribe', json={
            'email': 'waste8@example.com',
            'postal_code': 'G1R2K8',
            'preferences': {
                'snow_alerts': True,
                'garbage_alerts': True,
                'recycling_alerts': False
            }
        })

        user = get_user_by_email('waste8@example.com')
        assert user.waste_zone_id == 10


# ============== Task 3.3: Next Events in Response Tests ==============

class TestNextEventsInResponse:
    """Test next_events in subscribe response (Task 3.3)"""

    @patch('app.routes.check_postal_code')
    @patch('app.routes.get_schedule')
    @patch('app.routes.geocode_postal_code')
    @patch('app.routes.send_welcome_email')
    def test_response_includes_next_events_object(self, mock_email, mock_geocode, mock_scrape, mock_check, client):
        """Verify response includes next_events object."""
        mock_geocode.return_value = {'lat': 46.8, 'lon': -71.2}
        mock_check.return_value = (False, [])
        mock_scrape.return_value = {
            'garbage_day': 'monday',
            'recycling_week': 'odd',
            'zone_id': 1
        }

        response = client.post('/subscribe', json={
            'email': 'events1@example.com',
            'postal_code': 'G1R2K8',
            'preferences': {
                'snow_alerts': True,
                'garbage_alerts': True,
                'recycling_alerts': True
            }
        })

        data = response.get_json()
        assert 'next_events' in data

    @patch('app.routes.check_postal_code')
    @patch('app.routes.get_schedule')
    @patch('app.routes.geocode_postal_code')
    @patch('app.routes.send_welcome_email')
    def test_next_events_has_snow_removal_key(self, mock_email, mock_geocode, mock_scrape, mock_check, client):
        """Verify next_events has snow_removal key."""
        mock_geocode.return_value = {'lat': 46.8, 'lon': -71.2}
        mock_check.return_value = (False, [])

        response = client.post('/subscribe', json={
            'email': 'events2@example.com',
            'postal_code': 'G1R2K8'
        })

        data = response.get_json()
        assert 'snow_removal' in data['next_events']

    @patch('app.routes.check_postal_code')
    @patch('app.routes.get_schedule')
    @patch('app.routes.geocode_postal_code')
    @patch('app.routes.send_welcome_email')
    def test_next_events_has_garbage_key(self, mock_email, mock_geocode, mock_scrape, mock_check, client):
        """Verify next_events has garbage key."""
        mock_geocode.return_value = {'lat': 46.8, 'lon': -71.2}
        mock_check.return_value = (False, [])
        mock_scrape.return_value = {
            'garbage_day': 'tuesday',
            'recycling_week': 'even',
            'zone_id': 2
        }

        response = client.post('/subscribe', json={
            'email': 'events3@example.com',
            'postal_code': 'G1R2K8',
            'preferences': {'garbage_alerts': True}
        })

        data = response.get_json()
        assert 'garbage' in data['next_events']

    @patch('app.routes.check_postal_code')
    @patch('app.routes.get_schedule')
    @patch('app.routes.geocode_postal_code')
    @patch('app.routes.send_welcome_email')
    def test_next_events_has_recycling_key(self, mock_email, mock_geocode, mock_scrape, mock_check, client):
        """Verify next_events has recycling key."""
        mock_geocode.return_value = {'lat': 46.8, 'lon': -71.2}
        mock_check.return_value = (False, [])
        mock_scrape.return_value = {
            'garbage_day': 'wednesday',
            'recycling_week': 'odd',
            'zone_id': 3
        }

        response = client.post('/subscribe', json={
            'email': 'events4@example.com',
            'postal_code': 'G1R2K8',
            'preferences': {'recycling_alerts': True}
        })

        data = response.get_json()
        assert 'recycling' in data['next_events']

    @patch('app.routes.check_postal_code')
    @patch('app.routes.get_schedule')
    @patch('app.routes.geocode_postal_code')
    @patch('app.routes.send_welcome_email')
    def test_next_events_snow_removal_is_date_when_active(self, mock_email, mock_geocode, mock_scrape, mock_check, client):
        """Verify snow_removal is date when operation is active."""
        mock_geocode.return_value = {'lat': 46.8, 'lon': -71.2}
        mock_check.return_value = (True, ['Rue Test'])  # Active operation

        response = client.post('/subscribe', json={
            'email': 'events5@example.com',
            'postal_code': 'G1R2K8'
        })

        data = response.get_json()
        snow_date = data['next_events']['snow_removal']
        assert snow_date is not None
        # Verify ISO format (YYYY-MM-DD)
        import re
        assert re.match(r'^\d{4}-\d{2}-\d{2}$', snow_date)

    @patch('app.routes.check_postal_code')
    @patch('app.routes.get_schedule')
    @patch('app.routes.geocode_postal_code')
    @patch('app.routes.send_welcome_email')
    def test_next_events_snow_removal_is_null_when_no_operation(self, mock_email, mock_geocode, mock_scrape, mock_check, client):
        """Verify snow_removal is null when no operation."""
        mock_geocode.return_value = {'lat': 46.8, 'lon': -71.2}
        mock_check.return_value = (False, [])  # No active operation

        response = client.post('/subscribe', json={
            'email': 'events6@example.com',
            'postal_code': 'G1R2K8'
        })

        data = response.get_json()
        assert data['next_events']['snow_removal'] is None

    @patch('app.routes.check_postal_code')
    @patch('app.routes.get_schedule')
    @patch('app.routes.geocode_postal_code')
    @patch('app.routes.send_welcome_email')
    def test_next_events_garbage_date_in_iso_format(self, mock_email, mock_geocode, mock_scrape, mock_check, client):
        """Verify garbage date is in ISO format (YYYY-MM-DD)."""
        mock_geocode.return_value = {'lat': 46.8, 'lon': -71.2}
        mock_check.return_value = (False, [])
        mock_scrape.return_value = {
            'garbage_day': 'thursday',
            'recycling_week': 'even',
            'zone_id': 4
        }

        response = client.post('/subscribe', json={
            'email': 'events7@example.com',
            'postal_code': 'G1R2K8',
            'preferences': {'garbage_alerts': True}
        })

        data = response.get_json()
        garbage_date = data['next_events']['garbage']
        assert garbage_date is not None
        import re
        assert re.match(r'^\d{4}-\d{2}-\d{2}$', garbage_date)

    @patch('app.routes.check_postal_code')
    @patch('app.routes.get_schedule')
    @patch('app.routes.geocode_postal_code')
    @patch('app.routes.send_welcome_email')
    def test_next_events_recycling_date_in_iso_format(self, mock_email, mock_geocode, mock_scrape, mock_check, client):
        """Verify recycling date is in ISO format (YYYY-MM-DD)."""
        mock_geocode.return_value = {'lat': 46.8, 'lon': -71.2}
        mock_check.return_value = (False, [])
        mock_scrape.return_value = {
            'garbage_day': 'friday',
            'recycling_week': 'odd',
            'zone_id': 5
        }

        response = client.post('/subscribe', json={
            'email': 'events8@example.com',
            'postal_code': 'G1R2K8',
            'preferences': {'recycling_alerts': True}
        })

        data = response.get_json()
        recycling_date = data['next_events']['recycling']
        assert recycling_date is not None
        import re
        assert re.match(r'^\d{4}-\d{2}-\d{2}$', recycling_date)

    @patch('app.routes.check_postal_code')
    @patch('app.routes.geocode_postal_code')
    @patch('app.routes.send_welcome_email')
    def test_next_events_garbage_is_null_without_waste_alerts(self, mock_email, mock_geocode, mock_check, client):
        """Verify garbage is null when waste alerts not enabled."""
        mock_geocode.return_value = {'lat': 46.8, 'lon': -71.2}
        mock_check.return_value = (False, [])

        response = client.post('/subscribe', json={
            'email': 'events9@example.com',
            'postal_code': 'G1R2K8',
            'preferences': {
                'snow_alerts': True,
                'garbage_alerts': False,
                'recycling_alerts': False
            }
        })

        data = response.get_json()
        assert data['next_events']['garbage'] is None
        assert data['next_events']['recycling'] is None


class TestNextDateCalculations:
    """Test helper functions for date calculations."""

    def test_get_week_parity_odd(self):
        """Verify get_week_parity returns 'odd' for odd weeks."""
        from app.routes import get_week_parity
        from datetime import date

        # Week 1 of 2025 is odd
        d = date(2025, 1, 6)  # Monday of week 2
        parity = get_week_parity(d)
        assert parity == 'even'

        d = date(2025, 1, 1)  # Week 1
        parity = get_week_parity(d)
        assert parity == 'odd'

    def test_get_next_garbage_date_returns_future_date(self):
        """Verify get_next_garbage_date returns a future date."""
        from app.routes import get_next_garbage_date
        from datetime import date

        result = get_next_garbage_date('monday')
        assert result is not None
        result_date = date.fromisoformat(result)
        assert result_date > date.today()

    def test_get_next_garbage_date_returns_correct_weekday(self):
        """Verify get_next_garbage_date returns the correct weekday."""
        from app.routes import get_next_garbage_date, DAY_TO_WEEKDAY
        from datetime import date

        for day_name, weekday_num in DAY_TO_WEEKDAY.items():
            result = get_next_garbage_date(day_name)
            result_date = date.fromisoformat(result)
            assert result_date.weekday() == weekday_num

    def test_get_next_recycling_date_returns_correct_parity(self):
        """Verify get_next_recycling_date returns date with correct week parity."""
        from app.routes import get_next_recycling_date, get_week_parity
        from datetime import date

        # Test odd week
        result = get_next_recycling_date('monday', 'odd')
        result_date = date.fromisoformat(result)
        assert get_week_parity(result_date) == 'odd'

        # Test even week
        result = get_next_recycling_date('monday', 'even')
        result_date = date.fromisoformat(result)
        assert get_week_parity(result_date) == 'even'

    def test_get_next_garbage_date_invalid_day(self):
        """Verify get_next_garbage_date returns None for invalid day."""
        from app.routes import get_next_garbage_date

        result = get_next_garbage_date('invalid_day')
        assert result is None

    def test_get_next_recycling_date_invalid_week(self):
        """Verify get_next_recycling_date returns None for invalid week."""
        from app.routes import get_next_recycling_date

        result = get_next_recycling_date('monday', 'invalid')
        assert result is None


class TestPreferencesEndpoint:
    """Tests for PUT /preferences endpoint."""

    @patch('app.routes.geocode_postal_code')
    @patch('app.routes.send_welcome_email')
    def test_preferences_requires_email(self, mock_email, mock_geocode, client):
        """Verify PUT /preferences returns 400 when email is missing."""
        response = client.put('/preferences', json={
            'snow_alerts': True
        })

        assert response.status_code == 400
        assert 'Email is required' in response.json['error']

    def test_preferences_invalid_email(self, client):
        """Verify PUT /preferences returns 400 for invalid email format."""
        response = client.put('/preferences', json={
            'email': 'not-an-email',
            'snow_alerts': True
        })

        assert response.status_code == 400
        assert 'Invalid email' in response.json['error']

    def test_preferences_user_not_found(self, client):
        """Verify PUT /preferences returns 404 when user doesn't exist."""
        response = client.put('/preferences', json={
            'email': 'nonexistent@example.com',
            'snow_alerts': True
        })

        assert response.status_code == 404
        assert 'User not found' in response.json['error']

    @patch('app.routes.geocode_postal_code')
    @patch('app.routes.send_welcome_email')
    def test_preferences_updates_snow_alerts(self, mock_email, mock_geocode, client):
        """Verify PUT /preferences updates snow_alerts preference."""
        mock_geocode.return_value = {'lat': 46.8, 'lon': -71.2}
        mock_email.return_value = True

        # Subscribe first with both snow and garbage alerts
        client.post('/subscribe', json={
            'email': 'prefs@example.com',
            'postal_code': 'G1R2K8',
            'preferences': {'snow_alerts': True, 'garbage_alerts': True}
        })

        # Update preferences - disable snow but keep garbage
        response = client.put('/preferences', json={
            'email': 'prefs@example.com',
            'snow_alerts': False
        })

        assert response.status_code == 200
        assert response.json['success'] is True
        assert response.json['preferences']['snow_alerts'] is False
        assert response.json['preferences']['garbage_alerts'] is True

    @patch('app.routes.geocode_postal_code')
    @patch('app.routes.send_welcome_email')
    def test_preferences_updates_garbage_alerts(self, mock_email, mock_geocode, client):
        """Verify PUT /preferences updates garbage_alerts preference."""
        mock_geocode.return_value = {'lat': 46.8, 'lon': -71.2}
        mock_email.return_value = True

        # Subscribe first
        client.post('/subscribe', json={
            'email': 'prefs2@example.com',
            'postal_code': 'G1R2K8'
        })

        # Update preferences
        response = client.put('/preferences', json={
            'email': 'prefs2@example.com',
            'garbage_alerts': True
        })

        assert response.status_code == 200
        assert response.json['preferences']['garbage_alerts'] is True

    @patch('app.routes.geocode_postal_code')
    @patch('app.routes.send_welcome_email')
    def test_preferences_updates_recycling_alerts(self, mock_email, mock_geocode, client):
        """Verify PUT /preferences updates recycling_alerts preference."""
        mock_geocode.return_value = {'lat': 46.8, 'lon': -71.2}
        mock_email.return_value = True

        # Subscribe first
        client.post('/subscribe', json={
            'email': 'prefs3@example.com',
            'postal_code': 'G1R2K8'
        })

        # Update preferences
        response = client.put('/preferences', json={
            'email': 'prefs3@example.com',
            'recycling_alerts': True
        })

        assert response.status_code == 200
        assert response.json['preferences']['recycling_alerts'] is True

    @patch('app.routes.geocode_postal_code')
    @patch('app.routes.send_welcome_email')
    def test_preferences_preserves_unspecified_values(self, mock_email, mock_geocode, client):
        """Verify PUT /preferences preserves preferences not specified in request."""
        mock_geocode.return_value = {'lat': 46.8, 'lon': -71.2}
        mock_email.return_value = True

        # Subscribe with specific preferences
        client.post('/subscribe', json={
            'email': 'prefs4@example.com',
            'postal_code': 'G1R2K8',
            'preferences': {
                'snow_alerts': True,
                'garbage_alerts': True,
                'recycling_alerts': False
            }
        })

        # Update only snow_alerts
        response = client.put('/preferences', json={
            'email': 'prefs4@example.com',
            'snow_alerts': False
        })

        assert response.status_code == 200
        assert response.json['preferences']['snow_alerts'] is False
        assert response.json['preferences']['garbage_alerts'] is True
        assert response.json['preferences']['recycling_alerts'] is False

    @patch('app.routes.geocode_postal_code')
    @patch('app.routes.send_welcome_email')
    @patch('app.routes.get_schedule')
    def test_preferences_scrapes_schedule_when_waste_enabled(self, mock_schedule, mock_email, mock_geocode, client):
        """Verify PUT /preferences scrapes waste schedule when waste alerts newly enabled."""
        mock_geocode.return_value = {'lat': 46.8, 'lon': -71.2}
        mock_email.return_value = True
        mock_schedule.return_value = {
            'garbage_day': 'friday',
            'recycling_week': 'even',
            'zone_id': 123
        }

        # Subscribe without waste alerts
        client.post('/subscribe', json={
            'email': 'prefs5@example.com',
            'postal_code': 'G1R2K8',
            'preferences': {
                'garbage_alerts': False,
                'recycling_alerts': False
            }
        })

        # Enable garbage alerts
        response = client.put('/preferences', json={
            'email': 'prefs5@example.com',
            'garbage_alerts': True
        })

        assert response.status_code == 200
        assert response.json['preferences']['garbage_alerts'] is True
        mock_schedule.assert_called()

    @patch('app.routes.geocode_postal_code')
    @patch('app.routes.send_welcome_email')
    def test_preferences_returns_message(self, mock_email, mock_geocode, client):
        """Verify PUT /preferences returns success message."""
        mock_geocode.return_value = {'lat': 46.8, 'lon': -71.2}
        mock_email.return_value = True

        # Subscribe first
        client.post('/subscribe', json={
            'email': 'prefs6@example.com',
            'postal_code': 'G1R2K8'
        })

        # Update preferences - enable garbage_alerts (snow_alerts is already True by default)
        response = client.put('/preferences', json={
            'email': 'prefs6@example.com',
            'garbage_alerts': True
        })

        assert response.status_code == 200
        assert 'Successfully updated preferences' in response.json['message']

    @patch('app.routes.geocode_postal_code')
    @patch('app.routes.send_welcome_email')
    def test_preferences_requires_at_least_one_alert_type(self, mock_email, mock_geocode, client):
        """Verify PUT /preferences returns 400 when all alert types are disabled."""
        mock_geocode.return_value = {'lat': 46.8, 'lon': -71.2}
        mock_email.return_value = True

        # Subscribe first
        client.post('/subscribe', json={
            'email': 'prefs7@example.com',
            'postal_code': 'G1R2K8',
            'preferences': {'snow_alerts': True}
        })

        # Try to disable all alerts
        response = client.put('/preferences', json={
            'email': 'prefs7@example.com',
            'snow_alerts': False,
            'garbage_alerts': False,
            'recycling_alerts': False
        })

        assert response.status_code == 400
        assert 'At least one alert type must be enabled' in response.json['error']


class TestSubscriberEndpoint:
    """Tests for GET /subscriber/<email> endpoint."""

    def test_subscriber_invalid_email(self, client):
        """Verify GET /subscriber returns 400 for invalid email format."""
        response = client.get('/subscriber/not-an-email')

        assert response.status_code == 400
        assert 'Invalid email' in response.json['error']

    def test_subscriber_user_not_found(self, client):
        """Verify GET /subscriber returns 404 when user doesn't exist."""
        response = client.get('/subscriber/nonexistent@example.com')

        assert response.status_code == 404
        assert 'User not found' in response.json['error']

    @patch('app.routes.geocode_postal_code')
    @patch('app.routes.send_welcome_email')
    @patch('app.routes.check_postal_code')
    def test_subscriber_returns_user_info(self, mock_check, mock_email, mock_geocode, client):
        """Verify GET /subscriber returns user info."""
        mock_geocode.return_value = {'lat': 46.8, 'lon': -71.2}
        mock_email.return_value = True
        mock_check.return_value = (False, [])

        # Subscribe first
        client.post('/subscribe', json={
            'email': 'sub1@example.com',
            'postal_code': 'G1R2K8'
        })

        # Get subscriber info
        response = client.get('/subscriber/sub1@example.com')

        assert response.status_code == 200
        assert response.json['email'] == 'sub1@example.com'
        assert response.json['postal_code'] == 'G1R2K8'

    @patch('app.routes.geocode_postal_code')
    @patch('app.routes.send_welcome_email')
    @patch('app.routes.check_postal_code')
    def test_subscriber_returns_preferences(self, mock_check, mock_email, mock_geocode, client):
        """Verify GET /subscriber returns user preferences."""
        mock_geocode.return_value = {'lat': 46.8, 'lon': -71.2}
        mock_email.return_value = True
        mock_check.return_value = (False, [])

        # Subscribe with specific preferences
        client.post('/subscribe', json={
            'email': 'sub2@example.com',
            'postal_code': 'G1R2K8',
            'preferences': {
                'snow_alerts': True,
                'garbage_alerts': True,
                'recycling_alerts': False
            }
        })

        # Get subscriber info
        response = client.get('/subscriber/sub2@example.com')

        assert response.status_code == 200
        assert response.json['preferences']['snow_alerts'] is True
        assert response.json['preferences']['garbage_alerts'] is True
        assert response.json['preferences']['recycling_alerts'] is False

    @patch('app.routes.geocode_postal_code')
    @patch('app.routes.send_welcome_email')
    @patch('app.routes.check_postal_code')
    def test_subscriber_returns_active_status(self, mock_check, mock_email, mock_geocode, client):
        """Verify GET /subscriber returns active status."""
        mock_geocode.return_value = {'lat': 46.8, 'lon': -71.2}
        mock_email.return_value = True
        mock_check.return_value = (False, [])

        # Subscribe first
        client.post('/subscribe', json={
            'email': 'sub3@example.com',
            'postal_code': 'G1R2K8'
        })

        # Get subscriber info
        response = client.get('/subscriber/sub3@example.com')

        assert response.status_code == 200
        assert response.json['active'] is True

    @patch('app.routes.geocode_postal_code')
    @patch('app.routes.send_welcome_email')
    @patch('app.routes.check_postal_code')
    def test_subscriber_returns_next_events(self, mock_check, mock_email, mock_geocode, client):
        """Verify GET /subscriber returns next_events object."""
        mock_geocode.return_value = {'lat': 46.8, 'lon': -71.2}
        mock_email.return_value = True
        mock_check.return_value = (False, [])

        # Subscribe first
        client.post('/subscribe', json={
            'email': 'sub4@example.com',
            'postal_code': 'G1R2K8'
        })

        # Get subscriber info
        response = client.get('/subscriber/sub4@example.com')

        assert response.status_code == 200
        assert 'next_events' in response.json
        assert 'snow_removal' in response.json['next_events']
        assert 'garbage' in response.json['next_events']
        assert 'recycling' in response.json['next_events']

    @patch('app.routes.geocode_postal_code')
    @patch('app.routes.send_welcome_email')
    @patch('app.routes.get_schedule')
    @patch('app.routes.check_postal_code')
    @patch('app.routes.get_waste_zone_by_id')
    def test_subscriber_returns_waste_schedule(self, mock_zone, mock_check, mock_schedule, mock_email, mock_geocode, client):
        """Verify GET /subscriber returns waste_schedule if available."""
        mock_geocode.return_value = {'lat': 46.8, 'lon': -71.2}
        mock_email.return_value = True
        mock_check.return_value = (False, [])
        mock_schedule.return_value = {
            'garbage_day': 'monday',
            'recycling_week': 'odd',
            'zone_id': 42
        }
        # Return a dict as the real function does
        mock_zone.return_value = {
            'id': 42,
            'garbage_day': 'monday',
            'recycling_week': 'odd'
        }

        # Subscribe with waste alerts
        client.post('/subscribe', json={
            'email': 'sub5@example.com',
            'postal_code': 'G1R2K8',
            'preferences': {
                'garbage_alerts': True
            }
        })

        # Get subscriber info
        response = client.get('/subscriber/sub5@example.com')

        assert response.status_code == 200
        assert 'waste_schedule' in response.json
        assert response.json['waste_schedule']['garbage_day'] == 'monday'
        assert response.json['waste_schedule']['recycling_week'] == 'odd'


class TestUnsubscribe:
    @patch('app.routes.geocode_postal_code')
    @patch('app.routes.send_welcome_email')
    def test_unsubscribe_success(self, mock_email, mock_geocode, client):
        mock_geocode.return_value = {'lat': 46.8, 'lon': -71.2}
        mock_email.return_value = True

        # Subscribe first
        client.post('/subscribe', json={
            'email': 'unsub@example.com',
            'postal_code': 'G1R2K8'
        })

        # Unsubscribe
        response = client.post('/unsubscribe', json={
            'email': 'unsub@example.com'
        })

        assert response.status_code == 200
        assert response.json['success'] is True

    def test_unsubscribe_not_found(self, client):
        response = client.post('/unsubscribe', json={
            'email': 'nobody@example.com'
        })

        assert response.status_code == 404

    def test_unsubscribe_missing_email(self, client):
        response = client.post('/unsubscribe', json={})

        assert response.status_code == 400

    def test_unsubscribe_invalid_email(self, client):
        """Verify /unsubscribe returns 400 for invalid email format."""
        response = client.post('/unsubscribe', json={
            'email': 'not-an-email'
        })

        assert response.status_code == 400
        assert 'Invalid email' in response.json['error']


class TestStatus:
    @patch('app.routes.check_postal_code')
    def test_status_no_operation(self, mock_check, client):
        mock_check.return_value = (False, [])

        response = client.get('/status/G1R2K8')

        assert response.status_code == 200
        assert response.json['has_operation'] is False

    @patch('app.routes.check_postal_code')
    def test_status_with_operation(self, mock_check, client):
        mock_check.return_value = (True, ['Rue Test', 'Avenue Example'])

        response = client.get('/status/G1R2K8')

        assert response.status_code == 200
        assert response.json['has_operation'] is True
        assert len(response.json['streets_affected']) == 2

    def test_status_invalid_postal_code(self, client):
        response = client.get('/status/INVALID')

        assert response.status_code == 400


class TestScheduleEndpoint:
    """Tests for GET /schedule/<postal_code> endpoint."""

    def test_schedule_invalid_postal_code(self, client):
        """Verify GET /schedule returns 400 for invalid postal code format."""
        response = client.get('/schedule/INVALID')

        assert response.status_code == 400
        assert 'Invalid postal code' in response.json['error']

    @patch('app.routes.get_schedule')
    def test_schedule_not_found(self, mock_schedule, client):
        """Verify GET /schedule returns 404 when schedule not found."""
        mock_schedule.return_value = None

        response = client.get('/schedule/G1R2K8')

        assert response.status_code == 404
        assert 'Could not find schedule' in response.json['error']

    @patch('app.routes.get_schedule')
    def test_schedule_returns_garbage_day(self, mock_schedule, client):
        """Verify GET /schedule returns garbage_day."""
        mock_schedule.return_value = {
            'garbage_day': 'monday',
            'recycling_week': 'odd',
            'zone_id': 1
        }

        response = client.get('/schedule/G1R2K8')

        assert response.status_code == 200
        assert response.json['garbage_day'] == 'monday'

    @patch('app.routes.get_schedule')
    def test_schedule_returns_recycling_week(self, mock_schedule, client):
        """Verify GET /schedule returns recycling_week."""
        mock_schedule.return_value = {
            'garbage_day': 'tuesday',
            'recycling_week': 'even',
            'zone_id': 1
        }

        response = client.get('/schedule/G1R2K8')

        assert response.status_code == 200
        assert response.json['recycling_week'] == 'even'

    @patch('app.routes.get_schedule')
    def test_schedule_returns_next_garbage_date(self, mock_schedule, client):
        """Verify GET /schedule returns next_garbage date."""
        mock_schedule.return_value = {
            'garbage_day': 'wednesday',
            'recycling_week': 'odd',
            'zone_id': 1
        }

        response = client.get('/schedule/G1R2K8')

        assert response.status_code == 200
        assert response.json['next_garbage'] is not None
        # Verify ISO date format (YYYY-MM-DD)
        import re
        assert re.match(r'^\d{4}-\d{2}-\d{2}$', response.json['next_garbage'])

    @patch('app.routes.get_schedule')
    def test_schedule_returns_next_recycling_date(self, mock_schedule, client):
        """Verify GET /schedule returns next_recycling date."""
        mock_schedule.return_value = {
            'garbage_day': 'thursday',
            'recycling_week': 'even',
            'zone_id': 1
        }

        response = client.get('/schedule/G1R2K8')

        assert response.status_code == 200
        assert response.json['next_recycling'] is not None
        # Verify ISO date format (YYYY-MM-DD)
        import re
        assert re.match(r'^\d{4}-\d{2}-\d{2}$', response.json['next_recycling'])

    @patch('app.routes.get_schedule')
    def test_schedule_returns_normalized_postal_code(self, mock_schedule, client):
        """Verify GET /schedule returns normalized postal code."""
        mock_schedule.return_value = {
            'garbage_day': 'friday',
            'recycling_week': 'odd',
            'zone_id': 1
        }

        response = client.get('/schedule/g1r 2k8')

        assert response.status_code == 200
        assert response.json['postal_code'] == 'G1R2K8'

    @patch('app.routes.get_schedule')
    def test_schedule_handles_exception(self, mock_schedule, client):
        """Verify GET /schedule returns 500 on exception."""
        mock_schedule.side_effect = Exception("Network error")

        response = client.get('/schedule/G1R2K8')

        assert response.status_code == 500
        assert 'Failed to retrieve schedule' in response.json['error']


class TestAdminTriggerCheck:
    """Tests for GET/POST /admin/trigger-check endpoint."""

    @patch('app.scheduler.trigger_check_now')
    def test_trigger_check_returns_200(self, mock_trigger, client):
        """Verify GET /admin/trigger-check returns 200."""
        mock_trigger.return_value = {'emails_sent': 5, 'errors': 0}

        response = client.get('/admin/trigger-check')

        assert response.status_code == 200
        assert response.json['success'] is True

    @patch('app.scheduler.trigger_check_now')
    def test_trigger_check_post_returns_200(self, mock_trigger, client):
        """Verify POST /admin/trigger-check returns 200."""
        mock_trigger.return_value = {'emails_sent': 3, 'errors': 0}

        response = client.post('/admin/trigger-check')

        assert response.status_code == 200
        assert response.json['success'] is True

    @patch('app.scheduler.trigger_check_now')
    def test_trigger_check_returns_result(self, mock_trigger, client):
        """Verify /admin/trigger-check returns trigger result."""
        mock_trigger.return_value = {'emails_sent': 10, 'errors': 2}

        response = client.get('/admin/trigger-check')

        assert response.status_code == 200
        assert response.json['result']['emails_sent'] == 10
        assert response.json['result']['errors'] == 2

    @patch('app.scheduler.trigger_check_now')
    def test_trigger_check_calls_trigger_function(self, mock_trigger, client):
        """Verify /admin/trigger-check calls trigger_check_now."""
        mock_trigger.return_value = {}

        client.get('/admin/trigger-check')

        mock_trigger.assert_called_once()


class TestAdminTriggerWasteCheck:
    """Tests for GET/POST /admin/trigger-waste-check endpoint."""

    @patch('app.scheduler.trigger_waste_check_now')
    def test_trigger_waste_check_returns_200(self, mock_trigger, client):
        """Verify GET /admin/trigger-waste-check returns 200."""
        mock_trigger.return_value = {
            'garbage_sent': 5,
            'recycling_sent': 3,
            'skipped': 2,
            'errors': 0
        }

        response = client.get('/admin/trigger-waste-check')

        assert response.status_code == 200
        assert response.json['success'] is True

    @patch('app.scheduler.trigger_waste_check_now')
    def test_trigger_waste_check_post_returns_200(self, mock_trigger, client):
        """Verify POST /admin/trigger-waste-check returns 200."""
        mock_trigger.return_value = {
            'garbage_sent': 5,
            'recycling_sent': 3,
            'skipped': 2,
            'errors': 0
        }

        response = client.post('/admin/trigger-waste-check')

        assert response.status_code == 200
        assert response.json['success'] is True

    @patch('app.scheduler.trigger_waste_check_now')
    def test_trigger_waste_check_returns_result_structure(self, mock_trigger, client):
        """Verify /admin/trigger-waste-check returns expected result structure."""
        mock_trigger.return_value = {
            'garbage_sent': 10,
            'recycling_sent': 5,
            'skipped': 3,
            'errors': 1
        }

        response = client.get('/admin/trigger-waste-check')

        assert response.status_code == 200
        result = response.json['result']
        assert 'garbage_sent' in result
        assert 'recycling_sent' in result
        assert 'skipped' in result
        assert 'errors' in result
        assert result['garbage_sent'] == 10
        assert result['recycling_sent'] == 5
        assert result['skipped'] == 3
        assert result['errors'] == 1

    @patch('app.scheduler.trigger_waste_check_now')
    def test_trigger_waste_check_calls_trigger_function(self, mock_trigger, client):
        """Verify /admin/trigger-waste-check calls trigger_waste_check_now."""
        mock_trigger.return_value = {}

        client.get('/admin/trigger-waste-check')

        mock_trigger.assert_called_once()

    @patch('app.scheduler.trigger_waste_check_now')
    def test_trigger_waste_check_returns_message(self, mock_trigger, client):
        """Verify /admin/trigger-waste-check returns success message."""
        mock_trigger.return_value = {}

        response = client.get('/admin/trigger-waste-check')

        assert response.status_code == 200
        assert 'Waste check triggered successfully' in response.json['message']

    @patch('app.scheduler.trigger_waste_check_now')
    def test_trigger_waste_check_handles_missing_keys(self, mock_trigger, client):
        """Verify /admin/trigger-waste-check handles missing keys in result."""
        mock_trigger.return_value = {}  # Empty result

        response = client.get('/admin/trigger-waste-check')

        assert response.status_code == 200
        result = response.json['result']
        # Should default to 0 for missing keys
        assert result['garbage_sent'] == 0
        assert result['recycling_sent'] == 0
        assert result['skipped'] == 0
        assert result['errors'] == 0


class TestAdminJobs:
    """Tests for GET /admin/jobs endpoint."""

    @patch('app.scheduler.get_scheduled_jobs')
    def test_admin_jobs_returns_200(self, mock_jobs, client):
        """Verify GET /admin/jobs returns 200."""
        mock_jobs.return_value = []

        response = client.get('/admin/jobs')

        assert response.status_code == 200

    @patch('app.scheduler.get_scheduled_jobs')
    def test_admin_jobs_returns_jobs_list(self, mock_jobs, client):
        """Verify GET /admin/jobs returns jobs list."""
        mock_jobs.return_value = [
            {'id': 'snow_check', 'trigger': 'cron[hour=16, minute=0]'},
            {'id': 'waste_check', 'trigger': 'cron[hour=18, minute=0]'}
        ]

        response = client.get('/admin/jobs')

        assert response.status_code == 200
        assert 'jobs' in response.json
        assert len(response.json['jobs']) == 2


class TestQuickCheck:
    """Tests for GET /quick-check/<postal_code> endpoint (Task 7.1)"""

    @patch('app.routes.check_postal_code')
    @patch('app.routes.get_schedule')
    def test_quick_check_valid_postal_code(self, mock_schedule, mock_check, client):
        """Verify quick-check returns 200 for valid postal code."""
        mock_check.return_value = (False, [])
        mock_schedule.return_value = {
            'garbage_day': 'monday',
            'recycling_week': 'odd',
            'zone_id': 1
        }

        response = client.get('/quick-check/G1R2K8')

        assert response.status_code == 200

    @patch('app.routes.check_postal_code')
    @patch('app.routes.get_schedule')
    def test_quick_check_returns_snow_status(self, mock_schedule, mock_check, client):
        """Verify quick-check returns snow_status object."""
        mock_check.return_value = (True, ['Rue Test', 'Avenue Example'])
        mock_schedule.return_value = {
            'garbage_day': 'tuesday',
            'recycling_week': 'even',
            'zone_id': 2
        }

        response = client.get('/quick-check/G1R2K8')

        assert response.status_code == 200
        assert 'snow_status' in response.json
        assert response.json['snow_status']['has_operation'] is True
        assert 'Rue Test' in response.json['snow_status']['streets_affected']

    @patch('app.routes.check_postal_code')
    @patch('app.routes.get_schedule')
    def test_quick_check_returns_waste_schedule(self, mock_schedule, mock_check, client):
        """Verify quick-check returns waste_schedule object."""
        mock_check.return_value = (False, [])
        mock_schedule.return_value = {
            'garbage_day': 'wednesday',
            'recycling_week': 'odd',
            'zone_id': 3
        }

        response = client.get('/quick-check/G1R2K8')

        assert response.status_code == 200
        assert 'waste_schedule' in response.json
        assert response.json['waste_schedule']['garbage_day'] == 'wednesday'
        assert response.json['waste_schedule']['recycling_week'] == 'odd'

    @patch('app.routes.check_postal_code')
    @patch('app.routes.get_schedule')
    def test_quick_check_returns_next_events(self, mock_schedule, mock_check, client):
        """Verify quick-check returns next_events with dates."""
        mock_check.return_value = (False, [])
        mock_schedule.return_value = {
            'garbage_day': 'thursday',
            'recycling_week': 'even',
            'zone_id': 4
        }

        response = client.get('/quick-check/G1R2K8')

        assert response.status_code == 200
        assert 'next_events' in response.json
        assert 'next_garbage' in response.json['next_events']
        assert 'next_recycling' in response.json['next_events']

    @patch('app.routes.check_postal_code')
    @patch('app.routes.get_schedule')
    def test_quick_check_dates_in_iso_format(self, mock_schedule, mock_check, client):
        """Verify dates are in ISO format (YYYY-MM-DD)."""
        mock_check.return_value = (False, [])
        mock_schedule.return_value = {
            'garbage_day': 'friday',
            'recycling_week': 'odd',
            'zone_id': 5
        }

        response = client.get('/quick-check/G1R2K8')

        assert response.status_code == 200
        import re
        assert re.match(r'^\d{4}-\d{2}-\d{2}$', response.json['next_events']['next_garbage'])
        assert re.match(r'^\d{4}-\d{2}-\d{2}$', response.json['next_events']['next_recycling'])

    @patch('app.routes.check_postal_code')
    @patch('app.routes.get_schedule')
    def test_quick_check_normalizes_postal_code(self, mock_schedule, mock_check, client):
        """Verify postal code is normalized in response."""
        mock_check.return_value = (False, [])
        mock_schedule.return_value = {
            'garbage_day': 'monday',
            'recycling_week': 'odd',
            'zone_id': 1
        }

        response = client.get('/quick-check/g1r 2k8')

        assert response.status_code == 200
        assert response.json['postal_code'] == 'G1R2K8'


class TestQuickCheckInvalidPostalCode:
    """Tests for quick-check with invalid postal codes (Task 7.2)"""

    def test_quick_check_empty_postal_code(self, client):
        """Verify quick-check returns 404 for empty postal code (route not matched)."""
        response = client.get('/quick-check/')
        assert response.status_code == 404

    def test_quick_check_invalid_format(self, client):
        """Verify quick-check returns 400 for invalid format like '12345'."""
        response = client.get('/quick-check/12345')
        assert response.status_code == 400
        assert 'Invalid postal code' in response.json['error']

    def test_quick_check_incomplete_postal_code(self, client):
        """Verify quick-check returns 400 for incomplete postal code."""
        response = client.get('/quick-check/G1R')
        assert response.status_code == 400
        assert 'Invalid postal code' in response.json['error']

    def test_quick_check_error_message_explains_format(self, client):
        """Verify error message explains valid postal code format."""
        response = client.get('/quick-check/INVALID')
        assert response.status_code == 400
        assert 'G1R 2K8' in response.json['error']


class TestQuickCheckGeocodingFailure:
    """Tests for quick-check handling geocoding failures (Task 7.3)"""

    @patch('app.routes.check_postal_code')
    @patch('app.routes.get_schedule')
    def test_quick_check_returns_200_when_snow_check_fails(self, mock_schedule, mock_check, client):
        """Verify quick-check returns 200 even when snow check raises exception."""
        mock_check.side_effect = Exception("Geocoding failed")
        mock_schedule.return_value = {
            'garbage_day': 'monday',
            'recycling_week': 'odd',
            'zone_id': 1
        }

        response = client.get('/quick-check/G1R2K8')

        assert response.status_code == 200
        # Snow status should have default values
        assert response.json['snow_status']['has_operation'] is False

    @patch('app.routes.check_postal_code')
    @patch('app.routes.get_schedule')
    def test_quick_check_still_returns_waste_schedule_on_snow_failure(self, mock_schedule, mock_check, client):
        """Verify waste schedule is still returned when snow check fails."""
        mock_check.side_effect = Exception("Geocoding timeout")
        mock_schedule.return_value = {
            'garbage_day': 'tuesday',
            'recycling_week': 'even',
            'zone_id': 2
        }

        response = client.get('/quick-check/G1R2K8')

        assert response.status_code == 200
        assert 'waste_schedule' in response.json
        assert response.json['waste_schedule']['garbage_day'] == 'tuesday'


class TestQuickCheckScrapingFailure:
    """Tests for quick-check handling scraping failures (Task 7.4)"""

    @patch('app.routes.check_postal_code')
    @patch('app.routes.get_schedule')
    def test_quick_check_returns_200_when_scraping_fails(self, mock_schedule, mock_check, client):
        """Verify quick-check returns 200 with partial data when scraping fails."""
        mock_check.return_value = (True, ['Rue Test'])
        mock_schedule.side_effect = Exception("Scraping failed")

        response = client.get('/quick-check/G1R2K8')

        assert response.status_code == 200

    @patch('app.routes.check_postal_code')
    @patch('app.routes.get_schedule')
    def test_quick_check_snow_status_returned_when_scraping_fails(self, mock_schedule, mock_check, client):
        """Verify snow status is still returned when scraping fails."""
        mock_check.return_value = (True, ['Avenue Example'])
        mock_schedule.side_effect = Exception("Network timeout")

        response = client.get('/quick-check/G1R2K8')

        assert response.status_code == 200
        assert response.json['snow_status']['has_operation'] is True
        assert 'Avenue Example' in response.json['snow_status']['streets_affected']

    @patch('app.routes.check_postal_code')
    @patch('app.routes.get_schedule')
    def test_quick_check_waste_schedule_always_present(self, mock_schedule, mock_check, client):
        """Verify waste_schedule object is always in response."""
        mock_check.return_value = (False, [])
        mock_schedule.side_effect = Exception("Scraping error")

        response = client.get('/quick-check/G1R2K8')

        assert response.status_code == 200
        assert 'waste_schedule' in response.json
        assert response.json['waste_schedule']['garbage_day'] is None
        assert response.json['waste_schedule']['recycling_week'] is None

    @patch('app.routes.check_postal_code')
    @patch('app.routes.get_schedule')
    def test_quick_check_null_next_events_when_scraping_fails(self, mock_schedule, mock_check, client):
        """Verify next_events has null dates when scraping fails."""
        mock_check.return_value = (False, [])
        mock_schedule.return_value = None  # Scrape returned None

        response = client.get('/quick-check/G1R2K8')

        assert response.status_code == 200
        assert response.json['next_events']['next_garbage'] is None
        assert response.json['next_events']['next_recycling'] is None


class TestQuickCheckWasteScheduleError:
    """Tests for quick-check waste_schedule_error field (Task 8.3)"""

    @patch('app.routes.check_postal_code')
    @patch('app.routes.get_schedule')
    def test_quick_check_returns_waste_error_on_exception(self, mock_schedule, mock_check, client):
        """Verify quick-check returns waste_schedule_error when scraping raises exception."""
        mock_check.return_value = (False, [])
        mock_schedule.side_effect = Exception("Network error")

        response = client.get('/quick-check/G1R2K8')

        assert response.status_code == 200
        assert 'waste_schedule_error' in response.json
        assert 'Unable to fetch' in response.json['waste_schedule_error']

    @patch('app.routes.check_postal_code')
    @patch('app.routes.get_schedule')
    def test_quick_check_returns_waste_error_on_none(self, mock_schedule, mock_check, client):
        """Verify quick-check returns waste_schedule_error when schedule is None."""
        mock_check.return_value = (False, [])
        mock_schedule.return_value = None

        response = client.get('/quick-check/G1R2K8')

        assert response.status_code == 200
        assert 'waste_schedule_error' in response.json
        assert 'Could not find' in response.json['waste_schedule_error']

    @patch('app.routes.check_postal_code')
    @patch('app.routes.get_schedule')
    def test_quick_check_no_waste_error_on_success(self, mock_schedule, mock_check, client):
        """Verify quick-check has no waste_schedule_error on success."""
        mock_check.return_value = (False, [])
        mock_schedule.return_value = {
            'garbage_day': 'monday',
            'recycling_week': 'odd',
            'zone_id': 1
        }

        response = client.get('/quick-check/G1R2K8')

        assert response.status_code == 200
        assert 'waste_schedule_error' not in response.json

    @patch('app.routes.check_postal_code')
    @patch('app.routes.get_schedule')
    def test_quick_check_snow_still_works_with_waste_error(self, mock_schedule, mock_check, client):
        """Verify snow status is returned even when waste has error."""
        mock_check.return_value = (True, ['Rue Example'])
        mock_schedule.side_effect = Exception("Timeout")

        response = client.get('/quick-check/G1R2K8')

        assert response.status_code == 200
        assert response.json['snow_status']['has_operation'] is True
        assert 'waste_schedule_error' in response.json


# ============== Phase 10: Snow Status (Geolocation) Tests ==============

class TestSnowStatusEndpoint:
    """Tests for GET /snow-status endpoint (Task 10.1)."""

    @patch('app.routes.check_snow_removal')
    @patch('app.routes.reverse_geocode')
    def test_snow_status_valid_coords(self, mock_reverse, mock_check, client):
        """Verify endpoint returns snow status for valid coordinates."""
        mock_check.return_value = {
            'has_operation': False,
            'streets': [],
            'search_radius': 200
        }
        mock_reverse.return_value = 'Rue Saint-Jean'

        response = client.get('/snow-status?lat=46.8123&lon=-71.2145')

        assert response.status_code == 200
        assert 'has_operation' in response.json
        assert response.json['has_operation'] is False

    @patch('app.routes.check_snow_removal')
    @patch('app.routes.reverse_geocode')
    def test_snow_status_with_operation(self, mock_reverse, mock_check, client):
        """Verify endpoint returns streets when operation is active."""
        mock_check.return_value = {
            'has_operation': True,
            'streets': ['Rue Saint-Jean', 'Avenue Cartier'],
            'search_radius': 200
        }
        mock_reverse.return_value = 'Rue Saint-Jean'

        response = client.get('/snow-status?lat=46.8123&lon=-71.2145')

        assert response.status_code == 200
        assert response.json['has_operation'] is True
        assert len(response.json['streets_affected']) == 2
        assert 'Rue Saint-Jean' in response.json['streets_affected']

    @patch('app.routes.check_snow_removal')
    @patch('app.routes.reverse_geocode')
    def test_snow_status_includes_coordinates(self, mock_reverse, mock_check, client):
        """Verify response includes the coordinates."""
        mock_check.return_value = {'has_operation': False, 'streets': [], 'search_radius': 200}
        mock_reverse.return_value = 'Unknown'

        response = client.get('/snow-status?lat=46.8123&lon=-71.2145')

        assert response.status_code == 200
        assert 'coordinates' in response.json
        assert response.json['coordinates']['lat'] == 46.8123
        assert response.json['coordinates']['lon'] == -71.2145

    @patch('app.routes.check_snow_removal')
    @patch('app.routes.reverse_geocode')
    def test_snow_status_includes_search_radius(self, mock_reverse, mock_check, client):
        """Verify response includes search_radius_meters."""
        mock_check.return_value = {'has_operation': False, 'streets': [], 'search_radius': 200}
        mock_reverse.return_value = 'Unknown'

        response = client.get('/snow-status?lat=46.8123&lon=-71.2145')

        assert response.status_code == 200
        assert 'search_radius_meters' in response.json
        assert response.json['search_radius_meters'] == 200


class TestSnowStatusValidation:
    """Tests for /snow-status input validation (Task 10.2)."""

    def test_snow_status_missing_lat(self, client):
        """Verify 400 error when lat is missing."""
        response = client.get('/snow-status?lon=-71.2')

        assert response.status_code == 400
        assert 'Missing required parameters' in response.json['error']

    def test_snow_status_missing_lon(self, client):
        """Verify 400 error when lon is missing."""
        response = client.get('/snow-status?lat=46.8')

        assert response.status_code == 400
        assert 'Missing required parameters' in response.json['error']

    def test_snow_status_missing_both(self, client):
        """Verify 400 error when both params are missing."""
        response = client.get('/snow-status')

        assert response.status_code == 400
        assert 'Missing required parameters' in response.json['error']

    def test_snow_status_non_numeric_lat(self, client):
        """Verify 400 error for non-numeric lat."""
        response = client.get('/snow-status?lat=abc&lon=-71.2')

        assert response.status_code == 400
        assert 'Invalid coordinates' in response.json['error']

    def test_snow_status_non_numeric_lon(self, client):
        """Verify 400 error for non-numeric lon."""
        response = client.get('/snow-status?lat=46.8&lon=xyz')

        assert response.status_code == 400
        assert 'Invalid coordinates' in response.json['error']

    def test_snow_status_lat_too_high(self, client):
        """Verify 400 error when lat > 90."""
        response = client.get('/snow-status?lat=91&lon=-71.2')

        assert response.status_code == 400
        assert 'Invalid latitude' in response.json['error']

    def test_snow_status_lat_too_low(self, client):
        """Verify 400 error when lat < -90."""
        response = client.get('/snow-status?lat=-91&lon=-71.2')

        assert response.status_code == 400
        assert 'Invalid latitude' in response.json['error']

    def test_snow_status_lon_too_high(self, client):
        """Verify 400 error when lon > 180."""
        response = client.get('/snow-status?lat=46.8&lon=181')

        assert response.status_code == 400
        assert 'Invalid longitude' in response.json['error']

    def test_snow_status_lon_too_low(self, client):
        """Verify 400 error when lon < -180."""
        response = client.get('/snow-status?lat=46.8&lon=-181')

        assert response.status_code == 400
        assert 'Invalid longitude' in response.json['error']

    @patch('app.routes.check_snow_removal')
    @patch('app.routes.reverse_geocode')
    def test_snow_status_boundary_coords_valid(self, mock_reverse, mock_check, client):
        """Verify boundary coordinates are accepted."""
        mock_check.return_value = {'has_operation': False, 'streets': [], 'search_radius': 200}
        mock_reverse.return_value = 'Unknown'

        # Test boundary values
        response = client.get('/snow-status?lat=90&lon=180')
        assert response.status_code == 200

        response = client.get('/snow-status?lat=-90&lon=-180')
        assert response.status_code == 200


class TestSnowStatusLocationName:
    """Tests for /snow-status location_name field (Task 10.3)."""

    @patch('app.routes.check_snow_removal')
    @patch('app.routes.reverse_geocode')
    def test_snow_status_includes_location_name(self, mock_reverse, mock_check, client):
        """Verify response includes location_name."""
        mock_check.return_value = {'has_operation': False, 'streets': [], 'search_radius': 200}
        mock_reverse.return_value = 'Boulevard Laurier'

        response = client.get('/snow-status?lat=46.8&lon=-71.2')

        assert response.status_code == 200
        assert 'location_name' in response.json
        assert response.json['location_name'] == 'Boulevard Laurier'

    @patch('app.routes.check_snow_removal')
    @patch('app.routes.reverse_geocode')
    def test_snow_status_location_name_unknown_fallback(self, mock_reverse, mock_check, client):
        """Verify location_name falls back to 'Unknown'."""
        mock_check.return_value = {'has_operation': False, 'streets': [], 'search_radius': 200}
        mock_reverse.return_value = 'Unknown'

        response = client.get('/snow-status?lat=46.8&lon=-71.2')

        assert response.status_code == 200
        assert response.json['location_name'] == 'Unknown'


class TestSnowStatusErrorHandling:
    """Tests for /snow-status error handling (Task 10.4)."""

    @patch('app.routes.check_snow_removal')
    def test_snow_status_api_failure(self, mock_check, client):
        """Verify 500 error when snow API fails."""
        mock_check.side_effect = Exception("API connection failed")

        response = client.get('/snow-status?lat=46.8&lon=-71.2')

        assert response.status_code == 500
        assert 'Failed to check snow removal status' in response.json['error']

    @patch('app.routes.check_snow_removal')
    @patch('app.routes.reverse_geocode')
    def test_snow_status_includes_message(self, mock_reverse, mock_check, client):
        """Verify response includes message field."""
        mock_check.return_value = {'has_operation': True, 'streets': ['Rue Test'], 'search_radius': 200}
        mock_reverse.return_value = 'Rue Test'

        response = client.get('/snow-status?lat=46.8&lon=-71.2')

        assert response.status_code == 200
        assert 'message' in response.json
        assert 'Snow removal in progress' in response.json['message']


class TestErrorHandlers:
    def test_404_error(self, client):
        response = client.get('/nonexistent-page')
        assert response.status_code == 404
