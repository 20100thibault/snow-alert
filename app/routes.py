"""
Flask Routes for Quebec City Alerts
"""

import re
import logging
from datetime import date, timedelta
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


def get_week_parity(d: date) -> str:
    """
    Get the parity of the ISO week number for a given date.
    Returns 'odd' or 'even'.
    """
    week_number = d.isocalendar()[1]
    return 'odd' if week_number % 2 == 1 else 'even'


def get_next_weekday(from_date: date, target_weekday: int) -> date:
    """
    Get the next occurrence of a weekday from a given date.
    If from_date is the target weekday, returns the next week's occurrence.
    """
    days_ahead = target_weekday - from_date.weekday()
    if days_ahead <= 0:  # Target day already happened this week or is today
        days_ahead += 7
    return from_date + timedelta(days=days_ahead)


def get_next_garbage_date(garbage_day: str, from_date: date = None) -> str:
    """
    Calculate the next garbage collection date.
    Returns ISO format date string (YYYY-MM-DD).
    """
    if from_date is None:
        from_date = date.today()

    if garbage_day not in DAY_TO_WEEKDAY:
        return None

    target_weekday = DAY_TO_WEEKDAY[garbage_day]
    next_date = get_next_weekday(from_date, target_weekday)
    return next_date.isoformat()


def get_next_recycling_date(garbage_day: str, recycling_week: str, from_date: date = None) -> str:
    """
    Calculate the next recycling collection date.
    Recycling is collected on the same day as garbage, but only on odd or even weeks.
    Returns ISO format date string (YYYY-MM-DD).
    """
    if from_date is None:
        from_date = date.today()

    if garbage_day not in DAY_TO_WEEKDAY:
        return None

    if recycling_week not in ('odd', 'even'):
        return None

    target_weekday = DAY_TO_WEEKDAY[garbage_day]

    # Start from next occurrence of the garbage day
    next_date = get_next_weekday(from_date, target_weekday)

    # Check if that week matches the recycling week parity
    # If not, add a week
    if get_week_parity(next_date) != recycling_week:
        next_date += timedelta(days=7)

    return next_date.isoformat()


def build_next_events(postal_code: str, waste_schedule: dict = None) -> dict:
    """
    Build the next_events object for the response.
    """
    next_events = {
        'snow_removal': None,
        'garbage': None,
        'recycling': None
    }

    # Check for active snow removal operation
    try:
        has_operation, streets = check_postal_code(postal_code)
        if has_operation:
            next_events['snow_removal'] = date.today().isoformat()
    except Exception as e:
        logger.error(f"Error checking snow removal for {postal_code}: {e}")

    # Calculate next waste collection dates
    if waste_schedule:
        garbage_day = waste_schedule.get('garbage_day')
        recycling_week = waste_schedule.get('recycling_week')

        if garbage_day:
            next_events['garbage'] = get_next_garbage_date(garbage_day)

        if garbage_day and recycling_week:
            next_events['recycling'] = get_next_recycling_date(garbage_day, recycling_week)

    return next_events


def is_valid_email(email: str) -> bool:
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def is_valid_postal_code(postal_code: str) -> bool:
    """Validate Canadian postal code format."""
    normalized = postal_code.upper().replace(' ', '')
    pattern = r'^[A-Z]\d[A-Z]\d[A-Z]\d$'
    return bool(re.match(pattern, normalized))


@bp.route('/')
def index():
    """Serve the main page."""
    return render_template('index.html')


