"""
Tests for the Waste Collection Service module.
"""

import pytest
from datetime import date, timedelta
from unittest.mock import patch, MagicMock


class TestWasteServiceModuleExists:
    """Tests for Task 4.1: Verify waste_service module structure."""

    def test_module_imports_without_error(self):
        """Verify waste_service module can be imported."""
        import app.waste_service
        assert app.waste_service is not None

    def test_get_week_parity_function_exists(self):
        """Verify get_week_parity function exists."""
        from app.waste_service import get_week_parity
        assert callable(get_week_parity)

    def test_is_garbage_day_function_exists(self):
        """Verify is_garbage_day function exists."""
        from app.waste_service import is_garbage_day
        assert callable(is_garbage_day)

    def test_is_recycling_day_function_exists(self):
        """Verify is_recycling_day function exists."""
        from app.waste_service import is_recycling_day
        assert callable(is_recycling_day)

    def test_get_next_collection_dates_function_exists(self):
        """Verify get_next_collection_dates function exists."""
        from app.waste_service import get_next_collection_dates
        assert callable(get_next_collection_dates)

    def test_is_collection_tomorrow_function_exists(self):
        """Verify is_collection_tomorrow function exists."""
        from app.waste_service import is_collection_tomorrow
        assert callable(is_collection_tomorrow)

    def test_process_waste_reminders_function_exists(self):
        """Verify process_waste_reminders function exists."""
        from app.waste_service import process_waste_reminders
        assert callable(process_waste_reminders)

    def test_day_to_weekday_mapping_exists(self):
        """Verify DAY_TO_WEEKDAY constant exists."""
        from app.waste_service import DAY_TO_WEEKDAY
        assert isinstance(DAY_TO_WEEKDAY, dict)
        assert 'monday' in DAY_TO_WEEKDAY
        assert DAY_TO_WEEKDAY['monday'] == 0


class TestGetWeekParity:
    """Tests for Task 4.2: Week parity calculation."""

    def test_returns_odd_for_odd_week(self):
        """Verify returns 'odd' for odd ISO week numbers."""
        from app.waste_service import get_week_parity
        # Week 1 of 2025 starts on Dec 30, 2024
        # Jan 6, 2025 is in week 2 (even)
        # Jan 13, 2025 is in week 3 (odd)
        odd_week_date = date(2025, 1, 13)
        assert get_week_parity(odd_week_date) == 'odd'

    def test_returns_even_for_even_week(self):
        """Verify returns 'even' for even ISO week numbers."""
        from app.waste_service import get_week_parity
        # Jan 6, 2025 is in week 2 (even)
        even_week_date = date(2025, 1, 6)
        assert get_week_parity(even_week_date) == 'even'

    def test_consecutive_weeks_alternate_parity(self):
        """Verify consecutive weeks have alternating parity."""
        from app.waste_service import get_week_parity
        d = date(2025, 1, 6)  # Week 2
        parity1 = get_week_parity(d)
        parity2 = get_week_parity(d + timedelta(days=7))
        assert parity1 != parity2

    def test_same_week_same_parity(self):
        """Verify dates in same week have same parity."""
        from app.waste_service import get_week_parity
        monday = date(2025, 1, 6)
        friday = date(2025, 1, 10)
        assert get_week_parity(monday) == get_week_parity(friday)


class TestIsGarbageDay:
    """Tests for Task 4.3: Garbage day check."""

    def test_returns_true_when_weekday_matches(self):
        """Verify returns True when weekday matches zone's garbage_day."""
        from app.waste_service import is_garbage_day
        zone = {'garbage_day': 'monday'}
        # Jan 6, 2025 is a Monday
        monday = date(2025, 1, 6)
        assert is_garbage_day(zone, monday) is True

    def test_returns_false_for_other_weekdays(self):
        """Verify returns False for non-garbage weekdays."""
        from app.waste_service import is_garbage_day
        zone = {'garbage_day': 'monday'}
        # Jan 7, 2025 is a Tuesday
        tuesday = date(2025, 1, 7)
        assert is_garbage_day(zone, tuesday) is False

    def test_returns_false_for_invalid_garbage_day(self):
        """Verify returns False when garbage_day is invalid."""
        from app.waste_service import is_garbage_day
        zone = {'garbage_day': 'invalid'}
        monday = date(2025, 1, 6)
        assert is_garbage_day(zone, monday) is False

    def test_returns_false_for_missing_garbage_day(self):
        """Verify returns False when garbage_day is missing."""
        from app.waste_service import is_garbage_day
        zone = {}
        monday = date(2025, 1, 6)
        assert is_garbage_day(zone, monday) is False

    def test_works_for_all_weekdays(self):
        """Verify works correctly for all days of the week."""
        from app.waste_service import is_garbage_day, DAY_TO_WEEKDAY
        # Jan 6, 2025 is Monday, so Jan 6+N gives us each weekday
        for day_name, weekday_num in DAY_TO_WEEKDAY.items():
            zone = {'garbage_day': day_name}
            test_date = date(2025, 1, 6) + timedelta(days=weekday_num)
            assert is_garbage_day(zone, test_date) is True


