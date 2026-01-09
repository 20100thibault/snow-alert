import pytest
import os
import sys
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Use test database and disable emails
os.environ['DATABASE_PATH'] = 'test_scheduler.db'
os.environ['EMAIL_ENABLED'] = 'false'

from app.scheduler import check_all_users, get_scheduled_jobs
from app.database import init_db, add_user, remove_user
from app.models import Base
from app.database import engine


@pytest.fixture(autouse=True)
def setup_teardown():
    """Create fresh database for each test."""
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


class TestCheckAllUsers:
    def test_returns_dict(self):
        result = check_all_users()
        assert isinstance(result, dict)
        assert 'users_checked' in result
        assert 'alerts_sent' in result
        assert 'errors' in result

    def test_no_users_returns_zero(self):
        result = check_all_users()
        assert result['users_checked'] == 0
        assert result['alerts_sent'] == 0

    @patch('app.snow_checker.check_postal_code')
    @patch('app.email_service.send_alert_email')
    def test_checks_all_active_users(self, mock_email, mock_check):
        mock_check.return_value = (False, [])
        mock_email.return_value = True

        # Add test users
        add_user('user1@test.com', 'G1R2K8', 46.8, -71.2)
        add_user('user2@test.com', 'G1V1J8', 46.8, -71.3)

        result = check_all_users()

        assert result['users_checked'] == 2
        assert mock_check.call_count == 2

    @patch('app.snow_checker.check_postal_code')
    @patch('app.email_service.send_alert_email')
    def test_sends_alert_when_operation_active(self, mock_email, mock_check):
        mock_check.return_value = (True, ['Rue Test'])
        mock_email.return_value = True

        add_user('alert@test.com', 'G1R2K8', 46.8, -71.2)

        result = check_all_users()

        assert result['alerts_sent'] == 1
        mock_email.assert_called_once()

    @patch('app.snow_checker.check_postal_code')
    @patch('app.email_service.send_alert_email')
    def test_no_alert_when_no_operation(self, mock_email, mock_check):
        mock_check.return_value = (False, [])
        mock_email.return_value = True

        add_user('noalert@test.com', 'G1R2K8', 46.8, -71.2)

        result = check_all_users()

        assert result['alerts_sent'] == 0
        mock_email.assert_not_called()

    @patch('app.snow_checker.check_postal_code')
    @patch('app.email_service.send_alert_email')
    def test_counts_email_errors(self, mock_email, mock_check):
        mock_check.return_value = (True, ['Rue Test'])
        mock_email.return_value = False  # Email fails

        add_user('fail@test.com', 'G1R2K8', 46.8, -71.2)

        result = check_all_users()

        assert result['errors'] == 1
        assert result['alerts_sent'] == 0


class TestGetScheduledJobs:
    def test_returns_list(self):
        jobs = get_scheduled_jobs()
        assert isinstance(jobs, list)


class TestAdminEndpoints:
    @pytest.fixture
    def client(self):
        from app import create_app
        app = create_app(start_scheduler=False)
        app.config['TESTING'] = True
        return app.test_client()

    def test_trigger_check_endpoint(self, client):
        response = client.get('/admin/trigger-check')
        assert response.status_code == 200
        assert response.json['success'] is True
        assert 'result' in response.json

    def test_jobs_endpoint(self, client):
        response = client.get('/admin/jobs')
        assert response.status_code == 200
        assert 'jobs' in response.json
