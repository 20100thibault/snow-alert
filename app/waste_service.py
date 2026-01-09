"""
Waste Collection Service

Business logic for waste collection reminder calculations and processing.
"""

import logging
from datetime import date, timedelta
from typing import Optional, Dict, Any, List, Callable

logger = logging.getLogger(__name__)

# Day name to weekday number mapping (Monday=0, Sunday=6)
DAY_TO_WEEKDAY = {
    'monday': 0,
    'tuesday': 1,
    'wednesday': 2,
    'thursday': 3,
    'friday': 4,
    'saturday': 5,
    'sunday': 6,
}

WEEKDAY_TO_DAY = {v: k for k, v in DAY_TO_WEEKDAY.items()}


def get_week_parity(d: date) -> str:
    """
    Get the parity of the ISO week number for a given date.

    Args:
        d: The date to check

    Returns:
        'odd' or 'even' based on the ISO week number
    """
    week_number = d.isocalendar()[1]
    return 'odd' if week_number % 2 == 1 else 'even'


def is_garbage_day(zone: Dict[str, Any], check_date: date) -> bool:
    """
    Check if a given date is a garbage collection day for a zone.

    Args:
        zone: Dict with 'garbage_day' key (e.g., 'monday', 'tuesday')
        check_date: The date to check

    Returns:
        True if check_date is a garbage collection day, False otherwise
    """
    garbage_day = zone.get('garbage_day')
    if not garbage_day or garbage_day not in DAY_TO_WEEKDAY:
        return False

    target_weekday = DAY_TO_WEEKDAY[garbage_day]
    return check_date.weekday() == target_weekday


def is_recycling_day(zone: Dict[str, Any], check_date: date) -> bool:
    """
    Check if a given date is a recycling collection day for a zone.

    Recycling is collected on the same weekday as garbage, but only
    on weeks matching the zone's recycling_week parity (odd or even).

    Args:
        zone: Dict with 'garbage_day' and 'recycling_week' keys
        check_date: The date to check

    Returns:
        True if check_date is a recycling collection day, False otherwise
    """
    garbage_day = zone.get('garbage_day')
    recycling_week = zone.get('recycling_week')

    if not garbage_day or garbage_day not in DAY_TO_WEEKDAY:
        return False

    if recycling_week not in ('odd', 'even'):
        return False

    target_weekday = DAY_TO_WEEKDAY[garbage_day]

    # Check if weekday matches
    if check_date.weekday() != target_weekday:
        return False

    # Check if week parity matches
    return get_week_parity(check_date) == recycling_week


def is_collection_tomorrow(zone: Dict[str, Any], check_date: date = None) -> Dict[str, bool]:
    """
    Check if garbage or recycling collection is scheduled for tomorrow.

    Args:
        zone: Dict with 'garbage_day' and 'recycling_week' keys
        check_date: The date to check from (defaults to today)

    Returns:
        Dict with 'garbage' and 'recycling' boolean keys
    """
    if check_date is None:
        check_date = date.today()

    tomorrow = check_date + timedelta(days=1)

    return {
        'garbage': is_garbage_day(zone, tomorrow),
        'recycling': is_recycling_day(zone, tomorrow)
    }


def get_next_collection_dates(zone: Dict[str, Any], from_date: date = None) -> Dict[str, Optional[date]]:
    """
    Calculate the next garbage and recycling collection dates for a zone.

    Args:
        zone: Dict with 'garbage_day' and 'recycling_week' keys
        from_date: The date to calculate from (defaults to today)

    Returns:
        Dict with 'garbage' and 'recycling' keys containing date objects or None
    """
    if from_date is None:
        from_date = date.today()

    result = {
        'garbage': None,
        'recycling': None
    }

    garbage_day = zone.get('garbage_day')
    recycling_week = zone.get('recycling_week')

    if not garbage_day or garbage_day not in DAY_TO_WEEKDAY:
        return result

    target_weekday = DAY_TO_WEEKDAY[garbage_day]

    # Calculate next garbage day
    days_ahead = target_weekday - from_date.weekday()
    if days_ahead <= 0:  # Target day already happened this week or is today
        days_ahead += 7
    next_garbage = from_date + timedelta(days=days_ahead)
    result['garbage'] = next_garbage

    # Calculate next recycling day
    if recycling_week in ('odd', 'even'):
        next_recycling = next_garbage
        # If the next garbage day's week doesn't match recycling parity, add a week
        if get_week_parity(next_recycling) != recycling_week:
            next_recycling += timedelta(days=7)
        result['recycling'] = next_recycling

    return result


