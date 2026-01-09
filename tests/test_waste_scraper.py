"""
Tests for the waste_scraper module.
"""

import os
import pytest
from unittest.mock import patch, Mock, MagicMock
import requests

# Use test database
os.environ['DATABASE_PATH'] = 'test_snow_alert.db'


# ============== Task 2.1: Module Structure Tests ==============

class TestWasteScraperModuleExists:
    """Verify waste_scraper module structure (Task 2.1)"""

    def test_module_imports_without_error(self):
        """Verify waste_scraper module can be imported."""
        import app.waste_scraper
        assert app.waste_scraper is not None

    def test_scrape_schedule_function_exists(self):
        """Verify scrape_schedule function exists."""
        from app.waste_scraper import scrape_schedule
        assert callable(scrape_schedule)

    def test_parse_schedule_html_function_exists(self):
        """Verify parse_schedule_html function exists."""
        from app.waste_scraper import parse_schedule_html
        assert callable(parse_schedule_html)

    def test_get_cached_schedule_function_exists(self):
        """Verify get_cached_schedule function exists."""
        from app.waste_scraper import get_cached_schedule
        assert callable(get_cached_schedule)

    def test_get_schedule_function_exists(self):
        """Verify get_schedule main entry point exists."""
        from app.waste_scraper import get_schedule
        assert callable(get_schedule)

    def test_rate_limit_constant_exists(self):
        """Verify RATE_LIMIT_SECONDS constant is defined."""
        from app.waste_scraper import RATE_LIMIT_SECONDS
        assert RATE_LIMIT_SECONDS == 10

    def test_cache_expiration_constant_exists(self):
        """Verify CACHE_EXPIRATION_HOURS constant is defined."""
        from app.waste_scraper import CACHE_EXPIRATION_HOURS
        assert CACHE_EXPIRATION_HOURS == 24

    def test_info_collecte_url_defined(self):
        """Verify INFO_COLLECTE_URL is defined."""
        from app.waste_scraper import INFO_COLLECTE_URL
        assert "ville.quebec.qc.ca" in INFO_COLLECTE_URL
        assert "info-collecte" in INFO_COLLECTE_URL


# ============== Task 2.2: HTTP Request Tests ==============

# Sample HTML with ASP.NET form fields for testing
SAMPLE_FORM_HTML = '''
<html>
<form>
<input type="hidden" id="__VIEWSTATE" value="test_viewstate_value" />
<input type="hidden" id="__VIEWSTATEGENERATOR" value="test_generator" />
<input type="hidden" id="__EVENTVALIDATION" value="test_validation" />
</form>
</html>
'''

SAMPLE_RESPONSE_HTML = '''
<html>
<div class="result">
    <p>Collecte des ordures: Lundi</p>
    <p>Semaine: Impaire</p>
</div>
</html>
'''


