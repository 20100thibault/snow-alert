"""
Tests for the UI templates (Phase 5).
"""

import pytest
from bs4 import BeautifulSoup


@pytest.fixture
def template_html():
    """Load the index.html template."""
    with open('templates/index.html', 'r') as f:
        return f.read()


@pytest.fixture
def soup(template_html):
    """Parse the template HTML with BeautifulSoup."""
    return BeautifulSoup(template_html, 'html.parser')


class TestUpdatedBranding:
    """Tests for Task 5.1: Updated page title and hero section."""

    def test_page_title_is_quebec_city_alerts(self, soup):
        """Verify page title is 'Quebec City Alerts'."""
        title = soup.find('title')
        assert title is not None
        assert 'Quebec City Alerts' in title.text

    def test_hero_heading_is_quebec_city_alerts(self, soup):
        """Verify hero heading is 'Quebec City Alerts'."""
        hero_h1 = soup.select_one('.hero h1')
        assert hero_h1 is not None
        assert 'Quebec City Alerts' in hero_h1.text

    def test_hero_subtitle_mentions_snow_and_waste(self, soup):
        """Verify hero subtitle mentions snow and waste collection."""
        hero_p = soup.select_one('.hero p')
        assert hero_p is not None
        text = hero_p.text.lower()
        assert 'snow' in text
        assert 'waste' in text or 'collection' in text

    def test_hero_icon_exists(self, soup):
        """Verify hero has an icon."""
        hero_icon = soup.select_one('.hero-icon')
        assert hero_icon is not None


class TestUnifiedFormStructure:
    """Tests for Task 5.2: Unified subscription form structure."""

    def test_form_has_postal_code_input(self, soup):
        """Verify form has postal_code input."""
        postal_input = soup.find('input', {'id': 'postal_code'})
        assert postal_input is not None

    def test_form_has_email_input(self, soup):
        """Verify form has email input."""
        email_input = soup.find('input', {'id': 'email'})
        assert email_input is not None

    def test_form_has_snow_alerts_checkbox(self, soup):
        """Verify form has snow_alerts checkbox."""
        checkbox = soup.find('input', {'id': 'snow_alerts', 'type': 'checkbox'})
        assert checkbox is not None

    def test_form_has_garbage_alerts_checkbox(self, soup):
        """Verify form has garbage_alerts checkbox."""
        checkbox = soup.find('input', {'id': 'garbage_alerts', 'type': 'checkbox'})
        assert checkbox is not None

    def test_form_has_recycling_alerts_checkbox(self, soup):
        """Verify form has recycling_alerts checkbox."""
        checkbox = soup.find('input', {'id': 'recycling_alerts', 'type': 'checkbox'})
        assert checkbox is not None

    def test_submit_button_exists(self, soup):
        """Verify submit button exists."""
        submit_btn = soup.find('button', {'type': 'submit', 'id': 'subscribeBtn'})
        assert submit_btn is not None


class TestAlertCardsStyling:
    """Tests for Task 5.3: Alert type selection cards."""

    def test_snow_alert_card_has_snowflake_icon(self, soup):
        """Verify snow alert card has snowflake icon."""
        snow_card = soup.select_one('.alert-card.snow')
        assert snow_card is not None
        icon = snow_card.select_one('.alert-card-icon')
        assert icon is not None
        # Check for snowflake emoji or icon

    def test_garbage_alert_card_has_trash_icon(self, soup):
        """Verify garbage alert card has trash icon."""
        garbage_card = soup.select_one('.alert-card.garbage')
        assert garbage_card is not None
        icon = garbage_card.select_one('.alert-card-icon')
        assert icon is not None

    def test_recycling_alert_card_has_recycling_icon(self, soup):
        """Verify recycling alert card has recycling icon."""
        recycling_card = soup.select_one('.alert-card.recycling')
        assert recycling_card is not None
        icon = recycling_card.select_one('.alert-card-icon')
        assert icon is not None

    def test_cards_have_consistent_styling(self, soup):
        """Verify all cards have consistent styling."""
        cards = soup.select('.alert-card')
        assert len(cards) == 3
        for card in cards:
            assert card.select_one('.alert-card-icon') is not None
            assert card.select_one('.alert-card-content') is not None
            assert card.select_one('.alert-card-toggle') is not None

    def test_checkboxes_are_styled_as_toggles(self, template_html):
        """Verify checkboxes are styled as toggles."""
        assert '.alert-card-toggle' in template_html
        assert 'border-radius: 15px' in template_html or 'border-radius:15px' in template_html


