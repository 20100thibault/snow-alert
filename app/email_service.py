"""
Email Service Module
Sends email alerts using Resend API.
"""

import logging
import resend
from typing import List
from datetime import date
from config import Config

logger = logging.getLogger(__name__)

# Initialize Resend
resend.api_key = Config.RESEND_API_KEY


# Shared email styles matching website design
EMAIL_STYLES = """
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Helvetica Neue', Helvetica, Arial, sans-serif;
            background-color: #fbfbfd;
            margin: 0;
            padding: 0;
            -webkit-font-smoothing: antialiased;
        }
    </style>
"""

EMAIL_WRAPPER_START = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    {styles}
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Helvetica Neue', Helvetica, Arial, sans-serif; background-color: #fbfbfd; margin: 0; padding: 20px;">
    <div style="max-width: 480px; margin: 0 auto;">
"""

EMAIL_WRAPPER_END = """
    </div>
</body>
</html>
"""

EMAIL_FOOTER = """
        <div style="text-align: center; padding: 24px 0; color: #86868b; font-size: 13px;">
            <p style="margin: 0 0 8px 0;">Quebec City Alerts</p>
            <a href="{unsubscribe_url}" style="color: #0071e3; text-decoration: none;">Unsubscribe from alerts</a>
        </div>
"""


def send_alert_email(to_email: str, postal_code: str, streets: List[str]) -> bool:
    """
    Send a snow removal alert email.

    Args:
        to_email: Recipient email address
        postal_code: The postal code being monitored
        streets: List of affected street names

    Returns:
        True if email sent successfully, False otherwise
    """
    if not Config.EMAIL_ENABLED:
        print(f"[EMAIL DISABLED] Would send alert to {to_email}")
        return True

    streets_html = "".join([f"<li>{street}</li>" for street in streets])

    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #d32f2f;">⚠️ Snow Removal Alert</h2>
        <p>A snow removal operation is in progress near your location:</p>
        <p><strong>Postal Code:</strong> {postal_code}</p>
        <h3>Affected Streets:</h3>
        <ul>
            {streets_html}
        </ul>
        <p style="background-color: #ffebee; padding: 15px; border-radius: 5px;">
            <strong>🚗 Parking is PROHIBITED on these streets.</strong><br>
            Please move your vehicle to avoid a ticket or towing.
        </p>
        <hr>
        <p style="color: #666; font-size: 12px;">
            Snow Alert - Quebec City<br>
            <a href="{{unsubscribe_url}}">Unsubscribe</a>
        </p>
    </body>
    </html>
    """

    try:
        params = {
            "from": Config.EMAIL_FROM,
            "to": [to_email],
            "subject": f"⚠️ Snow Removal Alert - {postal_code}",
            "html": html_content
        }

        response = resend.Emails.send(params)
        print(f"[EMAIL SENT] Alert to {to_email} - ID: {response.get('id', 'unknown')}")
        return True

    except Exception as e:
        print(f"[EMAIL ERROR] Failed to send to {to_email}: {e}")
        return False


