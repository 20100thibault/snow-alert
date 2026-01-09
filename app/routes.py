"""
Flask Routes for Quebec City Alerts
"""

import re
import logging
from datetime import date, timedelta
from typing import Optional, Dict, Any, Tuple
from flask import Blueprint, request, jsonify, render_template
from app.database import (
    add_user, get_user_by_email, remove_user,
    update_user_preferences, get_waste_zone_by_id
)
from app.snow_checker import geocode_postal_code, check_postal_code
from app.email_service import send_welcome_email
from app.waste_scraper import get_schedule

logger = logging.getLogger(__name__)

bp = Blueprint('main', __name__)

# Regex patterns for validation
EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
POSTAL_CODE_PATTERN = re.compile(r'^[A-Z]\d[A-Z]\d[A-Z]\d$')

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


# ============== Validation Helpers ==============

def is_valid_email(email: str) -> bool:
    """Validate email format."""
    return bool(EMAIL_PATTERN.match(email))


def is_valid_postal_code(postal_code: str) -> bool:
    """Validate Canadian postal code format."""
    normalized = postal_code.upper().replace(' ', '')
    return bool(POSTAL_CODE_PATTERN.match(normalized))


def validate_email_field(email: str) -> Tuple[Optional[str], int]:
    """Validate email and return error response tuple if invalid, or (None, 0) if valid."""
    if not email:
        return jsonify({'error': 'Email is required'}), 400
    if not is_valid_email(email):
        return jsonify({'error': 'Invalid email format'}), 400
    return None, 0


def validate_postal_code_field(postal_code: str) -> Tuple[Optional[str], int]:
    """Validate postal code and return error response tuple if invalid, or (None, 0) if valid."""
    if not postal_code:
        return jsonify({'error': 'Postal code is required'}), 400
    if not is_valid_postal_code(postal_code):
        return jsonify({'error': 'Invalid postal code format. Use format like G1R 2K8'}), 400
    return None, 0