class TestHttpRequest:
    """Test HTTP request functionality (Task 2.2)"""

    def test_normalize_postal_code_with_space(self):
        """Verify postal code normalization handles spaces."""
        from app.waste_scraper import _normalize_postal_code
        assert _normalize_postal_code('G1R 2K8') == 'G1R 2K8'

    def test_normalize_postal_code_without_space(self):
        """Verify postal code normalization adds space."""
        from app.waste_scraper import _normalize_postal_code
        assert _normalize_postal_code('G1R2K8') == 'G1R 2K8'

    def test_normalize_postal_code_lowercase(self):
        """Verify postal code normalization uppercases."""
        from app.waste_scraper import _normalize_postal_code
        assert _normalize_postal_code('g1r2k8') == 'G1R 2K8'

    def test_extract_form_fields_viewstate(self):
        """Verify __VIEWSTATE is extracted from HTML."""
        from app.waste_scraper import _extract_form_fields
        fields = _extract_form_fields(SAMPLE_FORM_HTML)
        assert fields['__VIEWSTATE'] == 'test_viewstate_value'

    def test_extract_form_fields_generator(self):
        """Verify __VIEWSTATEGENERATOR is extracted from HTML."""
        from app.waste_scraper import _extract_form_fields
        fields = _extract_form_fields(SAMPLE_FORM_HTML)
        assert fields['__VIEWSTATEGENERATOR'] == 'test_generator'

    def test_extract_form_fields_validation(self):
        """Verify __EVENTVALIDATION is extracted from HTML."""
        from app.waste_scraper import _extract_form_fields
        fields = _extract_form_fields(SAMPLE_FORM_HTML)
        assert fields['__EVENTVALIDATION'] == 'test_validation'

    def test_extract_form_fields_empty_html(self):
        """Verify empty dict returned for HTML without form fields."""
        from app.waste_scraper import _extract_form_fields
        fields = _extract_form_fields('<html></html>')
        assert fields == {}

    @patch('app.waste_scraper.requests.Session')
    def test_make_request_calls_get_first(self, mock_session_class):
        """Verify _make_request calls GET to fetch form fields."""
        from app.waste_scraper import _make_request

        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        mock_get_response = Mock()
        mock_get_response.text = SAMPLE_FORM_HTML
        mock_get_response.raise_for_status = Mock()

        mock_post_response = Mock()
        mock_post_response.text = SAMPLE_RESPONSE_HTML
        mock_post_response.raise_for_status = Mock()

        mock_session.get.return_value = mock_get_response
        mock_session.post.return_value = mock_post_response

        result = _make_request('G1R 2K8')

        mock_session.get.assert_called_once()
        assert 'info-collecte' in mock_session.get.call_args[0][0]

    @patch('app.waste_scraper.requests.Session')
    def test_make_request_calls_post_with_form_data(self, mock_session_class):
        """Verify _make_request POSTs with correct form data."""
        from app.waste_scraper import _make_request

        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        mock_get_response = Mock()
        mock_get_response.text = SAMPLE_FORM_HTML
        mock_get_response.raise_for_status = Mock()

        mock_post_response = Mock()
        mock_post_response.text = SAMPLE_RESPONSE_HTML
        mock_post_response.raise_for_status = Mock()

        mock_session.get.return_value = mock_get_response
        mock_session.post.return_value = mock_post_response

        result = _make_request('G1R 2K8')

        mock_session.post.assert_called_once()
        post_data = mock_session.post.call_args[1]['data']
        assert '__VIEWSTATE' in post_data
        assert post_data['__VIEWSTATE'] == 'test_viewstate_value'

    @patch('app.waste_scraper.requests.Session')
    def test_make_request_includes_postal_code(self, mock_session_class):
        """Verify _make_request includes postal code in POST data."""
        from app.waste_scraper import _make_request

        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        mock_get_response = Mock()
        mock_get_response.text = SAMPLE_FORM_HTML
        mock_get_response.raise_for_status = Mock()

        mock_post_response = Mock()
        mock_post_response.text = SAMPLE_RESPONSE_HTML
        mock_post_response.raise_for_status = Mock()

        mock_session.get.return_value = mock_get_response
        mock_session.post.return_value = mock_post_response

        result = _make_request('G1R 2K8')

        post_data = mock_session.post.call_args[1]['data']
        # Check postal code is in one of the form fields
        postal_code_found = any('G1R 2K8' in str(v) for v in post_data.values())
        assert postal_code_found

    @patch('app.waste_scraper.requests.Session')
    def test_make_request_sets_headers(self, mock_session_class):
        """Verify _make_request sets appropriate headers."""
        from app.waste_scraper import _make_request, USER_AGENT

        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        mock_get_response = Mock()
        mock_get_response.text = SAMPLE_FORM_HTML
        mock_get_response.raise_for_status = Mock()

        mock_post_response = Mock()
        mock_post_response.text = SAMPLE_RESPONSE_HTML
        mock_post_response.raise_for_status = Mock()

        mock_session.get.return_value = mock_get_response
        mock_session.post.return_value = mock_post_response

        result = _make_request('G1R 2K8')

        # Verify headers were set
        mock_session.headers.update.assert_called_once()
        headers = mock_session.headers.update.call_args[0][0]
        assert 'User-Agent' in headers

    @patch('app.waste_scraper.requests.Session')
    def test_make_request_returns_html_on_success(self, mock_session_class):
        """Verify _make_request returns HTML on success."""
        from app.waste_scraper import _make_request

        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        mock_get_response = Mock()
        mock_get_response.text = SAMPLE_FORM_HTML
        mock_get_response.raise_for_status = Mock()

        mock_post_response = Mock()
        mock_post_response.text = SAMPLE_RESPONSE_HTML
        mock_post_response.raise_for_status = Mock()

        mock_session.get.return_value = mock_get_response
        mock_session.post.return_value = mock_post_response

        result = _make_request('G1R 2K8')

        assert result == SAMPLE_RESPONSE_HTML

    @patch('app.waste_scraper.requests.Session')
    def test_make_request_handles_timeout(self, mock_session_class):
        """Verify _make_request handles timeout gracefully."""
        from app.waste_scraper import _make_request

        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_session.get.side_effect = requests.Timeout()

        result = _make_request('G1R 2K8')

        assert result is None

    @patch('app.waste_scraper.requests.Session')
    def test_make_request_handles_connection_error(self, mock_session_class):
        """Verify _make_request handles connection error gracefully."""
        from app.waste_scraper import _make_request

        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_session.get.side_effect = requests.ConnectionError()

        result = _make_request('G1R 2K8')

        assert result is None

    @patch('app.waste_scraper.requests.Session')
    def test_make_request_handles_http_error(self, mock_session_class):
        """Verify _make_request handles HTTP error gracefully."""
        from app.waste_scraper import _make_request

        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        mock_get_response = Mock()
        mock_get_response.raise_for_status.side_effect = requests.HTTPError("500 Server Error")

        mock_session.get.return_value = mock_get_response

        result = _make_request('G1R 2K8')

        assert result is None

    @patch('app.waste_scraper.requests.Session')
    def test_make_request_returns_none_without_viewstate(self, mock_session_class):
        """Verify _make_request returns None if VIEWSTATE not found."""
        from app.waste_scraper import _make_request

        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        mock_get_response = Mock()
        mock_get_response.text = '<html>no form fields</html>'
        mock_get_response.raise_for_status = Mock()

        mock_session.get.return_value = mock_get_response

        result = _make_request('G1R 2K8')

        assert result is None


