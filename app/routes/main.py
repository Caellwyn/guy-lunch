from flask import Blueprint, render_template

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Home page - simple landing for now."""
    return render_template('index.html')


@main_bp.route('/health')
def health():
    """Health check endpoint for Railway."""
    return {'status': 'healthy', 'app': 'Tuesday Lunch Scheduler'}
