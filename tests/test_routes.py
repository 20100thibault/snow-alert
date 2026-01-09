import pytest
import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Use test database
os.environ['DATABASE_PATH'] = 'test_routes.db'
os.environ['EMAIL_ENABLED'] = 'false'

from app import create_app
from app.database import init_db, remove_user
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
    def test_subscribe_duplicate_email(self, mock_email, mock_geocode, client):
        mock_geocode.return_value = {'lat': 46.8, 'lon': -71.2}
        mock_email.return_value = True

        # First subscription
        client.post('/subscribe', json={
            'email': 'duplicate@example.com',
            'postal_code': 'G1R2K8'
        })

        # Duplicate attempt
        response = client.post('/subscribe', json={
            'email': 'duplicate@example.com',
            'postal_code': 'G1V1J8'
        })

        assert response.status_code == 409
        assert 'already subscribed' in response.json['error']


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


class TestErrorHandlers:
    def test_404_error(self, client):
        response = client.get('/nonexistent-page')
        assert response.status_code == 404