def parse_bool_preference(value: Any, default: bool) -> bool:
    """Parse a boolean preference value from various input types."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ('true', '1', 'yes', 'on')
    return bool(value)


# ============== Date Calculation Helpers ==============

def get_week_parity(d: date) -> str:
    """Get the parity of the ISO week number for a given date. Returns 'odd' or 'even'."""
    week_number = d.isocalendar()[1]
    return 'odd' if week_number % 2 == 1 else 'even'


def get_next_weekday(from_date: date, target_weekday: int) -> date:
    """
    Get the next occurrence of a weekday from a given date.
    If from_date is the target weekday, returns the next week's occurrence.
    """
    days_ahead = target_weekday - from_date.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return from_date + timedelta(days=days_ahead)


def get_next_garbage_date(garbage_day: str, from_date: date = None) -> Optional[str]:
    """Calculate the next garbage collection date. Returns ISO format date string."""
    if from_date is None:
        from_date = date.today()

    if garbage_day not in DAY_TO_WEEKDAY:
        return None

    target_weekday = DAY_TO_WEEKDAY[garbage_day]
    next_date = get_next_weekday(from_date, target_weekday)
    return next_date.isoformat()


def get_next_recycling_date(garbage_day: str, recycling_week: str, from_date: date = None) -> Optional[str]:
    """
    Calculate the next recycling collection date.
    Recycling is collected on the same day as garbage, but only on odd or even weeks.
    Returns ISO format date string.
    """
    if from_date is None:
        from_date = date.today()

    if garbage_day not in DAY_TO_WEEKDAY or recycling_week not in ('odd', 'even'):
        return None

    target_weekday = DAY_TO_WEEKDAY[garbage_day]
    next_date = get_next_weekday(from_date, target_weekday)

    if get_week_parity(next_date) != recycling_week:
        next_date += timedelta(days=7)

    return next_date.isoformat()


def build_next_events(postal_code: str, waste_schedule: dict = None) -> dict:
    """Build the next_events object for the response."""
    next_events = {
        'snow_removal': None,
        'garbage': None,
        'recycling': None
    }

    try:
        has_operation, _ = check_postal_code(postal_code)
        if has_operation:
            next_events['snow_removal'] = date.today().isoformat()
    except Exception as e:
        logger.error(f"Error checking snow removal for {postal_code}: {e}")

    if waste_schedule:
        garbage_day = waste_schedule.get('garbage_day')
        recycling_week = waste_schedule.get('recycling_week')

        if garbage_day:
            next_events['garbage'] = get_next_garbage_date(garbage_day)
            if recycling_week:
                next_events['recycling'] = get_next_recycling_date(garbage_day, recycling_week)

    return next_events


@bp.route('/')
def index():
    """Serve the main page."""
    return render_template('index.html')


def _extract_preferences(data: dict) -> Tuple[bool, bool, bool]:
    """Extract and parse alert preferences from request data."""
    preferences = data.get('preferences', {})
    if isinstance(preferences, str):
        preferences = {}

    snow_alerts = parse_bool_preference(preferences.get('snow_alerts'), default=True)
    garbage_alerts = parse_bool_preference(preferences.get('garbage_alerts'), default=False)
    recycling_alerts = parse_bool_preference(preferences.get('recycling_alerts'), default=False)

    return snow_alerts, garbage_alerts, recycling_alerts


def _fetch_waste_schedule(postal_code: str, garbage_alerts: bool, recycling_alerts: bool):
    """Fetch waste schedule if waste alerts are enabled. Returns (waste_zone_id, waste_schedule)."""
    if not (garbage_alerts or recycling_alerts):
        return None, None

    try:
        waste_schedule = get_schedule(postal_code)
        if waste_schedule:
            logger.info(f"Scraped waste schedule for {postal_code}: zone_id={waste_schedule.get('zone_id')}")
            return waste_schedule.get('zone_id'), waste_schedule
        logger.warning(f"Could not scrape waste schedule for {postal_code}")
    except Exception as e:
        logger.error(f"Error scraping waste schedule for {postal_code}: {e}")

    return None, None


def _build_subscribe_response(message: str, preferences: dict, next_events: dict, waste_schedule: dict = None) -> dict:
    """Build the response data for subscribe/update endpoints."""
    response_data = {
        'success': True,
        'message': message,
        'preferences': preferences,
        'next_events': next_events
    }

    if waste_schedule:
        response_data['waste_schedule'] = {
            'garbage_day': waste_schedule.get('garbage_day'),
            'recycling_week': waste_schedule.get('recycling_week')
        }

    return response_data


@bp.route('/subscribe', methods=['POST'])
def subscribe():
    """Subscribe a user to Quebec City alerts."""
    data = request.get_json() or request.form

    email = data.get('email', '').strip()
    postal_code = data.get('postal_code', '').strip()

    # Validate inputs
    error, code = validate_email_field(email)
    if error:
        return error, code

    error, code = validate_postal_code_field(postal_code)
    if error:
        return error, code

    # Extract preferences
    snow_alerts, garbage_alerts, recycling_alerts = _extract_preferences(data)

    if not (snow_alerts or garbage_alerts or recycling_alerts):
        return jsonify({'error': 'At least one alert type must be enabled'}), 400

    # Geocode postal code
    location = geocode_postal_code(postal_code)
    if not location:
        return jsonify({'error': 'Could not find postal code. Make sure it is in Quebec City.'}), 400

    # Fetch waste schedule if needed
    waste_zone_id, waste_schedule = _fetch_waste_schedule(postal_code, garbage_alerts, recycling_alerts)

    # Check for existing user and create/update accordingly
    existing = get_user_by_email(email)

    if existing:
        try:
            update_user_preferences(
                email=email,
                snow_alerts=snow_alerts,
                garbage_alerts=garbage_alerts,
                recycling_alerts=recycling_alerts,
                postal_code=postal_code,
                lat=location['lat'],
                lon=location['lon'],
                waste_zone_id=waste_zone_id
            )
            status_code = 200
            message = f'Successfully updated preferences for {email}'
        except Exception:
            return jsonify({'error': 'Failed to update preferences'}), 500
    else:
        try:
            add_user(
                email=email,
                postal_code=postal_code,
                lat=location['lat'],
                lon=location['lon'],
                snow_alerts=snow_alerts,
                garbage_alerts=garbage_alerts,
                recycling_alerts=recycling_alerts,
                waste_zone_id=waste_zone_id
            )
            status_code = 201
            message = f'Successfully subscribed {email} for postal code {postal_code}'
            send_welcome_email(email, postal_code)
        except Exception:
            return jsonify({'error': 'Failed to save subscription'}), 500

    next_events = build_next_events(postal_code, waste_schedule)
    preferences = {
        'snow_alerts': snow_alerts,
        'garbage_alerts': garbage_alerts,
        'recycling_alerts': recycling_alerts
    }

    return jsonify(_build_subscribe_response(message, preferences, next_events, waste_schedule)), status_code


@bp.route('/preferences', methods=['PUT'])
def update_preferences():
    """Update alert preferences for an existing user."""
    data = request.get_json() or request.form
    email = data.get('email', '').strip()

    # Validate email
    error, code = validate_email_field(email)
    if error:
        return error, code

    # Check if user exists
    user = get_user_by_email(email)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    # Extract and merge preferences with existing values
    snow_alerts = parse_bool_preference(data.get('snow_alerts'), user.snow_alerts_enabled)
    garbage_alerts = parse_bool_preference(data.get('garbage_alerts'), user.garbage_alerts_enabled)
    recycling_alerts = parse_bool_preference(data.get('recycling_alerts'), user.recycling_alerts_enabled)

    if not (snow_alerts or garbage_alerts or recycling_alerts):
        return jsonify({'error': 'At least one alert type must be enabled'}), 400

    # Fetch waste schedule if waste alerts newly enabled and no zone assigned
    waste_zone_id = user.waste_zone_id
    waste_schedule = None
    if (garbage_alerts or recycling_alerts) and not waste_zone_id:
        waste_zone_id, waste_schedule = _fetch_waste_schedule(user.postal_code, garbage_alerts, recycling_alerts)

    # Update preferences
    try:
        update_user_preferences(
            email=email,
            snow_alerts=snow_alerts,
            garbage_alerts=garbage_alerts,
            recycling_alerts=recycling_alerts,
            waste_zone_id=waste_zone_id
        )
    except Exception as e:
        logger.error(f"Error updating preferences for {email}: {e}")
        return jsonify({'error': 'Failed to update preferences'}), 500

    preferences = {
        'snow_alerts': snow_alerts,
        'garbage_alerts': garbage_alerts,
        'recycling_alerts': recycling_alerts
    }

    response_data = {
        'success': True,
        'message': f'Successfully updated preferences for {email}',
        'preferences': preferences
    }

    if waste_schedule:
        response_data['waste_schedule'] = {
            'garbage_day': waste_schedule.get('garbage_day'),
            'recycling_week': waste_schedule.get('recycling_week')
        }

    return jsonify(response_data), 200


@bp.route('/subscriber/<email>')
def get_subscriber(email: str):
    """Get subscription status and preferences for a user."""
    email = email.strip()

    error, code = validate_email_field(email)
    if error:
        return error, code

    user = get_user_by_email(email)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    # Build waste schedule from waste zone if linked
    waste_schedule = None
    if user.waste_zone_id:
        waste_zone = get_waste_zone_by_id(user.waste_zone_id)
        if waste_zone:
            waste_schedule = {
                'garbage_day': waste_zone['garbage_day'],
                'recycling_week': waste_zone['recycling_week']
            }

    response_data = {
        'email': user.email,
        'postal_code': user.postal_code,
        'active': user.active,
        'preferences': {
            'snow_alerts': user.snow_alerts_enabled,
            'garbage_alerts': user.garbage_alerts_enabled,
            'recycling_alerts': user.recycling_alerts_enabled
        },
        'next_events': build_next_events(user.postal_code, waste_schedule)
    }

    if waste_schedule:
        response_data['waste_schedule'] = waste_schedule

    return jsonify(response_data), 200


@bp.route('/unsubscribe', methods=['POST'])
def unsubscribe():
    """Unsubscribe a user from all alerts and remove their subscription."""
    data = request.get_json() or request.form
    email = data.get('email', '').strip()

    error, code = validate_email_field(email)
    if error:
        return error, code

    if remove_user(email):
        return jsonify({'success': True, 'message': f'Successfully unsubscribed {email}'}), 200
    return jsonify({'error': 'Email not found'}), 404


@bp.route('/status/<postal_code>')
def status(postal_code: str):
    """Check current snow removal status for a postal code."""
    if not is_valid_postal_code(postal_code):
        return jsonify({'error': 'Invalid postal code format'}), 400

    has_operation, streets = check_postal_code(postal_code)
    normalized_code = postal_code.upper().replace(' ', '')

    message = 'Snow removal in progress - NO PARKING' if has_operation else 'No active snow removal operation'

    return jsonify({
        'postal_code': normalized_code,
        'has_operation': has_operation,
        'streets_affected': streets,
        'message': message
    }), 200


@bp.route('/schedule/<postal_code>')
def schedule(postal_code: str):
    """Get waste collection schedule for a postal code."""
    if not is_valid_postal_code(postal_code):
        return jsonify({'error': 'Invalid postal code format'}), 400

    try:
        waste_schedule = get_schedule(postal_code)
    except Exception as e:
        logger.error(f"Error getting schedule for {postal_code}: {e}")
        return jsonify({'error': 'Failed to retrieve schedule'}), 500

    if not waste_schedule:
        return jsonify({'error': 'Could not find schedule for this postal code'}), 404

    garbage_day = waste_schedule.get('garbage_day')
    recycling_week = waste_schedule.get('recycling_week')

    return jsonify({
        'postal_code': postal_code.upper().replace(' ', ''),
        'garbage_day': garbage_day,
        'recycling_week': recycling_week,
        'next_garbage': get_next_garbage_date(garbage_day) if garbage_day else None,
        'next_recycling': get_next_recycling_date(garbage_day, recycling_week) if garbage_day and recycling_week else None
    }), 200


@bp.route('/quick-check/<postal_code>')
def quick_check(postal_code: str):
    """Quick check snow status and waste schedule for a postal code without subscribing."""
    if not is_valid_postal_code(postal_code):
        return jsonify({'error': 'Invalid postal code format. Use format like G1R 2K8'}), 400

    normalized_code = postal_code.upper().replace(' ', '')

    # Get snow status
    snow_status = {
        'has_operation': False,
        'streets_affected': [],
        'message': 'No active snow removal operation'
    }
    try:
        has_operation, streets = check_postal_code(postal_code)
        snow_status = {
            'has_operation': has_operation,
            'streets_affected': streets,
            'message': 'Snow removal in progress - NO PARKING' if has_operation else 'No active snow removal operation'
        }
    except Exception as e:
        logger.error(f"Error checking snow status for {normalized_code}: {e}")

    # Get waste schedule
    waste_schedule = None
    waste_schedule_error = None
    next_events = {
        'next_garbage': None,
        'next_recycling': None
    }
    try:
        waste_schedule = get_schedule(postal_code)
        if waste_schedule:
            garbage_day = waste_schedule.get('garbage_day')
            recycling_week = waste_schedule.get('recycling_week')
            if garbage_day:
                next_events['next_garbage'] = get_next_garbage_date(garbage_day)
                if recycling_week:
                    next_events['next_recycling'] = get_next_recycling_date(garbage_day, recycling_week)
        else:
            waste_schedule_error = 'Could not find waste schedule for this postal code'
            logger.warning(f"Waste schedule not found for postal code: {normalized_code}")
    except Exception as e:
        waste_schedule_error = 'Unable to fetch waste schedule. Please try again.'
        logger.error(f"Error getting waste schedule for {normalized_code}: {type(e).__name__}: {e}")

    response_data = {
        'postal_code': normalized_code,
        'snow_status': snow_status,
        'next_events': next_events,
        'waste_schedule': {
            'garbage_day': waste_schedule.get('garbage_day') if waste_schedule else None,
            'recycling_week': waste_schedule.get('recycling_week') if waste_schedule else None
        }
    }

    if waste_schedule_error:
        response_data['waste_schedule_error'] = waste_schedule_error

    return jsonify(response_data), 200


@bp.route('/admin/trigger-check', methods=['GET', 'POST'])
def admin_trigger_check():
    """Manually trigger the snow removal check for all users."""
    from app.scheduler import trigger_check_now
    return jsonify({'success': True, 'message': 'Check triggered successfully', 'result': trigger_check_now()}), 200


@bp.route('/admin/jobs')
def admin_jobs():
    """View scheduled jobs."""
    from app.scheduler import get_scheduled_jobs
    return jsonify({'jobs': get_scheduled_jobs()}), 200


@bp.route('/admin/trigger-waste-check', methods=['GET', 'POST'])
def admin_trigger_waste_check():
    """Manually trigger the waste reminder check for all users."""
    from app.scheduler import trigger_waste_check_now

    result = trigger_waste_check_now()
    return jsonify({
        'success': True,
        'message': 'Waste check triggered successfully',
        'result': {
            'garbage_sent': result.get('garbage_sent', 0),
            'recycling_sent': result.get('recycling_sent', 0),
            'skipped': result.get('skipped', 0),
            'errors': result.get('errors', 0)
        }
    }), 200


@bp.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({'error': 'Not found'}), 404


@bp.errorhandler(500)
def server_error(error):
    """Handle 500 errors."""
    return jsonify({'error': 'Internal server error'}), 500
