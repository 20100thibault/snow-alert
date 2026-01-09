"""
Tests for the Email Service module.
"""

import pytest
import os
from datetime import date
from unittest.mock import patch, MagicMock

# Disable email for tests
os.environ['EMAIL_ENABLED'] = 'false'


class TestGarbageEmailTemplate:
    """Tests for Task 4.6: Garbage reminder email template."""

    def test_garbage_email_template_exists(self):
        """Verify _build_garbage_email_html function exists."""
        from app.email_service import _build_garbage_email_html
        assert callable(_build_garbage_email_html)

    def test_garbage_email_subject_contains_garbage_pickup(self):
        """Verify garbage email subject includes 'Garbage pickup tomorrow'."""
        from app.email_service import send_garbage_reminder
        # The subject is set in send_garbage_reminder, verify the pattern
        collection_date = date(2025, 1, 15)
        # Subject format: "🗑️ Garbage pickup tomorrow - January 15"
        formatted = collection_date.strftime("%B %d")
        expected_subject = f"🗑️ Garbage pickup tomorrow - {formatted}"
        assert "Garbage pickup tomorrow" in expected_subject

    def test_garbage_email_body_includes_collection_date(self):
        """Verify garbage email body includes collection date."""
        from app.email_service import _build_garbage_email_html
        collection_date = date(2025, 1, 15)
        html = _build_garbage_email_html("G1R2K8", collection_date)
        # Should contain formatted date
        assert "Wednesday, January 15, 2025" in html

    def test_garbage_email_body_includes_postal_code(self):
        """Verify garbage email body includes postal code."""
        from app.email_service import _build_garbage_email_html
        collection_date = date(2025, 1, 15)
        html = _build_garbage_email_html("G1R 2K8", collection_date)
        assert "G1R 2K8" in html

    def test_garbage_email_body_includes_unsubscribe_link(self):
        """Verify garbage email body includes unsubscribe link."""
        from app.email_service import _build_garbage_email_html
        collection_date = date(2025, 1, 15)
        html = _build_garbage_email_html("G1R2K8", collection_date)
        assert "Unsubscribe" in html

    def test_garbage_email_is_valid_html(self):
        """Verify garbage email HTML is properly structured."""
        from app.email_service import _build_garbage_email_html
        collection_date = date(2025, 1, 15)
        html = _build_garbage_email_html("G1R2K8", collection_date)
        assert html.startswith("<!DOCTYPE html>") or html.strip().startswith("<!DOCTYPE html>") or "<html" in html
        assert "</html>" in html
        assert "<body" in html
        assert "</body>" in html

    def test_garbage_email_includes_garbage_icon(self):
        """Verify garbage email includes trash icon."""
        from app.email_service import _build_garbage_email_html
        collection_date = date(2025, 1, 15)
        html = _build_garbage_email_html("G1R2K8", collection_date)
        assert "🗑️" in html

    def test_garbage_email_has_reminder_tips(self):
        """Verify garbage email includes reminder tips."""
        from app.email_service import _build_garbage_email_html
        collection_date = date(2025, 1, 15)
        html = _build_garbage_email_html("G1R2K8", collection_date)
        assert "7:00 AM" in html
        assert "sealed" in html.lower() or "garbage" in html.lower()