def send_welcome_email(to_email: str, postal_code: str) -> bool:
    """
    Send a welcome/confirmation email when user subscribes.

    Args:
        to_email: Recipient email address
        postal_code: The postal code they subscribed to monitor

    Returns:
        True if email sent successfully, False otherwise
    """
    if not Config.EMAIL_ENABLED:
        print(f"[EMAIL DISABLED] Would send welcome to {to_email}")
        return True

    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #1976d2;">✅ Subscription Confirmed</h2>
        <p>You are now subscribed to snow removal alerts!</p>
        <p><strong>Postal Code:</strong> {postal_code}</p>
        <p>You will receive an email alert at 4:00 PM whenever a snow removal
        operation is scheduled in your area.</p>
        <h3>What to expect:</h3>
        <ul>
            <li>Daily check at 4:00 PM</li>
            <li>Email only when there's an active operation</li>
            <li>List of affected streets near you</li>
        </ul>
        <hr>
        <p style="color: #666; font-size: 12px;">
            Snow Alert - Quebec City<br>
            <a href="{{unsubscribe_url}}">Unsubscribe</a>
        </p>
    </body>
    </html>
    """

    try:
        params = {
            "from": Config.EMAIL_FROM,
            "to": [to_email],
            "subject": f"✅ Snow Alert Subscription Confirmed - {postal_code}",
            "html": html_content
        }

        response = resend.Emails.send(params)
        print(f"[EMAIL SENT] Welcome to {to_email} - ID: {response.get('id', 'unknown')}")
        return True

    except Exception as e:
        print(f"[EMAIL ERROR] Failed to send to {to_email}: {e}")
        return False


def _build_garbage_email_html(postal_code: str, collection_date: date) -> str:
    """
    Build HTML content for garbage reminder email.
    Design matches the website's Apple-style aesthetic.
    """
    formatted_date = collection_date.strftime("%A, %B %d, %Y")

    return EMAIL_WRAPPER_START.format(styles=EMAIL_STYLES) + f"""
        <!-- Header with gradient background -->
        <div style="background: linear-gradient(180deg, #e8f4e8 0%, #fbfbfd 100%); padding: 40px 24px 30px; text-align: center; border-radius: 20px 20px 0 0;">
            <!-- Icon container -->
            <div style="width: 80px; height: 80px; margin: 0 auto 20px; background: linear-gradient(145deg, #ffffff 0%, #f0fff0 100%); border-radius: 22px; display: inline-flex; align-items: center; justify-content: center; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);">
                <span style="font-size: 40px;">🗑️</span>
            </div>
            <h1 style="font-size: 28px; font-weight: 600; color: #1d1d1f; margin: 0 0 8px 0; letter-spacing: -0.02em;">Garbage Pickup Tomorrow</h1>
            <p style="font-size: 17px; color: #86868b; margin: 0;">{postal_code}</p>
        </div>

        <!-- Main card -->
        <div style="background: #ffffff; border-radius: 0 0 20px 20px; padding: 32px; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08); border: 1px solid rgba(0, 0, 0, 0.08); border-top: none;">
            <!-- Date highlight -->
            <div style="background: rgba(52, 199, 89, 0.1); border-radius: 12px; padding: 20px; text-align: center; margin-bottom: 24px;">
                <p style="font-size: 13px; font-weight: 600; color: #34c759; text-transform: uppercase; letter-spacing: 0.02em; margin: 0 0 4px 0;">Collection Date</p>
                <p style="font-size: 21px; font-weight: 600; color: #248a3d; margin: 0;">{formatted_date}</p>
            </div>

            <!-- Reminder content -->
            <div style="border-top: 1px solid rgba(0, 0, 0, 0.08); padding-top: 24px;">
                <h3 style="font-size: 15px; font-weight: 600; color: #1d1d1f; margin: 0 0 16px 0; display: flex; align-items: center;">
                    <span style="margin-right: 8px;">📋</span> Reminder
                </h3>
                <ul style="list-style: none; padding: 0; margin: 0;">
                    <li style="display: flex; align-items: flex-start; font-size: 15px; color: #86868b; line-height: 1.5; padding: 8px 0;">
                        <span style="color: #34c759; margin-right: 12px; flex-shrink: 0;">✓</span>
                        Place your garbage bins at the curb by 7:00 AM
                    </li>
                    <li style="display: flex; align-items: flex-start; font-size: 15px; color: #86868b; line-height: 1.5; padding: 8px 0;">
                        <span style="color: #34c759; margin-right: 12px; flex-shrink: 0;">✓</span>
                        Ensure bags are properly sealed
                    </li>
                    <li style="display: flex; align-items: flex-start; font-size: 15px; color: #86868b; line-height: 1.5; padding: 8px 0;">
                        <span style="color: #34c759; margin-right: 12px; flex-shrink: 0;">✓</span>
                        Bins should be accessible from the street
                    </li>
                </ul>
            </div>
        </div>