class TestIsRecyclingDay:
    """Tests for Task 4.4: Recycling day check."""

    def test_returns_true_when_weekday_and_parity_match(self):
        """Verify returns True when weekday matches AND week parity matches."""
        from app.waste_service import is_recycling_day, get_week_parity
        zone = {'garbage_day': 'monday', 'recycling_week': 'even'}
        # Find a Monday in an even week
        monday = date(2025, 1, 6)  # Week 2 (even)
        assert get_week_parity(monday) == 'even'
        assert is_recycling_day(zone, monday) is True

    def test_returns_false_when_weekday_matches_but_wrong_week(self):
        """Verify returns False when weekday matches but wrong week parity."""
        from app.waste_service import is_recycling_day, get_week_parity
        zone = {'garbage_day': 'monday', 'recycling_week': 'odd'}
        # Jan 6, 2025 is Monday in week 2 (even)
        monday = date(2025, 1, 6)
        assert get_week_parity(monday) == 'even'
        assert is_recycling_day(zone, monday) is False

    def test_returns_false_for_non_collection_weekdays(self):
        """Verify returns False for non-collection weekdays."""
        from app.waste_service import is_recycling_day
        zone = {'garbage_day': 'monday', 'recycling_week': 'even'}
        # Tuesday in an even week
        tuesday = date(2025, 1, 7)
        assert is_recycling_day(zone, tuesday) is False

    def test_returns_false_for_invalid_recycling_week(self):
        """Verify returns False when recycling_week is invalid."""
        from app.waste_service import is_recycling_day
        zone = {'garbage_day': 'monday', 'recycling_week': 'invalid'}
        monday = date(2025, 1, 6)
        assert is_recycling_day(zone, monday) is False

    def test_returns_false_for_missing_recycling_week(self):
        """Verify returns False when recycling_week is missing."""
        from app.waste_service import is_recycling_day
        zone = {'garbage_day': 'monday'}
        monday = date(2025, 1, 6)
        assert is_recycling_day(zone, monday) is False

    def test_handles_biweekly_alternation(self):
        """Verify recycling correctly alternates every two weeks."""
        from app.waste_service import is_recycling_day
        zone = {'garbage_day': 'monday', 'recycling_week': 'even'}
        # Jan 6 is Monday week 2 (even) - recycling
        # Jan 13 is Monday week 3 (odd) - no recycling
        # Jan 20 is Monday week 4 (even) - recycling
        week2_monday = date(2025, 1, 6)
        week3_monday = date(2025, 1, 13)
        week4_monday = date(2025, 1, 20)

        assert is_recycling_day(zone, week2_monday) is True
        assert is_recycling_day(zone, week3_monday) is False
        assert is_recycling_day(zone, week4_monday) is True


