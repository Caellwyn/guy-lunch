# Technical Guide - Tuesday Lunch Scheduler

**Purpose:** Architectural blueprint for AI agents to quickly understand project structure, component connections, and key file locations. Updated after each completed step.

---

## Infrastructure

### Hosting (Render)
- **Project:** Linked to GitHub repo `Caellwyn/guy-lunch` (auto-deploy on push to main)
- **PostgreSQL:** Connected database, ready for schema initialization
- **Web Service:** To be deployed

### External Services
| Service | Purpose | Status |
|---------|---------|--------|
| Render PostgreSQL | Primary database | ✅ Connected |
| Render Web Service | Flask app hosting | ⏳ Pending |
| SendGrid | Transactional email | ⏳ Not configured |
| Google Places API | Location search/details | ⏳ Not configured |

---

## Project Structure

```
guy-lunch/
├── .claude                 # AI instructions (this project's rules)
├── .env.example            # Environment variable template
├── .gitignore
├── README.md               # Human-focused documentation
├── technical_guide.md      # THIS FILE - architectural blueprint
├── Tuesday_Lunch_Scheduler_Project_Plan.md  # Requirements & progress
├── _archive/               # Archived files (don't delete, move here)
│
├── app/                    # [TO BE CREATED] Flask application
│   ├── __init__.py         # App factory
│   ├── models/             # SQLAlchemy models
│   ├── routes/             # Route blueprints
│   ├── services/           # Business logic
│   ├── templates/          # Jinja2 templates
│   └── static/             # CSS, JS, uploads
│
├── migrations/             # [TO BE CREATED] Alembic migrations
├── tests/                  # [TO BE CREATED] pytest tests
└── requirements.txt        # [TO BE CREATED] Python dependencies
```

---

## Components

### Database Layer
**Location:** `app/models/`
**ORM:** SQLAlchemy with Flask-SQLAlchemy

| Model | File | Purpose |
|-------|------|---------|
| Member | `member.py` | Lunch group members, hosting stats |
| Location | `location.py` | Restaurants with Google Places data |
| Lunch | `lunch.py` | Weekly lunch events |
| Attendance | `attendance.py` | Who attended each lunch |
| Rating | `rating.py` | Member ratings for locations |
| Photo | `photo.py` | Uploaded photos |
| PhotoTag | `photo.py` | Member tags in photos |

**Key Relationships:**
- Lunch → Location (many-to-one)
- Lunch → Member as host (many-to-one)
- Attendance → Lunch + Member (junction table)
- Rating → Lunch + Member (junction table)
- PhotoTag → Photo + Member (junction table)

### Routes Layer
**Location:** `app/routes/`

| Blueprint | File | Purpose |
|-----------|------|---------|
| admin | `admin.py` | Secretary dashboard, attendance tracking |
| public | `public.py` | Host confirmation, rating submission |
| member | `member.py` | Member portal, photo gallery |
| api | `api.py` | JSON endpoints (if needed) |

### Services Layer
**Location:** `app/services/`

| Service | File | Purpose |
|---------|------|---------|
| email | `email_service.py` | SendGrid integration, all email sending |
| scheduler | `scheduler.py` | APScheduler jobs for automated emails |
| places | `places_service.py` | Google Places API integration |
| hosting | `hosting_service.py` | Host rotation logic, queue management |
| photos | `photo_service.py` | Upload, compression, thumbnail generation |

### Templates
**Location:** `app/templates/`
**Engine:** Jinja2 with Tailwind CSS

```
templates/
├── base.html              # Base layout with nav
├── admin/
│   ├── dashboard.html     # Main secretary view
│   ├── attendance.html    # Check-off interface
│   └── members.html       # Member management
├── public/
│   ├── confirm.html       # Host location confirmation
│   └── rate.html          # Rating submission
├── member/
│   ├── portal.html        # Member dashboard
│   └── gallery.html       # Photo gallery
└── emails/
    ├── host_confirmation.html
    ├── secretary_reminder.html
    ├── announcement.html
    └── rating_request.html
```

---

## Key Algorithms

### Host Rotation Queue
**Location:** `app/services/hosting_service.py`
**Logic:** 
1. Track `attendance_since_hosting` for each member
2. Increment counter when member attends but doesn't host
3. Reset to 0 when member hosts
4. Next host = member with highest counter (ties broken alphabetically)

### Automated Email Schedule
**Location:** `app/services/scheduler.py`
| Day | Time | Job | Function |
|-----|------|-----|----------|
| Thursday | 9am | Host confirmation request | `send_host_confirmation()` |
| Friday | 9am | Secretary reminder | `send_secretary_reminder()` |
| Monday | 9am | Group announcement | `send_announcement()` |
| Tuesday | 6pm | Rating requests | `send_rating_requests()` |

---

## Environment Variables

| Variable | Purpose | Source |
|----------|---------|--------|
| `DATABASE_URL` | PostgreSQL connection string | Render dashboard |
| `SECRET_KEY` | Flask session encryption | Generate: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `SENDGRID_API_KEY` | Email API | SendGrid dashboard |
| `GOOGLE_PLACES_API_KEY` | Location search | Google Cloud Console |
| `ADMIN_PASSWORD_HASH` | Admin login | Generate with bcrypt |
| `APP_URL` | Base URL for email links | Render URL |

---

## Development Status

### Completed
- [x] Repository setup with .gitignore, .env.example
- [x] Documentation structure established
- [x] Render project linked with PostgreSQL

### In Progress
- [ ] Flask app skeleton

### Next Steps
1. Create Flask app structure
2. Set up database models and migrations
3. Deploy "Hello World" to Render

---

*Last Updated: December 5, 2025*