""" + EMAIL_FOOTER.format(unsubscribe_url="{{unsubscribe_url}}") + EMAIL_WRAPPER_END


def _build_recycling_email_html(postal_code: str, collection_date: date) -> str:
    """
    Build HTML content for recycling reminder email.
    Design matches the website's Apple-style aesthetic.
    """
    formatted_date = collection_date.strftime("%A, %B %d, %Y")

    return EMAIL_WRAPPER_START.format(styles=EMAIL_STYLES) + f"""
        <!-- Header with gradient background -->
        <div style="background: linear-gradient(180deg, #e8f4fd 0%, #fbfbfd 100%); padding: 40px 24px 30px; text-align: center; border-radius: 20px 20px 0 0;">
            <!-- Icon container -->
            <div style="width: 80px; height: 80px; margin: 0 auto 20px; background: linear-gradient(145deg, #ffffff 0%, #f0f5ff 100%); border-radius: 22px; display: inline-flex; align-items: center; justify-content: center; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);">
                <span style="font-size: 40px;">♻️</span>
            </div>
            <h1 style="font-size: 28px; font-weight: 600; color: #1d1d1f; margin: 0 0 8px 0; letter-spacing: -0.02em;">Recycling Pickup Tomorrow</h1>
            <p style="font-size: 17px; color: #86868b; margin: 0;">{postal_code}</p>
        </div>

        <!-- Main card -->
        <div style="background: #ffffff; border-radius: 0 0 20px 20px; padding: 32px; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08); border: 1px solid rgba(0, 0, 0, 0.08); border-top: none;">
            <!-- Date highlight -->
            <div style="background: rgba(0, 113, 227, 0.1); border-radius: 12px; padding: 20px; text-align: center; margin-bottom: 24px;">
                <p style="font-size: 13px; font-weight: 600; color: #0071e3; text-transform: uppercase; letter-spacing: 0.02em; margin: 0 0 4px 0;">Collection Date</p>
                <p style="font-size: 21px; font-weight: 600; color: #0058b0; margin: 0;">{formatted_date}</p>
            </div>

            <!-- Reminder content -->
            <div style="border-top: 1px solid rgba(0, 0, 0, 0.08); padding-top: 24px;">
                <h3 style="font-size: 15px; font-weight: 600; color: #1d1d1f; margin: 0 0 16px 0; display: flex; align-items: center;">
                    <span style="margin-right: 8px;">📋</span> Reminder
                </h3>
                <ul style="list-style: none; padding: 0; margin: 0;">
                    <li style="display: flex; align-items: flex-start; font-size: 15px; color: #86868b; line-height: 1.5; padding: 8px 0;">
                        <span style="color: #0071e3; margin-right: 12px; flex-shrink: 0;">✓</span>
                        Place your recycling bin at the curb by 7:00 AM
                    </li>
                    <li style="display: flex; align-items: flex-start; font-size: 15px; color: #86868b; line-height: 1.5; padding: 8px 0;">
                        <span style="color: #0071e3; margin-right: 12px; flex-shrink: 0;">✓</span>
                        Rinse containers and flatten cardboard
                    </li>
                    <li style="display: flex; align-items: flex-start; font-size: 15px; color: #86868b; line-height: 1.5; padding: 8px 0;">
                        <span style="color: #0071e3; margin-right: 12px; flex-shrink: 0;">✓</span>
                        No plastic bags in recycling bin
                    </li>
                </ul>
            </div>
        </div>
""" + EMAIL_FOOTER.format(unsubscribe_url="{{unsubscribe_url}}") + EMAIL_WRAPPER_END


def send_garbage_reminder(to_email: str, postal_code: str, collection_date: date) -> bool:
    """
    Send a garbage collection reminder email.

    Args:
        to_email: Recipient email address
        postal_code: The postal code being monitored
        collection_date: The date of garbage collection

    Returns:
        True if email sent successfully, False otherwise
    """
    if not Config.EMAIL_ENABLED:
        logger.info(f"[EMAIL DISABLED] Would send garbage reminder to {to_email}")
        return True

    html_content = _build_garbage_email_html(postal_code, collection_date)
    formatted_date = collection_date.strftime("%B %d")

    try:
        params = {
            "from": Config.EMAIL_FROM,
            "to": [to_email],
            "subject": f"🗑️ Garbage pickup tomorrow - {formatted_date}",
            "html": html_content
        }

        response = resend.Emails.send(params)
        logger.info(f"[EMAIL SENT] Garbage reminder to {to_email} - ID: {response.get('id', 'unknown')}")
        return True

    except Exception as e:
        logger.error(f"[EMAIL ERROR] Failed to send garbage reminder to {to_email}: {e}")
        return False


def send_recycling_reminder(to_email: str, postal_code: str, collection_date: date) -> bool:
    """
    Send a recycling collection reminder email.

    Args:
        to_email: Recipient email address
        postal_code: The postal code being monitored
        collection_date: The date of recycling collection

    Returns:
        True if email sent successfully, False otherwise
    """
    if not Config.EMAIL_ENABLED:
        logger.info(f"[EMAIL DISABLED] Would send recycling reminder to {to_email}")
        return True

    html_content = _build_recycling_email_html(postal_code, collection_date)
    formatted_date = collection_date.strftime("%B %d")

    try:
        params = {
            "from": Config.EMAIL_FROM,
            "to": [to_email],
            "subject": f"♻️ Recycling pickup tomorrow - {formatted_date}",
            "html": html_content
        }

        response = resend.Emails.send(params)
        logger.info(f"[EMAIL SENT] Recycling reminder to {to_email} - ID: {response.get('id', 'unknown')}")
        return True

    except Exception as e:
        logger.error(f"[EMAIL ERROR] Failed to send recycling reminder to {to_email}: {e}")
        return False