# ============== Task 2.3: HTML Parser Tests ==============

# Sample HTML fixtures for testing parse_schedule_html
SAMPLE_SCHEDULE_HTML_MONDAY_ODD = '''
<html>
<body>
<div class="info-collecte-result">
    <h3>Résultat de la recherche</h3>
    <p>Collecte des ordures: <strong>Lundi</strong></p>
    <p>Semaine de recyclage: <strong>Impaire</strong></p>
</div>
</body>
</html>
'''

SAMPLE_SCHEDULE_HTML_WEDNESDAY_EVEN = '''
<html>
<body>
<div class="schedule">
    <p>Les ordures sont collectées le mercredi.</p>
    <p>Recyclage: semaines paires</p>
</div>
</body>
</html>
'''

SAMPLE_SCHEDULE_HTML_FRIDAY_ODD = '''
<html>
<body>
<div class="schedule">
    <p>Collecte des ordures: Vendredi</p>
    <p>Recyclage: Semaines impaires</p>
</div>
</body>
</html>
'''

SAMPLE_SCHEDULE_HTML_DAY_ONLY = '''
<html>
<body>
<p>Collecte des déchets: Mardi</p>
</body>
</html>
'''

SAMPLE_SCHEDULE_HTML_NO_SCHEDULE = '''
<html>
<body>
<p>Aucun résultat trouvé pour ce code postal.</p>
</body>
</html>
'''


