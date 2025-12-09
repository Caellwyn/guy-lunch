import os
from datetime import timedelta
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate, upgrade
from dotenv import load_dotenv

# Load environment variables (override=True ensures .env values take precedence)
load_dotenv(override=True)

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()


def create_app(config_name=None):
    """Application factory pattern."""
    app = Flask(__name__)

    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-me')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///dev.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Session configuration - 30 day persistent sessions
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)
    app.config['SESSION_COOKIE_SECURE'] = os.environ.get('RAILWAY_ENVIRONMENT') is not None  # HTTPS only in production
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

    # Admin password for simple auth (MVP)
    app.config['ADMIN_PASSWORD'] = os.environ.get('ADMIN_PASSWORD', 'lunch-admin-2024')

    # App URL for magic links (defaults to localhost for dev, must be set in production)
    app.config['APP_URL'] = os.environ.get('APP_URL', 'http://localhost:5000')
    
    # Fix for postgres:// vs postgresql:// (some providers use older postgres:// format)
    if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres://'):
        app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace(
            'postgres://', 'postgresql://', 1
        )
    
    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Register blueprints
    from app.routes.main import main_bp
    from app.routes.admin import admin_bp
    from app.routes.api import api_bp
    from app.routes.member import member_bp
    from app.routes.secretary import secretary_bp
    # Gallery disabled per member feedback (December 2024)
    # from app.routes.gallery import gallery_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(member_bp)
    app.register_blueprint(secretary_bp)
    # app.register_blueprint(gallery_bp)
    
    # Import models so they're known to Flask-Migrate
    from app import models
    
    # Auto-run migrations in production (Railway)
    if os.environ.get('RAILWAY_ENVIRONMENT'):
        with app.app_context():
            upgrade()
    
    return app
