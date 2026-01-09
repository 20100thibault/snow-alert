import os
import pytest

# Use test database
os.environ['DATABASE_PATH'] = 'test_snow_alert.db'

from app.database import init_db, add_user, get_user_by_email, remove_user, get_all_active_users
from app.models import Base
from app.database import engine


@pytest.fixture(autouse=True)
def setup_teardown():
    """Create fresh database for each test."""
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


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


class TestRemoveUser:
    def test_remove_existing_user(self):
        add_user('remove@example.com', 'G1R2K8', 46.0, -71.0)
        result = remove_user('remove@example.com')
        assert result is True
        assert get_user_by_email('remove@example.com') is None

    def test_remove_nonexistent_user(self):
        result = remove_user('nobody@example.com')
        assert result is False


class TestGetAllActiveUsers:
    def test_get_active_users(self):
        add_user('active1@example.com', 'G1R2K8', 46.0, -71.0)
        add_user('active2@example.com', 'G1V1J8', 46.0, -71.0)
        users = get_all_active_users()
        assert len(users) == 2

    def test_empty_when_no_users(self):
        users = get_all_active_users()
        assert len(users) == 0
