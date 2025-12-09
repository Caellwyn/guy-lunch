# Tuesday Lunch Scheduler

A web application for automating weekly lunch coordination for a 25-member business networking group in Longview, WA.

## Overview

This app automates the entire weekly workflow for a recurring Tuesday lunch group:
- **Thursday:** Auto-email next host for location confirmation
- **Friday:** Alert secretary to make reservation
- **Monday:** Send professional announcement to all members
- **Tuesday:** Track attendance and collect ratings

### Key Features

- 🗓️ Automated host rotation based on attendance
- 📧 Scheduled email workflows (host confirmation, announcements, rating requests)
- 📊 Attendance tracking with automatic counter management
- 📍 Location management with Google Places integration
- ⭐ Restaurant rating system with comments
- 👤 Member profiles with business info
- 📱 Progressive Web App (PWA) - installable on iOS/Android with custom splash screens
- ⚾ Baseball-themed "batting order" hosting queue display

## Tech Stack

- **Backend:** Python Flask
- **Database:** PostgreSQL (Railway)
- **Frontend:** Flask templates + Tailwind CSS + Stadium Theme
- **Email:** Brevo (transactional emails)
- **Maps:** Google Places API
- **Hosting:** Railway (auto-deploy from GitHub)

## Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL
- Git

### Local Development

```bash
# Clone the repository
git clone https://github.com/Caellwyn/guy-lunch.git
cd guy-lunch

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your values

# Run database migrations
flask db upgrade

# Start development server
flask run
```

### Environment Variables

```
DATABASE_URL=postgresql://...
BREVO_API_KEY=xkeysib-...
GOOGLE_PLACES_API_KEY=AIza...
ADMIN_PASSWORD=your-admin-password
SECRET_KEY=random-string...
APP_URL=http://localhost:5000
```

## Initial Setup (For New Groups)

After deploying the app, set up your lunch group:

1. **Access the Admin Dashboard**
   - Navigate to `/admin`
   - Log in with your admin password (default: `lunch-admin-2024`)

2. **Go to Setup & Import**
   - Click "Setup & Import" from the dashboard
   - Or go directly to `/admin/setup`

3. **Add Members via CSV Import**
   - Click "Download CSV Template" to get the format
   - Fill in member data in Excel/Google Sheets:
     - `name` - Member's full name (required)
     - `email` - Email address, used as unique identifier (required)
     - `member_type` - `regular`, `guest`, or `inactive`
     - `attendance_since_hosting` - Lunches attended since last hosting
     - `last_hosted_date` - YYYY-MM-DD format
     - `total_hosting_count` - Total times hosted
     - `first_attended` - YYYY-MM-DD format
   - Save as CSV and upload

4. **Verify Setup**
   - Check the Members page shows all imported members
   - Verify the Hosting Queue is ordered correctly based on historical data
   - You're ready to start tracking attendance!

**Re-importing:** You can re-upload CSV anytime to update member data. Existing members (matched by email) will be updated; new emails create new members.

## Project Structure

```
guy-lunch/
├── app/
│   ├── __init__.py
│   ├── models/          # Database models
│   ├── routes/          # API endpoints
│   ├── templates/       # Jinja2 templates
│   ├── static/          # CSS, JS, images
│   └── services/        # Business logic (email, scheduling)
├── migrations/          # Database migrations
├── tests/
├── .env.example
├── requirements.txt
└── README.md
```

## Development Phases

1. ✅ **Phase 0:** Setup & Infrastructure
2. ✅ **Phase 1:** MVP - Core Functionality (attendance, hosting queue, email templates)
3. ✅ **Phase 2:** Email Automation (Brevo integration, host confirmation flow)
4. ✅ **Phase 3:** Location Management & Ratings (Google Places, one-click ratings)
5. ✅ **Phase 4:** Member Portal & Authentication (magic link login, member dashboard)
6. ✅ **Phase 4.5-4.8:** Polish (profiles, secretary portal, PWA enhancements)

## Installing as a PWA

### On iPhone/iPad:
1. Open the app in Safari
2. Tap the Share button (square with arrow)
3. Scroll down and tap "Add to Home Screen"
4. Tap "Add" - the app icon will appear on your home screen

### On Android:
1. Open the app in Chrome
2. Tap the three-dot menu
3. Tap "Add to Home Screen" or "Install app"
4. The app will install with full splash screen support

## License

Private project - All rights reserved

## Author

Josh Caellwyn (The AI Guy) - [theaiguy.rocks](https://theaiguy.rocks)
