import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate, upgrade
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

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
    
    # Admin password for simple auth (MVP)
    app.config['ADMIN_PASSWORD'] = os.environ.get('ADMIN_PASSWORD', 'lunch-admin-2024')
    
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
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)
    
    # Import models so they're known to Flask-Migrate
    from app import models
    
    # Auto-run migrations in production (Railway)
    if os.environ.get('RAILWAY_ENVIRONMENT'):
        with app.app_context():
            upgrade()
    
    return app