class TestGetNextCollectionDates:
    """Tests for Task 4.5: Next collection date calculator."""

    def test_returns_dict_with_garbage_and_recycling_keys(self):
        """Verify returns dict with both keys."""
        from app.waste_service import get_next_collection_dates
        zone = {'garbage_day': 'monday', 'recycling_week': 'even'}
        result = get_next_collection_dates(zone)
        assert 'garbage' in result
        assert 'recycling' in result

    def test_returns_correct_next_garbage_date(self):
        """Verify returns correct next garbage date."""
        from app.waste_service import get_next_collection_dates
        zone = {'garbage_day': 'wednesday'}
        # From Tuesday Jan 7, next Wednesday is Jan 8
        from_date = date(2025, 1, 7)
        result = get_next_collection_dates(zone, from_date)
        assert result['garbage'] == date(2025, 1, 8)

    def test_returns_correct_next_recycling_date(self):
        """Verify returns correct next recycling date."""
        from app.waste_service import get_next_collection_dates, get_week_parity
        zone = {'garbage_day': 'monday', 'recycling_week': 'odd'}
        # From Jan 6 (Monday, week 2 even), next odd week Monday is Jan 13
        from_date = date(2025, 1, 6)
        result = get_next_collection_dates(zone, from_date)
        assert result['recycling'] == date(2025, 1, 13)
        assert get_week_parity(result['recycling']) == 'odd'

    def test_dates_are_always_in_future(self):
        """Verify returned dates are always in the future."""
        from app.waste_service import get_next_collection_dates
        zone = {'garbage_day': 'monday', 'recycling_week': 'even'}
        from_date = date(2025, 1, 6)  # A Monday
        result = get_next_collection_dates(zone, from_date)
        # Should return next Monday, not today
        assert result['garbage'] > from_date

    def test_handles_end_of_month(self):
        """Verify handles month boundary correctly."""
        from app.waste_service import get_next_collection_dates
        zone = {'garbage_day': 'friday'}
        # From Jan 30, 2025 (Thursday), next Friday is Jan 31
        from_date = date(2025, 1, 30)
        result = get_next_collection_dates(zone, from_date)
        assert result['garbage'] == date(2025, 1, 31)

    def test_returns_none_for_invalid_zone(self):
        """Verify returns None values for invalid zone config."""
        from app.waste_service import get_next_collection_dates
        zone = {'garbage_day': 'invalid'}
        result = get_next_collection_dates(zone)
        assert result['garbage'] is None
        assert result['recycling'] is None

    def test_returns_none_recycling_when_no_recycling_week(self):
        """Verify returns None for recycling when recycling_week is missing."""
        from app.waste_service import get_next_collection_dates
        zone = {'garbage_day': 'monday'}
        result = get_next_collection_dates(zone)
        assert result['garbage'] is not None
        assert result['recycling'] is None

    def test_uses_today_when_from_date_not_provided(self):
        """Verify uses today's date when from_date is not provided."""
        from app.waste_service import get_next_collection_dates
        zone = {'garbage_day': 'monday', 'recycling_week': 'even'}
        result = get_next_collection_dates(zone)
        today = date.today()
        # Result should be in the future
        assert result['garbage'] > today


class TestIsCollectionTomorrow:
    """Tests for is_collection_tomorrow helper function."""

    def test_returns_dict_with_garbage_and_recycling_keys(self):
        """Verify returns dict with both keys."""
        from app.waste_service import is_collection_tomorrow
        zone = {'garbage_day': 'monday', 'recycling_week': 'even'}
        result = is_collection_tomorrow(zone)
        assert 'garbage' in result
        assert 'recycling' in result

    def test_garbage_true_when_tomorrow_is_garbage_day(self):
        """Verify garbage is True when tomorrow is garbage day."""
        from app.waste_service import is_collection_tomorrow
        zone = {'garbage_day': 'tuesday'}
        # Jan 6, 2025 is Monday, so tomorrow (Tuesday) is garbage day
        monday = date(2025, 1, 6)
        result = is_collection_tomorrow(zone, monday)
        assert result['garbage'] is True

    def test_garbage_false_when_tomorrow_is_not_garbage_day(self):
        """Verify garbage is False when tomorrow is not garbage day."""
        from app.waste_service import is_collection_tomorrow
        zone = {'garbage_day': 'friday'}
        # Jan 6, 2025 is Monday, so tomorrow (Tuesday) is not Friday
        monday = date(2025, 1, 6)
        result = is_collection_tomorrow(zone, monday)
        assert result['garbage'] is False

    def test_recycling_true_when_tomorrow_matches_day_and_week(self):
        """Verify recycling is True when tomorrow matches day and week parity."""
        from app.waste_service import is_collection_tomorrow, get_week_parity
        zone = {'garbage_day': 'tuesday', 'recycling_week': 'even'}
        # Jan 6, 2025 is Monday in week 2 (even), tomorrow is Tuesday week 2
        monday = date(2025, 1, 6)
        assert get_week_parity(monday + timedelta(days=1)) == 'even'
        result = is_collection_tomorrow(zone, monday)
        assert result['recycling'] is True

    def test_recycling_false_when_wrong_week_parity(self):
        """Verify recycling is False when week parity doesn't match."""
        from app.waste_service import is_collection_tomorrow, get_week_parity
        zone = {'garbage_day': 'tuesday', 'recycling_week': 'odd'}
        # Jan 6, 2025 is Monday in week 2 (even), tomorrow is Tuesday week 2
        monday = date(2025, 1, 6)
        assert get_week_parity(monday + timedelta(days=1)) == 'even'
        result = is_collection_tomorrow(zone, monday)
        assert result['recycling'] is False