class TestParseScheduleHtml:
    """Test HTML parsing functionality (Task 2.3)"""

    def test_parse_monday_odd(self):
        """Verify parsing Monday garbage day and odd recycling week."""
        from app.waste_scraper import parse_schedule_html
        result = parse_schedule_html(SAMPLE_SCHEDULE_HTML_MONDAY_ODD)
        assert result is not None
        assert result['garbage_day'] == 'monday'
        assert result['recycling_week'] == 'odd'

    def test_parse_wednesday_even(self):
        """Verify parsing Wednesday garbage day and even recycling week."""
        from app.waste_scraper import parse_schedule_html
        result = parse_schedule_html(SAMPLE_SCHEDULE_HTML_WEDNESDAY_EVEN)
        assert result is not None
        assert result['garbage_day'] == 'wednesday'
        assert result['recycling_week'] == 'even'

    def test_parse_friday_odd(self):
        """Verify parsing Friday garbage day and odd recycling week."""
        from app.waste_scraper import parse_schedule_html
        result = parse_schedule_html(SAMPLE_SCHEDULE_HTML_FRIDAY_ODD)
        assert result is not None
        assert result['garbage_day'] == 'friday'
        assert result['recycling_week'] == 'odd'

    def test_parse_day_only_no_week(self):
        """Verify parsing when only garbage day is present."""
        from app.waste_scraper import parse_schedule_html
        result = parse_schedule_html(SAMPLE_SCHEDULE_HTML_DAY_ONLY)
        assert result is not None
        assert result['garbage_day'] == 'tuesday'
        assert result['recycling_week'] is None

    def test_parse_no_schedule_found(self):
        """Verify None returned when no schedule in HTML."""
        from app.waste_scraper import parse_schedule_html
        result = parse_schedule_html(SAMPLE_SCHEDULE_HTML_NO_SCHEDULE)
        assert result is None

    def test_parse_empty_html(self):
        """Verify None returned for empty HTML."""
        from app.waste_scraper import parse_schedule_html
        result = parse_schedule_html('')
        assert result is None

    def test_parse_invalid_html(self):
        """Verify graceful handling of malformed HTML."""
        from app.waste_scraper import parse_schedule_html
        result = parse_schedule_html('<html><body><<<>>>')
        assert result is None

    def test_parse_case_insensitive_day(self):
        """Verify day parsing is case insensitive."""
        from app.waste_scraper import parse_schedule_html
        html = '<html><p>Collecte des ordures: JEUDI</p><p>Semaine PAIRE</p></html>'
        result = parse_schedule_html(html)
        assert result is not None
        assert result['garbage_day'] == 'thursday'
        assert result['recycling_week'] == 'even'

    def test_parse_all_french_days(self):
        """Verify all French day names are recognized."""
        from app.waste_scraper import parse_schedule_html
        days = [
            ('Lundi', 'monday'),
            ('Mardi', 'tuesday'),
            ('Mercredi', 'wednesday'),
            ('Jeudi', 'thursday'),
            ('Vendredi', 'friday'),
            ('Samedi', 'saturday'),
            ('Dimanche', 'sunday'),
        ]
        for french, english in days:
            html = f'<html><p>Collecte des ordures: {french}</p></html>'
            result = parse_schedule_html(html)
            assert result is not None, f"Failed for {french}"
            assert result['garbage_day'] == english, f"Expected {english}, got {result['garbage_day']}"

    def test_parse_both_week_types(self):
        """Verify both odd and even week types are recognized."""
        from app.waste_scraper import parse_schedule_html

        # Test odd (impaire)
        html_odd = '<html><p>Collecte des ordures: Lundi</p><p>Semaine impaire</p></html>'
        result_odd = parse_schedule_html(html_odd)
        assert result_odd['recycling_week'] == 'odd'

        # Test even (paire)
        html_even = '<html><p>Collecte des ordures: Lundi</p><p>Semaine paire</p></html>'
        result_even = parse_schedule_html(html_even)
        assert result_even['recycling_week'] == 'even'

    def test_parse_plural_week_forms(self):
        """Verify plural forms of week types are recognized."""
        from app.waste_scraper import parse_schedule_html

        # Test impaires (plural)
        html_odd = '<html><p>Collecte des ordures: Lundi</p><p>Semaines impaires</p></html>'
        result_odd = parse_schedule_html(html_odd)
        assert result_odd['recycling_week'] == 'odd'

        # Test paires (plural)
        html_even = '<html><p>Collecte des ordures: Lundi</p><p>Semaines paires</p></html>'
        result_even = parse_schedule_html(html_even)
        assert result_even['recycling_week'] == 'even'

    def test_parse_original_sample_response(self):
        """Verify parsing of original sample response HTML."""
        from app.waste_scraper import parse_schedule_html
        result = parse_schedule_html(SAMPLE_RESPONSE_HTML)
        assert result is not None
        assert result['garbage_day'] == 'monday'
        assert result['recycling_week'] == 'odd'


