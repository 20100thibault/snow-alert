import pytest
import os
import sys
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.email_service import send_alert_email, send_welcome_email


class TestSendAlertEmail:
    @patch('app.email_service.Config')
    def test_returns_true_when_disabled(self, mock_config):
        mock_config.EMAIL_ENABLED = False

        result = send_alert_email(
            to_email='test@example.com',
            postal_code='G1R2K8',
            streets=['Rue Test', 'Avenue Example']
        )
        assert result is True

    @patch('app.email_service.Config')
    def test_accepts_empty_streets_list(self, mock_config):
        mock_config.EMAIL_ENABLED = False

        result = send_alert_email(
            to_email='test@example.com',
            postal_code='G1R2K8',
            streets=[]
        )
        assert result is True

    @patch('app.email_service.resend.Emails.send')
    @patch('app.email_service.Config')
    def test_sends_email_when_enabled(self, mock_config, mock_send):
        mock_config.EMAIL_ENABLED = True
        mock_config.EMAIL_FROM = 'test@resend.dev'
        mock_send.return_value = {'id': 'test-id-123'}

        result = send_alert_email(
            to_email='test@example.com',
            postal_code='G1R2K8',
            streets=['Rue Test']
        )

        assert result is True
        mock_send.assert_called_once()
        call_args = mock_send.call_args[0][0]
        assert call_args['to'] == ['test@example.com']
        assert 'G1R2K8' in call_args['subject']

    @patch('app.email_service.resend.Emails.send')
    @patch('app.email_service.Config')
    def test_returns_false_on_error(self, mock_config, mock_send):
        mock_config.EMAIL_ENABLED = True
        mock_config.EMAIL_FROM = 'test@resend.dev'
        mock_send.side_effect = Exception('API Error')

        result = send_alert_email(
            to_email='test@example.com',
            postal_code='G1R2K8',
            streets=['Rue Test']
        )

        assert result is False


class TestSendWelcomeEmail:
    @patch('app.email_service.Config')
    def test_returns_true_when_disabled(self, mock_config):
        mock_config.EMAIL_ENABLED = False

        result = send_welcome_email(
            to_email='test@example.com',
            postal_code='G1R2K8'
        )
        assert result is True

    @patch('app.email_service.resend.Emails.send')
    @patch('app.email_service.Config')
    def test_sends_email_when_enabled(self, mock_config, mock_send):
        mock_config.EMAIL_ENABLED = True
        mock_config.EMAIL_FROM = 'test@resend.dev'
        mock_send.return_value = {'id': 'test-id-456'}

        result = send_welcome_email(
            to_email='newuser@example.com',
            postal_code='G1V1J8'
        )

        assert result is True
        mock_send.assert_called_once()
        call_args = mock_send.call_args[0][0]
        assert call_args['to'] == ['newuser@example.com']
        assert 'Confirmed' in call_args['subject']

    @patch('app.email_service.resend.Emails.send')
    @patch('app.email_service.Config')
    def test_returns_false_on_error(self, mock_config, mock_send):
        mock_config.EMAIL_ENABLED = True
        mock_config.EMAIL_FROM = 'test@resend.dev'
        mock_send.side_effect = Exception('API Error')

        result = send_welcome_email(
            to_email='test@example.com',
            postal_code='G1R2K8'
        )

        assert result is False