class TestProcessWasteReminders:
    """Tests for Task 4.10: process_waste_reminders function."""

    def test_returns_result_dict(self):
        """Verify returns dict with expected keys."""
        from app.waste_service import process_waste_reminders
        with patch('app.database.get_users_with_garbage_alerts', return_value=[]):
            with patch('app.database.get_users_with_recycling_alerts', return_value=[]):
                result = process_waste_reminders()
                assert 'garbage_sent' in result
                assert 'recycling_sent' in result
                assert 'skipped' in result
                assert 'errors' in result

    def test_sends_garbage_reminder_when_tomorrow_is_garbage_day(self):
        """Verify sends garbage reminder when tomorrow is garbage day."""
        from app.waste_service import process_waste_reminders

        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.email = "test@example.com"
        mock_user.postal_code = "G1R2K8"
        mock_user.waste_zone_id = 1

        mock_zone = {'garbage_day': 'tuesday', 'recycling_week': 'even'}

        # Jan 6, 2025 is Monday, tomorrow (Tuesday) is garbage day
        with patch('app.database.get_users_with_garbage_alerts', return_value=[mock_user]):
            with patch('app.database.get_users_with_recycling_alerts', return_value=[]):
                with patch('app.database.get_waste_zone_by_id', return_value=mock_zone):
                    with patch('app.database.was_reminder_sent', return_value=False):
                        with patch('app.email_service.send_garbage_reminder', return_value=True) as mock_send:
                            with patch('app.database.record_reminder_sent'):
                                result = process_waste_reminders(date(2025, 1, 6))
                                mock_send.assert_called_once()
                                assert result['garbage_sent'] == 1

    def test_skips_user_without_waste_zone(self):
        """Verify skips users without waste_zone_id."""
        from app.waste_service import process_waste_reminders

        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.email = "test@example.com"
        mock_user.postal_code = "G1R2K8"
        mock_user.waste_zone_id = None

        with patch('app.database.get_users_with_garbage_alerts', return_value=[mock_user]):
            with patch('app.database.get_users_with_recycling_alerts', return_value=[]):
                result = process_waste_reminders(date(2025, 1, 6))
                assert result['skipped'] == 1
                assert result['garbage_sent'] == 0


class TestDuplicateReminderPrevention:
    """Tests for Task 4.11: Duplicate reminder prevention."""

    def test_skips_when_reminder_already_sent(self):
        """Verify skips sending when reminder was already sent."""
        from app.waste_service import process_waste_reminders

        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.email = "test@example.com"
        mock_user.postal_code = "G1R2K8"
        mock_user.waste_zone_id = 1

        mock_zone = {'garbage_day': 'tuesday', 'recycling_week': 'even'}

        with patch('app.database.get_users_with_garbage_alerts', return_value=[mock_user]):
            with patch('app.database.get_users_with_recycling_alerts', return_value=[]):
                with patch('app.database.get_waste_zone_by_id', return_value=mock_zone):
                    with patch('app.database.was_reminder_sent', return_value=True):
                        with patch('app.email_service.send_garbage_reminder') as mock_send:
                            result = process_waste_reminders(date(2025, 1, 6))
                            mock_send.assert_not_called()
                            assert result['skipped'] == 1

    def test_records_reminder_after_successful_send(self):
        """Verify records reminder after successful send."""
        from app.waste_service import process_waste_reminders

        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.email = "test@example.com"
        mock_user.postal_code = "G1R2K8"
        mock_user.waste_zone_id = 1

        mock_zone = {'garbage_day': 'tuesday', 'recycling_week': 'even'}

        with patch('app.database.get_users_with_garbage_alerts', return_value=[mock_user]):
            with patch('app.database.get_users_with_recycling_alerts', return_value=[]):
                with patch('app.database.get_waste_zone_by_id', return_value=mock_zone):
                    with patch('app.database.was_reminder_sent', return_value=False):
                        with patch('app.email_service.send_garbage_reminder', return_value=True):
                            with patch('app.database.record_reminder_sent') as mock_record:
                                result = process_waste_reminders(date(2025, 1, 6))
                                mock_record.assert_called_once_with(1, 'garbage', date(2025, 1, 7))

    def test_does_not_record_when_send_fails(self):
        """Verify does not record reminder when send fails."""
        from app.waste_service import process_waste_reminders

        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.email = "test@example.com"
        mock_user.postal_code = "G1R2K8"
        mock_user.waste_zone_id = 1

        mock_zone = {'garbage_day': 'tuesday', 'recycling_week': 'even'}

        with patch('app.database.get_users_with_garbage_alerts', return_value=[mock_user]):
            with patch('app.database.get_users_with_recycling_alerts', return_value=[]):
                with patch('app.database.get_waste_zone_by_id', return_value=mock_zone):
                    with patch('app.database.was_reminder_sent', return_value=False):
                        with patch('app.email_service.send_garbage_reminder', return_value=False):
                            with patch('app.database.record_reminder_sent') as mock_record:
                                result = process_waste_reminders(date(2025, 1, 6))
                                mock_record.assert_not_called()
                                assert result['errors'] == 1
