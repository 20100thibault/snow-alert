"""
Flask Routes for Snow Alert
"""

import re
from flask import Blueprint, request, jsonify, render_template
from app.database import add_user, get_user_by_email, remove_user
from app.snow_checker import geocode_postal_code, check_postal_code
from app.email_service import send_welcome_email

bp = Blueprint('main', __name__)


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
    """Subscribe a user to snow alerts."""
    data = request.get_json() or request.form

    email = data.get('email', '').strip()
    postal_code = data.get('postal_code', '').strip()

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

    # Check for duplicate
    existing = get_user_by_email(email)
    if existing:
        return jsonify({'error': 'Email already subscribed'}), 409

    # Geocode postal code
    location = geocode_postal_code(postal_code)
    if not location:
        return jsonify({'error': 'Could not find postal code. Make sure it is in Quebec City.'}), 400

    # Add user to database
    try:
        user = add_user(
            email=email,
            postal_code=postal_code,
            lat=location['lat'],
            lon=location['lon']
        )
    except Exception as e:
        return jsonify({'error': 'Failed to save subscription'}), 500

    # Send welcome email
    send_welcome_email(email, postal_code)

    return jsonify({
        'success': True,
        'message': f'Successfully subscribed {email} for postal code {postal_code}'
    }), 201


@bp.route('/unsubscribe', methods=['POST'])
def unsubscribe():
    """Unsubscribe a user from snow alerts."""
    data = request.get_json() or request.form

    email = data.get('email', '').strip()

    if not email:
        return jsonify({'error': 'Email is required'}), 400

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


@bp.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({'error': 'Not found'}), 404


@bp.errorhandler(500)
def server_error(error):
    """Handle 500 errors."""
    return jsonify({'error': 'Internal server error'}), 500