def _process_reminders_for_type(
    users: List,
    reminder_type: str,
    tomorrow: date,
    is_collection_day_fn: Callable,
    send_reminder_fn: Callable,
    result: Dict[str, int],
    result_key: str
) -> None:
    """
    Process reminders for a specific type (garbage or recycling).

    Args:
        users: List of users to process
        reminder_type: Type of reminder ('garbage' or 'recycling')
        tomorrow: The collection date
        is_collection_day_fn: Function to check if tomorrow is a collection day
        send_reminder_fn: Function to send the reminder email
        result: Result dict to update
        result_key: Key in result dict for successful sends
    """
    from app.database import get_waste_zone_by_id, was_reminder_sent, record_reminder_sent

    for user in users:
        try:
            if not user.waste_zone_id:
                logger.debug(f"User {user.email} has no waste zone assigned, skipping")
                result['skipped'] += 1
                continue

            zone = get_waste_zone_by_id(user.waste_zone_id)
            if not zone:
                logger.warning(f"Waste zone {user.waste_zone_id} not found for user {user.email}")
                result['skipped'] += 1
                continue

            if not is_collection_day_fn(zone, tomorrow):
                continue

            if was_reminder_sent(user.id, reminder_type, tomorrow):
                logger.debug(f"{reminder_type.capitalize()} reminder already sent to {user.email} for {tomorrow}")
                result['skipped'] += 1
                continue

            if send_reminder_fn(user.email, user.postal_code, tomorrow):
                record_reminder_sent(user.id, reminder_type, tomorrow)
                result[result_key] += 1
                logger.info(f"{reminder_type.capitalize()} reminder sent to {user.email}")
            else:
                result['errors'] += 1
                logger.error(f"Failed to send {reminder_type} reminder to {user.email}")

        except Exception as e:
            result['errors'] += 1
            logger.error(f"Error processing {reminder_type} reminder for {user.email}: {e}")


def process_waste_reminders(check_date: date = None) -> Dict[str, int]:
    """
    Process all waste reminders for the day.

    Checks all users with garbage/recycling alerts enabled,
    determines if tomorrow is a collection day, and sends
    reminder emails. Prevents duplicate reminders.

    Args:
        check_date: The date to check from (defaults to today)

    Returns:
        Dict with counts: garbage_sent, recycling_sent, skipped, errors
    """
    from app.database import get_users_with_garbage_alerts, get_users_with_recycling_alerts
    from app.email_service import send_garbage_reminder, send_recycling_reminder

    if check_date is None:
        check_date = date.today()

    tomorrow = check_date + timedelta(days=1)
    result = {'garbage_sent': 0, 'recycling_sent': 0, 'skipped': 0, 'errors': 0}

    logger.info(f"Processing waste reminders for {check_date}")

    # Process garbage reminders
    garbage_users = get_users_with_garbage_alerts()
    logger.info(f"Found {len(garbage_users)} users with garbage alerts enabled")
    _process_reminders_for_type(
        users=garbage_users,
        reminder_type='garbage',
        tomorrow=tomorrow,
        is_collection_day_fn=is_garbage_day,
        send_reminder_fn=send_garbage_reminder,
        result=result,
        result_key='garbage_sent'
    )

    # Process recycling reminders
    recycling_users = get_users_with_recycling_alerts()
    logger.info(f"Found {len(recycling_users)} users with recycling alerts enabled")
    _process_reminders_for_type(
        users=recycling_users,
        reminder_type='recycling',
        tomorrow=tomorrow,
        is_collection_day_fn=is_recycling_day,
        send_reminder_fn=send_recycling_reminder,
        result=result,
        result_key='recycling_sent'
    )

    logger.info(f"Waste reminders complete: {result}")
    return result
