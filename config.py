import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

    # Database
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'snow_alert.db')
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{DATABASE_PATH}"

    # Resend
    RESEND_API_KEY = os.getenv('RESEND_API_KEY', '')
    EMAIL_FROM = os.getenv('EMAIL_FROM', 'onboarding@resend.dev')
    EMAIL_ENABLED = os.getenv('EMAIL_ENABLED', 'false').lower() == 'true'

    # Scheduler
    CHECK_HOUR = int(os.getenv('CHECK_HOUR', '16'))  # 4pm by default
    CHECK_MINUTE = int(os.getenv('CHECK_MINUTE', '0'))

    # Snow removal API
    SEARCH_RADIUS_METERS = int(os.getenv('SEARCH_RADIUS_METERS', '200'))