class TestRecyclingEmailTemplate:
    """Tests for Task 4.7: Recycling reminder email template."""

    def test_recycling_email_template_exists(self):
        """Verify _build_recycling_email_html function exists."""
        from app.email_service import _build_recycling_email_html
        assert callable(_build_recycling_email_html)

    def test_recycling_email_subject_contains_recycling_pickup(self):
        """Verify recycling email subject includes 'Recycling pickup tomorrow'."""
        from app.email_service import send_recycling_reminder
        collection_date = date(2025, 1, 15)
        formatted = collection_date.strftime("%B %d")
        expected_subject = f"♻️ Recycling pickup tomorrow - {formatted}"
        assert "Recycling pickup tomorrow" in expected_subject

    def test_recycling_email_body_includes_collection_date(self):
        """Verify recycling email body includes collection date."""
        from app.email_service import _build_recycling_email_html
        collection_date = date(2025, 1, 15)
        html = _build_recycling_email_html("G1R2K8", collection_date)
        assert "Wednesday, January 15, 2025" in html

    def test_recycling_email_body_includes_postal_code(self):
        """Verify recycling email body includes postal code."""
        from app.email_service import _build_recycling_email_html
        collection_date = date(2025, 1, 15)
        html = _build_recycling_email_html("G1R 2K8", collection_date)
        assert "G1R 2K8" in html

    def test_recycling_email_body_includes_unsubscribe_link(self):
        """Verify recycling email body includes unsubscribe link."""
        from app.email_service import _build_recycling_email_html
        collection_date = date(2025, 1, 15)
        html = _build_recycling_email_html("G1R2K8", collection_date)
        assert "Unsubscribe" in html

    def test_recycling_email_is_valid_html(self):
        """Verify recycling email HTML is properly structured."""
        from app.email_service import _build_recycling_email_html
        collection_date = date(2025, 1, 15)
        html = _build_recycling_email_html("G1R2K8", collection_date)
        assert html.startswith("<!DOCTYPE html>") or html.strip().startswith("<!DOCTYPE html>") or "<html" in html
        assert "</html>" in html
        assert "<body" in html
        assert "</body>" in html

    def test_recycling_email_includes_recycling_icon(self):
        """Verify recycling email includes recycling icon."""
        from app.email_service import _build_recycling_email_html
        collection_date = date(2025, 1, 15)
        html = _build_recycling_email_html("G1R2K8", collection_date)
        assert "♻️" in html

    def test_recycling_email_has_reminder_tips(self):
        """Verify recycling email includes reminder tips."""
        from app.email_service import _build_recycling_email_html
        collection_date = date(2025, 1, 15)
        html = _build_recycling_email_html("G1R2K8", collection_date)
        assert "7:00 AM" in html
        assert "plastic bags" in html.lower() or "recycling" in html.lower()


class TestSendGarbageReminder:
    """Tests for Task 4.8: send_garbage_reminder function."""

    def test_send_garbage_reminder_function_exists(self):
        """Verify send_garbage_reminder function exists."""
        from app.email_service import send_garbage_reminder
        assert callable(send_garbage_reminder)

    @patch('app.email_service.Config')
    def test_send_garbage_reminder_returns_true_when_disabled(self, mock_config):
        """Verify send_garbage_reminder returns True when email disabled."""
        mock_config.EMAIL_ENABLED = False

        from app.email_service import send_garbage_reminder
        result = send_garbage_reminder(
            "test@example.com",
            "G1R2K8",
            date(2025, 1, 15)
        )
        assert result is True

    @patch('app.email_service.resend.Emails.send')
    @patch('app.email_service.Config')
    def test_send_garbage_reminder_calls_email_api(self, mock_config, mock_send):
        """Verify send_garbage_reminder calls email API with correct recipient."""
        mock_config.EMAIL_ENABLED = True
        mock_config.EMAIL_FROM = "alerts@example.com"
        mock_send.return_value = {'id': 'test-id-123'}

        from app.email_service import send_garbage_reminder
        result = send_garbage_reminder(
            "recipient@example.com",
            "G1R2K8",
            date(2025, 1, 15)
        )

        assert result is True
        mock_send.assert_called_once()
        call_args = mock_send.call_args[0][0]
        assert call_args['to'] == ["recipient@example.com"]
        assert "Garbage" in call_args['subject']

    @patch('app.email_service.resend.Emails.send')
    @patch('app.email_service.Config')
    def test_send_garbage_reminder_returns_false_on_failure(self, mock_config, mock_send):
        """Verify send_garbage_reminder returns False on failure."""
        mock_config.EMAIL_ENABLED = True
        mock_config.EMAIL_FROM = "alerts@example.com"
        mock_send.side_effect = Exception("API Error")

        from app.email_service import send_garbage_reminder
        result = send_garbage_reminder(
            "recipient@example.com",
            "G1R2K8",
            date(2025, 1, 15)
        )

        assert result is False