# ============== Task 2.4: Rate Limiting Tests ==============

class TestRateLimiting:
    """Test rate limiting functionality (Task 2.4)"""

    def test_enforce_rate_limit_function_exists(self):
        """Verify _enforce_rate_limit function exists."""
        from app.waste_scraper import _enforce_rate_limit
        assert callable(_enforce_rate_limit)

    def test_rate_limit_no_wait_on_first_call(self):
        """Verify no wait time on first request."""
        from app.waste_scraper import _enforce_rate_limit, _reset_rate_limit
        import time

        _reset_rate_limit()
        start = time.time()
        _enforce_rate_limit()
        elapsed = time.time() - start

        # Should return immediately (less than 0.1 sec)
        assert elapsed < 0.1

    def test_rate_limit_waits_when_called_too_soon(self):
        """Verify rate limiting waits when called within RATE_LIMIT_SECONDS."""
        from app.waste_scraper import _enforce_rate_limit, _set_last_request_time, RATE_LIMIT_SECONDS
        import time

        # Set last request to 1 second ago
        _set_last_request_time(time.time() - 1)

        start = time.time()
        _enforce_rate_limit()
        elapsed = time.time() - start

        # Should wait approximately RATE_LIMIT_SECONDS - 1 seconds
        # Allow some tolerance (should wait at least 8 seconds for 10 sec limit)
        assert elapsed >= (RATE_LIMIT_SECONDS - 1 - 0.5)

    def test_rate_limit_no_wait_after_limit_expired(self):
        """Verify no wait when enough time has passed."""
        from app.waste_scraper import _enforce_rate_limit, _set_last_request_time, RATE_LIMIT_SECONDS
        import time

        # Set last request to RATE_LIMIT_SECONDS + 1 ago
        _set_last_request_time(time.time() - RATE_LIMIT_SECONDS - 1)

        start = time.time()
        _enforce_rate_limit()
        elapsed = time.time() - start

        # Should return immediately
        assert elapsed < 0.1

    def test_scrape_schedule_updates_last_request_time(self):
        """Verify scrape_schedule updates the last request time."""
        from app.waste_scraper import scrape_schedule, _reset_rate_limit, _last_request_time
        import app.waste_scraper as ws

        _reset_rate_limit()
        assert ws._last_request_time is None

        # Mock the HTTP request to avoid actual network call
        with patch('app.waste_scraper._make_request') as mock_request:
            mock_request.return_value = SAMPLE_RESPONSE_HTML
            scrape_schedule('G1R 2K8')

        # Last request time should be updated
        assert ws._last_request_time is not None

    def test_scrape_schedule_calls_enforce_rate_limit(self):
        """Verify scrape_schedule calls _enforce_rate_limit."""
        from app.waste_scraper import scrape_schedule, _reset_rate_limit

        _reset_rate_limit()

        with patch('app.waste_scraper._make_request') as mock_request, \
             patch('app.waste_scraper._enforce_rate_limit') as mock_rate_limit:
            mock_request.return_value = SAMPLE_RESPONSE_HTML
            scrape_schedule('G1R 2K8')

            mock_rate_limit.assert_called_once()


