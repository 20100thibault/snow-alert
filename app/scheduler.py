"""
Scheduler Module
Runs daily checks for snow removal operations and sends alerts.
"""

import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from config import Config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = None


def check_all_users():
    """
    Check snow removal status for all active users and send alerts if needed.
    This is the main scheduled job that runs daily.
    """
    from app.database import get_all_active_users
    from app.snow_checker import check_postal_code
    from app.email_service import send_alert_email

    logger.info("=" * 50)
    logger.info(f"Starting scheduled check at {datetime.now()}")
    logger.info("=" * 50)

    users = get_all_active_users()
    logger.info(f"Found {len(users)} active users to check")

    alerts_sent = 0
    errors = 0

    for user in users:
        try:
            logger.info(f"Checking {user.email} ({user.postal_code})...")

            has_operation, streets = check_postal_code(user.postal_code)

            if has_operation:
                logger.info(f"  -> OPERATION DETECTED! Streets: {streets}")
                success = send_alert_email(user.email, user.postal_code, streets)
                if success:
                    alerts_sent += 1
                    logger.info(f"  -> Alert sent to {user.email}")
                else:
                    errors += 1
                    logger.error(f"  -> Failed to send alert to {user.email}")
            else:
                logger.info(f"  -> No operation")

        except Exception as e:
            errors += 1
            logger.error(f"  -> Error checking {user.email}: {e}")

    logger.info("=" * 50)
    logger.info(f"Check complete: {alerts_sent} alerts sent, {errors} errors")
    logger.info("=" * 50)

    return {
        "users_checked": len(users),
        "alerts_sent": alerts_sent,
        "errors": errors
    }


def init_scheduler(app=None):
    """Initialize and start the background scheduler."""
    global scheduler

    if scheduler is not None:
        logger.info("Scheduler already initialized")
        return scheduler

    scheduler = BackgroundScheduler()

    # Schedule daily check at configured time (default 4pm)
    trigger = CronTrigger(
        hour=Config.CHECK_HOUR,
        minute=Config.CHECK_MINUTE
    )

    scheduler.add_job(
        check_all_users,
        trigger=trigger,
        id='daily_snow_check',
        name='Daily Snow Removal Check',
        replace_existing=True
    )

    scheduler.start()
    logger.info(f"Scheduler started - Daily check at {Config.CHECK_HOUR:02d}:{Config.CHECK_MINUTE:02d}")

    return scheduler


def get_scheduler():
    """Get the scheduler instance."""
    global scheduler
    return scheduler


def get_scheduled_jobs():
    """Get list of scheduled jobs."""
    global scheduler
    if scheduler is None:
        return []

    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": str(job.next_run_time) if job.next_run_time else None
        })
    return jobs


def trigger_check_now():
    """Manually trigger the check (for testing)."""
    logger.info("Manual trigger requested")
    return check_all_users()
