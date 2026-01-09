"""
Snow Alert Flask Application
"""

from flask import Flask
from config import Config
from app.database import init_db


def create_app(start_scheduler=True):
    """Create and configure the Flask application."""
    app = Flask(__name__, template_folder='../templates')

    # Load config
    app.config.from_object(Config)

    # Initialize database
    init_db()

    # Register routes
    from app.routes import bp
    app.register_blueprint(bp)

    # Start scheduler (unless disabled, e.g. for testing)
    if start_scheduler:
        from app.scheduler import init_scheduler
        init_scheduler(app)

    return app