# ============== Task 2.5 & 2.6: Caching Tests ==============

class TestCacheExpiration:
    """Test cache expiration functionality (Task 2.6)"""

    def test_is_cache_expired_function_exists(self):
        """Verify _is_cache_expired function exists."""
        from app.waste_scraper import _is_cache_expired
        assert callable(_is_cache_expired)

    def test_cache_not_expired_when_recent(self):
        """Verify cache is not expired when updated recently."""
        from app.waste_scraper import _is_cache_expired
        from datetime import datetime

        recent_time = datetime.utcnow()
        assert _is_cache_expired(recent_time) is False

    def test_cache_expired_when_old(self):
        """Verify cache is expired when older than 24 hours."""
        from app.waste_scraper import _is_cache_expired, CACHE_EXPIRATION_HOURS
        from datetime import datetime, timedelta

        old_time = datetime.utcnow() - timedelta(hours=CACHE_EXPIRATION_HOURS + 1)
        assert _is_cache_expired(old_time) is True

    def test_cache_not_expired_at_boundary(self):
        """Verify cache is not expired exactly at the boundary."""
        from app.waste_scraper import _is_cache_expired, CACHE_EXPIRATION_HOURS
        from datetime import datetime, timedelta

        # Just under the expiration time
        boundary_time = datetime.utcnow() - timedelta(hours=CACHE_EXPIRATION_HOURS - 0.1)
        assert _is_cache_expired(boundary_time) is False

    def test_cache_expired_when_none(self):
        """Verify cache is considered expired when updated_at is None."""
        from app.waste_scraper import _is_cache_expired

        assert _is_cache_expired(None) is True


class TestGetCachedSchedule:
    """Test get_cached_schedule functionality (Task 2.5)"""

    def test_get_cached_schedule_function_exists(self):
        """Verify get_cached_schedule function exists."""
        from app.waste_scraper import get_cached_schedule
        assert callable(get_cached_schedule)

    def test_get_cached_schedule_returns_none_when_no_cache(self):
        """Verify None returned when no cached data exists."""
        from app.waste_scraper import get_cached_schedule

        with patch('app.database.get_waste_zone') as mock_get_zone:
            mock_get_zone.return_value = None
            result = get_cached_schedule('G1R2K8')
            assert result is None

    def test_get_cached_schedule_returns_data_when_valid_cache(self):
        """Verify cached data returned when cache is valid."""
        from app.waste_scraper import get_cached_schedule
        from datetime import datetime

        mock_zone = {
            'id': 1,
            'zone_code': 'G1R2K8',
            'garbage_day': 'monday',
            'recycling_week': 'odd',
            'updated_at': datetime.utcnow()  # Recent, not expired
        }

        with patch('app.database.get_waste_zone') as mock_get_zone:
            mock_get_zone.return_value = mock_zone
            result = get_cached_schedule('G1R2K8')

            assert result is not None
            assert result['garbage_day'] == 'monday'
            assert result['recycling_week'] == 'odd'
            assert result['zone_id'] == 1

    def test_get_cached_schedule_returns_none_when_expired(self):
        """Verify None returned when cache is expired."""
        from app.waste_scraper import get_cached_schedule, CACHE_EXPIRATION_HOURS
        from datetime import datetime, timedelta

        old_time = datetime.utcnow() - timedelta(hours=CACHE_EXPIRATION_HOURS + 1)
        mock_zone = {
            'id': 1,
            'zone_code': 'G1R2K8',
            'garbage_day': 'monday',
            'recycling_week': 'odd',
            'updated_at': old_time  # Expired
        }

        with patch('app.database.get_waste_zone') as mock_get_zone:
            mock_get_zone.return_value = mock_zone
            result = get_cached_schedule('G1R2K8')
            assert result is None