class TestAlertCardDescriptions:
    """Tests for Task 5.4: Descriptive text on alert cards."""

    def test_snow_card_mentions_street_snow_removal(self, soup):
        """Verify snow card mentions street snow removal."""
        snow_card = soup.select_one('.alert-card.snow')
        assert snow_card is not None
        desc = snow_card.select_one('.alert-card-desc')
        assert desc is not None
        text = desc.text.lower()
        assert 'snow' in text

    def test_garbage_card_mentions_6_pm(self, soup):
        """Verify garbage card mentions 6 PM reminder."""
        garbage_card = soup.select_one('.alert-card.garbage')
        assert garbage_card is not None
        desc = garbage_card.select_one('.alert-card-desc')
        assert desc is not None
        text = desc.text.lower()
        assert '6 pm' in text or '6pm' in text

    def test_recycling_card_mentions_6_pm(self, soup):
        """Verify recycling card mentions 6 PM reminder."""
        recycling_card = soup.select_one('.alert-card.recycling')
        assert recycling_card is not None
        desc = recycling_card.select_one('.alert-card-desc')
        assert desc is not None
        text = desc.text.lower()
        assert '6 pm' in text or '6pm' in text


class TestFormSubmissionJS:
    """Tests for Task 5.5: JavaScript form submission."""

    def test_form_submission_collects_postal_code(self, template_html):
        """Verify JS collects postal_code."""
        assert "postal_code" in template_html
        assert "document.getElementById('postal_code')" in template_html

    def test_form_submission_collects_email(self, template_html):
        """Verify JS collects email."""
        assert "document.getElementById('email')" in template_html

    def test_form_submission_collects_checkboxes(self, template_html):
        """Verify JS collects all checkbox values."""
        assert "snow_alerts" in template_html
        assert "garbage_alerts" in template_html
        assert "recycling_alerts" in template_html

    def test_form_sends_post_to_subscribe(self, template_html):
        """Verify form sends POST to /subscribe."""
        assert "fetch('/subscribe'" in template_html
        assert "method: 'POST'" in template_html

    def test_shows_loading_state(self, template_html):
        """Verify loading state during submission."""
        assert "btn-loading" in template_html
        assert "btn.disabled = true" in template_html

    def test_displays_success_message(self, template_html):
        """Verify success message display."""
        assert "message success" in template_html


class TestCheckboxValidationJS:
    """Tests for Task 5.6: Checkbox validation."""

    def test_validates_at_least_one_checkbox(self, template_html):
        """Verify validation for at least one checkbox."""
        assert "validateCheckboxes" in template_html
        assert "Please select at least one alert type" in template_html


class TestScheduleDisplay:
    """Tests for Task 5.7: Schedule display after subscription."""

    def test_schedule_section_exists(self, soup):
        """Verify schedule section exists."""
        schedule_section = soup.find('div', {'id': 'scheduleSection'})
        assert schedule_section is not None

    def test_schedule_section_hidden_initially(self, template_html):
        """Verify schedule section is hidden initially."""
        assert "schedule-section" in template_html
        assert "display: none" in template_html

    def test_show_schedule_function_exists(self, template_html):
        """Verify showSchedule function exists."""
        assert "function showSchedule" in template_html

    def test_schedule_displays_garbage_date(self, template_html):
        """Verify schedule displays garbage date."""
        assert "Next Garbage Pickup" in template_html

    def test_schedule_displays_recycling_date(self, template_html):
        """Verify schedule displays recycling date."""
        assert "Next Recycling Pickup" in template_html


class TestUnsubscribeSection:
    """Tests for Task 5.8: Unsubscribe section."""

    def test_unsubscribe_form_has_email_input(self, soup):
        """Verify unsubscribe form has email input."""
        unsub_email = soup.find('input', {'id': 'unsub_email'})
        assert unsub_email is not None

    def test_submit_calls_unsubscribe_endpoint(self, template_html):
        """Verify unsubscribe calls /unsubscribe endpoint."""
        assert "fetch('/unsubscribe'" in template_html


class TestManagePreferencesLink:
    """Tests for Task 5.9: Manage preferences functionality."""

    def test_manage_preferences_button_exists(self, soup):
        """Verify manage preferences button exists."""
        manage_btn = soup.find('button', {'id': 'manageBtn'})
        assert manage_btn is not None

    def test_manage_section_exists(self, soup):
        """Verify manage section exists."""
        manage_section = soup.find('div', {'id': 'manageSection'})
        assert manage_section is not None

    def test_calls_status_endpoint(self, template_html):
        """Verify calls /subscriber endpoint to get preferences."""
        assert "/subscriber/" in template_html


class TestResponsiveLayout:
    """Tests for Task 5.10: Responsive design."""

    def test_has_media_query_for_mobile(self, template_html):
        """Verify media query for mobile exists."""
        assert "@media" in template_html
        assert "max-width" in template_html

    def test_alert_cards_stack_vertically(self, template_html):
        """Verify alert cards are flex column (stack vertically)."""
        assert "flex-direction: column" in template_html

    def test_form_inputs_full_width(self, template_html):
        """Verify form inputs are full width."""
        assert "width: 100%" in template_html

    def test_viewport_meta_tag_exists(self, soup):
        """Verify viewport meta tag exists."""
        viewport = soup.find('meta', {'name': 'viewport'})
        assert viewport is not None
        assert 'width=device-width' in viewport.get('content', '')
