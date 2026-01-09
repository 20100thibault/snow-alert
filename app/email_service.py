"""
Email Service Module
Sends email alerts using Resend API.
"""

import resend
from typing import List
from config import Config

# Initialize Resend
resend.api_key = Config.RESEND_API_KEY


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