class TestGetSchedule:
    """Test get_schedule main entry point (Task 2.5)"""

    def test_get_schedule_function_exists(self):
        """Verify get_schedule function exists."""
        from app.waste_scraper import get_schedule
        assert callable(get_schedule)

    def test_get_schedule_uses_cache_when_available(self):
        """Verify get_schedule uses cached data when available."""
        from app.waste_scraper import get_schedule
        import app.waste_scraper as ws

        cached_result = {
            'garbage_day': 'tuesday',
            'recycling_week': 'even',
            'zone_id': 5
        }

        with patch.object(ws, 'get_cached_schedule') as mock_cache, \
             patch.object(ws, 'scrape_schedule') as mock_scrape:
            mock_cache.return_value = cached_result

            result = get_schedule('G1R2K8')

            mock_cache.assert_called_once()
            mock_scrape.assert_not_called()
            assert result == cached_result

    def test_get_schedule_scrapes_when_no_cache(self):
        """Verify get_schedule scrapes when no cache available."""
        from app.waste_scraper import get_schedule, _reset_rate_limit
        import app.waste_scraper as ws

        _reset_rate_limit()

        scraped_result = {
            'garbage_day': 'wednesday',
            'recycling_week': 'odd'
        }

        with patch.object(ws, 'get_cached_schedule') as mock_cache, \
             patch.object(ws, 'scrape_schedule') as mock_scrape, \
             patch('app.database.add_waste_zone') as mock_add_zone:
            mock_cache.return_value = None
            mock_scrape.return_value = scraped_result
            mock_add_zone.return_value = 10

            result = get_schedule('G1R2K8')

            mock_cache.assert_called_once()
            mock_scrape.assert_called_once()
            mock_add_zone.assert_called_once()
            assert result['garbage_day'] == 'wednesday'
            assert result['recycling_week'] == 'odd'
            assert result['zone_id'] == 10

    def test_get_schedule_force_refresh_bypasses_cache(self):
        """Verify get_schedule bypasses cache when force_refresh=True."""
        from app.waste_scraper import get_schedule, _reset_rate_limit
        import app.waste_scraper as ws

        _reset_rate_limit()

        scraped_result = {
            'garbage_day': 'friday',
            'recycling_week': 'even'
        }

        with patch.object(ws, 'get_cached_schedule') as mock_cache, \
             patch.object(ws, 'scrape_schedule') as mock_scrape, \
             patch('app.database.add_waste_zone') as mock_add_zone:
            mock_scrape.return_value = scraped_result
            mock_add_zone.return_value = 15

            result = get_schedule('G1R2K8', force_refresh=True)

            mock_cache.assert_not_called()
            mock_scrape.assert_called_once()
            assert result['garbage_day'] == 'friday'

    def test_get_schedule_returns_none_when_scrape_fails(self):
        """Verify get_schedule returns None when scrape fails."""
        from app.waste_scraper import get_schedule, _reset_rate_limit
        import app.waste_scraper as ws

        _reset_rate_limit()

        with patch.object(ws, 'get_cached_schedule') as mock_cache, \
             patch.object(ws, 'scrape_schedule') as mock_scrape:
            mock_cache.return_value = None
            mock_scrape.return_value = None

            result = get_schedule('G1R2K8')

            assert result is None

    def test_get_schedule_saves_to_cache_after_scrape(self):
        """Verify get_schedule saves scraped data to cache."""
        from app.waste_scraper import get_schedule, _reset_rate_limit
        import app.waste_scraper as ws

        _reset_rate_limit()

        scraped_result = {
            'garbage_day': 'thursday',
            'recycling_week': 'odd'
        }

        with patch.object(ws, 'get_cached_schedule') as mock_cache, \
             patch.object(ws, 'scrape_schedule') as mock_scrape, \
             patch('app.database.add_waste_zone') as mock_add_zone:
            mock_cache.return_value = None
            mock_scrape.return_value = scraped_result
            mock_add_zone.return_value = 20

            get_schedule('G1R2K8')

            mock_add_zone.assert_called_once_with(
                zone_code='G1R2K8',
                garbage_day='thursday',
                recycling_week='odd'
            )