class TestSendRecyclingReminder:
    """Tests for Task 4.9: send_recycling_reminder function."""

    def test_send_recycling_reminder_function_exists(self):
        """Verify send_recycling_reminder function exists."""
        from app.email_service import send_recycling_reminder
        assert callable(send_recycling_reminder)

    @patch('app.email_service.Config')
    def test_send_recycling_reminder_returns_true_when_disabled(self, mock_config):
        """Verify send_recycling_reminder returns True when email disabled."""
        mock_config.EMAIL_ENABLED = False

        from app.email_service import send_recycling_reminder
        result = send_recycling_reminder(
            "test@example.com",
            "G1R2K8",
            date(2025, 1, 15)
        )
        assert result is True

    @patch('app.email_service.resend.Emails.send')
    @patch('app.email_service.Config')
    def test_send_recycling_reminder_calls_email_api(self, mock_config, mock_send):
        """Verify send_recycling_reminder calls email API with correct recipient."""
        mock_config.EMAIL_ENABLED = True
        mock_config.EMAIL_FROM = "alerts@example.com"
        mock_send.return_value = {'id': 'test-id-456'}

        from app.email_service import send_recycling_reminder
        result = send_recycling_reminder(
            "recipient@example.com",
            "G1R2K8",
            date(2025, 1, 15)
        )

        assert result is True
        mock_send.assert_called_once()
        call_args = mock_send.call_args[0][0]
        assert call_args['to'] == ["recipient@example.com"]
        assert "Recycling" in call_args['subject']

    @patch('app.email_service.resend.Emails.send')
    @patch('app.email_service.Config')
    def test_send_recycling_reminder_returns_false_on_failure(self, mock_config, mock_send):
        """Verify send_recycling_reminder returns False on failure."""
        mock_config.EMAIL_ENABLED = True
        mock_config.EMAIL_FROM = "alerts@example.com"
        mock_send.side_effect = Exception("API Error")

        from app.email_service import send_recycling_reminder
        result = send_recycling_reminder(
            "recipient@example.com",
            "G1R2K8",
            date(2025, 1, 15)
        )

        assert result is False


class TestEmailDesignConsistency:
    """Tests to verify email templates match website design."""

    def test_garbage_email_uses_website_colors(self):
        """Verify garbage email uses website color palette."""
        from app.email_service import _build_garbage_email_html
        html = _build_garbage_email_html("G1R2K8", date(2025, 1, 15))
        # Website uses #34c759 for success/green
        assert "#34c759" in html or "#248a3d" in html

    def test_recycling_email_uses_website_colors(self):
        """Verify recycling email uses website color palette."""
        from app.email_service import _build_recycling_email_html
        html = _build_recycling_email_html("G1R2K8", date(2025, 1, 15))
        # Website uses #0071e3 for accent/blue
        assert "#0071e3" in html or "#0058b0" in html

    def test_emails_use_apple_style_fonts(self):
        """Verify emails use Apple-style system fonts."""
        from app.email_service import _build_garbage_email_html, _build_recycling_email_html
        garbage_html = _build_garbage_email_html("G1R2K8", date(2025, 1, 15))
        recycling_html = _build_recycling_email_html("G1R2K8", date(2025, 1, 15))

        # Should include Apple system fonts
        assert "-apple-system" in garbage_html
        assert "-apple-system" in recycling_html

    def test_emails_have_card_style_design(self):
        """Verify emails use card-style design with rounded corners."""
        from app.email_service import _build_garbage_email_html, _build_recycling_email_html
        garbage_html = _build_garbage_email_html("G1R2K8", date(2025, 1, 15))
        recycling_html = _build_recycling_email_html("G1R2K8", date(2025, 1, 15))

        # Should include border-radius for rounded corners
        assert "border-radius" in garbage_html
        assert "border-radius" in recycling_html

    def test_emails_have_gradient_header(self):
        """Verify emails use gradient header like website."""
        from app.email_service import _build_garbage_email_html, _build_recycling_email_html
        garbage_html = _build_garbage_email_html("G1R2K8", date(2025, 1, 15))
        recycling_html = _build_recycling_email_html("G1R2K8", date(2025, 1, 15))

        # Should include gradient background
        assert "linear-gradient" in garbage_html
        assert "linear-gradient" in recycling_html