@bp.route('/subscribe', methods=['POST'])
def subscribe():
    """Subscribe a user to Quebec City alerts."""
    data = request.get_json() or request.form

    email = data.get('email', '').strip()
    postal_code = data.get('postal_code', '').strip()

    # Extract preferences (defaults: snow=True, garbage=False, recycling=False)
    preferences = data.get('preferences', {})
    if isinstance(preferences, str):
        preferences = {}

    snow_alerts = preferences.get('snow_alerts', True)
    garbage_alerts = preferences.get('garbage_alerts', False)
    recycling_alerts = preferences.get('recycling_alerts', False)

    # Convert string booleans if needed (from form data)
    if isinstance(snow_alerts, str):
        snow_alerts = snow_alerts.lower() in ('true', '1', 'yes', 'on')
    if isinstance(garbage_alerts, str):
        garbage_alerts = garbage_alerts.lower() in ('true', '1', 'yes', 'on')
    if isinstance(recycling_alerts, str):
        recycling_alerts = recycling_alerts.lower() in ('true', '1', 'yes', 'on')

    # Validate email
    if not email:
        return jsonify({'error': 'Email is required'}), 400
    if not is_valid_email(email):
        return jsonify({'error': 'Invalid email format'}), 400

    # Validate postal code
    if not postal_code:
        return jsonify({'error': 'Postal code is required'}), 400
    if not is_valid_postal_code(postal_code):
        return jsonify({'error': 'Invalid postal code format. Use format like G1R 2K8'}), 400

    # Validate at least one alert type is selected
    if not snow_alerts and not garbage_alerts and not recycling_alerts:
        return jsonify({'error': 'At least one alert type must be enabled'}), 400

    # Check for existing user
    existing = get_user_by_email(email)

    # Geocode postal code
    location = geocode_postal_code(postal_code)
    if not location:
        return jsonify({'error': 'Could not find postal code. Make sure it is in Quebec City.'}), 400

    # If waste alerts are enabled, scrape the schedule to get zone_id
    waste_zone_id = None
    waste_schedule = None
    if garbage_alerts or recycling_alerts:
        try:
            waste_schedule = get_schedule(postal_code)
            if waste_schedule:
                waste_zone_id = waste_schedule.get('zone_id')
                logger.info(f"Scraped waste schedule for {postal_code}: zone_id={waste_zone_id}")
            else:
                logger.warning(f"Could not scrape waste schedule for {postal_code}")
        except Exception as e:
            logger.error(f"Error scraping waste schedule for {postal_code}: {e}")
            # Continue without waste zone - user can still subscribe

    if existing:
        # Update existing user's preferences
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
        except Exception as e:
            return jsonify({'error': 'Failed to update preferences'}), 500
    else:
        # Add new user to database
        try:
            user = add_user(
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

            # Send welcome email for new subscriptions
            send_welcome_email(email, postal_code)
        except Exception as e:
            return jsonify({'error': 'Failed to save subscription'}), 500

    # Build next events
    next_events = build_next_events(postal_code, waste_schedule)

    # Build response
    response_data = {
        'success': True,
        'message': message,
        'preferences': {
            'snow_alerts': snow_alerts,
            'garbage_alerts': garbage_alerts,
            'recycling_alerts': recycling_alerts
        },
        'next_events': next_events
    }

    # Include waste schedule info if available
    if waste_schedule:
        response_data['waste_schedule'] = {
            'garbage_day': waste_schedule.get('garbage_day'),
            'recycling_week': waste_schedule.get('recycling_week')
        }

    return jsonify(response_data), status_code


@bp.route('/preferences', methods=['PUT'])
def update_preferences():
    """Update alert preferences for an existing user."""
    data = request.get_json() or request.form

    email = data.get('email', '').strip()

    # Validate email
    if not email:
        return jsonify({'error': 'Email is required'}), 400
    if not is_valid_email(email):
        return jsonify({'error': 'Invalid email format'}), 400

    # Check if user exists
    user = get_user_by_email(email)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    # Extract preferences from request
    snow_alerts = data.get('snow_alerts')
    garbage_alerts = data.get('garbage_alerts')
    recycling_alerts = data.get('recycling_alerts')

    # Convert string booleans if needed (from form data)
    if isinstance(snow_alerts, str):
        snow_alerts = snow_alerts.lower() in ('true', '1', 'yes', 'on')
    if isinstance(garbage_alerts, str):
        garbage_alerts = garbage_alerts.lower() in ('true', '1', 'yes', 'on')
    if isinstance(recycling_alerts, str):
        recycling_alerts = recycling_alerts.lower() in ('true', '1', 'yes', 'on')

    # Use existing values if not provided
    if snow_alerts is None:
        snow_alerts = user.snow_alerts_enabled
    if garbage_alerts is None:
        garbage_alerts = user.garbage_alerts_enabled
    if recycling_alerts is None:
        recycling_alerts = user.recycling_alerts_enabled

    # Validate at least one alert type is selected
    if not snow_alerts and not garbage_alerts and not recycling_alerts:
        return jsonify({'error': 'At least one alert type must be enabled'}), 400

    # If waste alerts are newly enabled and user has no waste_zone, fetch schedule
    waste_zone_id = user.waste_zone_id
    waste_schedule = None
    if (garbage_alerts or recycling_alerts) and not waste_zone_id:
        try:
            postal_code = user.postal_code
            waste_schedule = get_schedule(postal_code)
            if waste_schedule:
                waste_zone_id = waste_schedule.get('zone_id')
                logger.info(f"Scraped waste schedule for {postal_code}: zone_id={waste_zone_id}")
        except Exception as e:
            logger.error(f"Error scraping waste schedule: {e}")

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

    # Build response
    response_data = {
        'success': True,
        'message': f'Successfully updated preferences for {email}',
        'preferences': {
            'snow_alerts': snow_alerts,
            'garbage_alerts': garbage_alerts,
            'recycling_alerts': recycling_alerts
        }
    }

    # Include waste schedule info if available
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

    # Validate email
    if not email:
        return jsonify({'error': 'Email is required'}), 400
    if not is_valid_email(email):
        return jsonify({'error': 'Invalid email format'}), 400

    # Check if user exists
    user = get_user_by_email(email)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    # Build waste schedule from waste zone if linked
    waste_schedule = None
    if user.waste_zone_id:
        waste_zone = get_waste_zone_by_id(user.waste_zone_id)
        if waste_zone:
            waste_schedule = {
                'garbage_day': waste_zone.garbage_day,
                'recycling_week': waste_zone.recycling_week
            }

    # Build next events
    next_events = build_next_events(user.postal_code, waste_schedule)

    # Build response
    response_data = {
        'email': user.email,
        'postal_code': user.postal_code,
        'active': user.active,
        'preferences': {
            'snow_alerts': user.snow_alerts_enabled,
            'garbage_alerts': user.garbage_alerts_enabled,
            'recycling_alerts': user.recycling_alerts_enabled
        },
        'next_events': next_events
    }

    # Include waste schedule info if available
    if waste_schedule:
        response_data['waste_schedule'] = waste_schedule

    return jsonify(response_data), 200


@bp.route('/unsubscribe', methods=['POST'])
def unsubscribe():
    """Unsubscribe a user from all alerts and remove their subscription."""
    data = request.get_json() or request.form

    email = data.get('email', '').strip()

    if not email:
        return jsonify({'error': 'Email is required'}), 400
    if not is_valid_email(email):
        return jsonify({'error': 'Invalid email format'}), 400

    removed = remove_user(email)

    if removed:
        return jsonify({
            'success': True,
            'message': f'Successfully unsubscribed {email}'
        }), 200
    else:
        return jsonify({'error': 'Email not found'}), 404


@bp.route('/status/<postal_code>')
def status(postal_code: str):
    """Check current snow removal status for a postal code."""
    if not is_valid_postal_code(postal_code):
        return jsonify({'error': 'Invalid postal code format'}), 400

    has_operation, streets = check_postal_code(postal_code)

    return jsonify({
        'postal_code': postal_code.upper().replace(' ', ''),
        'has_operation': has_operation,
        'streets_affected': streets,
        'message': 'Snow removal in progress - NO PARKING' if has_operation else 'No active snow removal operation'
    }), 200


@bp.route('/schedule/<postal_code>')
def schedule(postal_code: str):
    """Get waste collection schedule for a postal code."""
    if not is_valid_postal_code(postal_code):
        return jsonify({'error': 'Invalid postal code format'}), 400

    # Try to get schedule (from cache or scrape)
    try:
        waste_schedule = get_schedule(postal_code)
    except Exception as e:
        logger.error(f"Error getting schedule for {postal_code}: {e}")
        return jsonify({'error': 'Failed to retrieve schedule'}), 500

    if not waste_schedule:
        return jsonify({'error': 'Could not find schedule for this postal code'}), 404

    # Calculate next collection dates
    garbage_day = waste_schedule.get('garbage_day')
    recycling_week = waste_schedule.get('recycling_week')

    next_garbage = get_next_garbage_date(garbage_day) if garbage_day else None
    next_recycling = get_next_recycling_date(garbage_day, recycling_week) if garbage_day and recycling_week else None

    return jsonify({
        'postal_code': postal_code.upper().replace(' ', ''),
        'garbage_day': garbage_day,
        'recycling_week': recycling_week,
        'next_garbage': next_garbage,
        'next_recycling': next_recycling
    }), 200


@bp.route('/admin/trigger-check', methods=['GET', 'POST'])
def admin_trigger_check():
    """Manually trigger the snow removal check for all users."""
    from app.scheduler import trigger_check_now

    result = trigger_check_now()

    return jsonify({
        'success': True,
        'message': 'Check triggered successfully',
        'result': result
    }), 200


@bp.route('/admin/jobs')
def admin_jobs():
    """View scheduled jobs."""
    from app.scheduler import get_scheduled_jobs

    jobs = get_scheduled_jobs()

    return jsonify({
        'jobs': jobs
    }), 200


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