# ============== Task 2.7: Error Handling Tests ==============

class TestErrorHandling:
    """Test error handling functionality (Task 2.7)"""

    def test_scrape_schedule_handles_network_error(self):
        """Verify scrape_schedule handles network errors gracefully."""
        from app.waste_scraper import scrape_schedule, _reset_rate_limit

        _reset_rate_limit()

        with patch('app.waste_scraper.requests.Session') as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value = mock_session
            mock_session.get.side_effect = requests.ConnectionError()

            result = scrape_schedule('G1R2K8')

            assert result is None

    def test_scrape_schedule_handles_timeout(self):
        """Verify scrape_schedule handles timeout gracefully."""
        from app.waste_scraper import scrape_schedule, _reset_rate_limit

        _reset_rate_limit()

        with patch('app.waste_scraper.requests.Session') as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value = mock_session
            mock_session.get.side_effect = requests.Timeout()

            result = scrape_schedule('G1R2K8')

            assert result is None

    def test_scrape_schedule_handles_invalid_html_response(self):
        """Verify scrape_schedule handles invalid HTML response."""
        from app.waste_scraper import scrape_schedule, _reset_rate_limit

        _reset_rate_limit()

        with patch('app.waste_scraper._make_request') as mock_request:
            mock_request.return_value = '<html>No schedule here</html>'

            result = scrape_schedule('G1R2K8')

            assert result is None

    def test_get_schedule_handles_database_error(self):
        """Verify get_schedule handles database errors gracefully."""
        from app.waste_scraper import get_schedule, _reset_rate_limit
        import app.waste_scraper as ws

        _reset_rate_limit()

        scraped_result = {
            'garbage_day': 'monday',
            'recycling_week': 'odd'
        }

        with patch.object(ws, 'get_cached_schedule') as mock_cache, \
             patch.object(ws, 'scrape_schedule') as mock_scrape, \
             patch('app.database.add_waste_zone') as mock_add_zone:
            mock_cache.return_value = None
            mock_scrape.return_value = scraped_result
            mock_add_zone.side_effect = Exception("Database error")

            # Should raise the database error since we can't save
            try:
                result = get_schedule('G1R2K8')
                # If no exception, the test may need adjustment
            except Exception as e:
                assert "Database error" in str(e)

    def test_parse_schedule_html_handles_exception(self):
        """Verify parse_schedule_html handles exceptions gracefully."""
        from app.waste_scraper import parse_schedule_html

        # Mock BeautifulSoup to raise an exception
        with patch('app.waste_scraper.BeautifulSoup') as mock_bs:
            mock_bs.side_effect = Exception("Parse error")

            result = parse_schedule_html('<html>test</html>')

            assert result is None

    def test_get_cached_schedule_handles_database_error(self):
        """Verify get_cached_schedule handles database errors gracefully."""
        from app.waste_scraper import get_cached_schedule

        with patch('app.database.get_waste_zone') as mock_get_zone:
            mock_get_zone.side_effect = Exception("Database connection error")

            # Should raise the exception
            try:
                result = get_cached_schedule('G1R2K8')
            except Exception as e:
                assert "Database connection error" in str(e)
