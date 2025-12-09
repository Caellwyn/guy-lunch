# Technical Guide - Tuesday Lunch Scheduler

**Purpose:** Architectural blueprint for AI agents to quickly understand project structure, component connections, and key file locations. Updated after each completed step.

---

## Infrastructure

### Hosting (Railway)
- **Project:** Linked to GitHub repo `Caellwyn/guy-lunch` (auto-deploy on push to main)
- **PostgreSQL:** Connected database, ready for schema initialization
- **Web Service:** Deploying to Railway
- **Start Command:** `gunicorn run:app` (via Procfile)

### External Services
| Service | Purpose | Status |
|---------|---------|--------|
| Railway PostgreSQL | Primary database | ✅ Connected |
| Railway Web Service | Flask app hosting | ✅ Deployed |
| Brevo | Transactional email (templates + API) | ✅ Configured |
| Google Places API | Location search/details | ✅ Integrated |
| Cloudflare R2 | Photo storage (S3-compatible) | ✅ Configured |

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
├── app/                    # Flask application
│   ├── __init__.py         # App factory with create_app()
│   ├── models/             # SQLAlchemy models
│   │   ├── __init__.py     # Exports all models
│   │   ├── member.py       # Member model
│   │   ├── location.py     # Location model
│   │   ├── lunch.py        # Lunch model
│   │   ├── attendance.py   # Attendance model
│   │   ├── rating.py       # Rating model
│   │   └── photo.py        # Photo & PhotoTag models
│   ├── routes/             # Route blueprints
│   │   ├── __init__.py
│   │   ├── main.py         # Main routes (/, /health, /confirm)
│   │   ├── admin.py        # Admin/secretary routes
│   │   ├── gallery.py      # Photo gallery routes
│   │   └── api.py          # JSON API endpoints
│   ├── services/           # Business logic (empty, ready for use)
│   ├── templates/          # Jinja2 templates
│   │   ├── base.html       # Base layout with Tailwind
│   │   └── index.html      # Home page
│   └── static/             # CSS, JS, uploads
│
├── migrations/             # Alembic migrations
│   └── versions/           # Migration scripts
├── run.py                  # Application entry point
├── Procfile                # Railway/Heroku start command
├── requirements.txt        # Python dependencies
└── instance/               # SQLite dev database (gitignored)
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
| main | `main.py` | Public routes: home, health, host confirmation, ratings |
| admin | `admin.py` | App admin dashboard, member/location management |
| secretary | `secretary.py` | Secretary portal: attendance, hosting order |
| api | `api.py` | JSON endpoints for Places search, etc. |
| member | `member.py` | Member portal: auth, dashboard, lineup, history |
| gallery | `gallery.py` | Photo gallery (DISABLED): upload, view, tagging, filtering |

**Public Routes (Implemented):**
- `/` - Home page
- `/health` - Health check for Railway
- `/confirm/<token>` - Host confirmation (select restaurant)
- `/rate/<token>/<rating>` - One-click rating (1-5 from email)

**API Routes (Implemented):**
- `/api/places/search?q=<query>` - Search restaurants via Google Places
- `/api/places/<place_id>` - Get full details for a place
- `/api/places/status` - Check if Google Places API is configured

**Member Portal Routes (Implemented):**
- `/member/login` - Magic link login (enter email, receive link)
- `/member/auth/<token>` - Validate magic link and log in
- `/member/logout` - Log out member
- `/member/` - Member dashboard with baseball-themed hosting lineup
- `/member/lineup` - Full batting order with estimated hosting dates
- `/member/history` - Member's lunch attendance history

**Gallery Routes (Implemented):**
- `/member/gallery` - Photo gallery with filtering by location/tagged member
- `/member/gallery/upload` (POST) - Upload photos for a lunch
- `/member/gallery/photo/<id>/delete` (POST) - Delete own photos
- `/member/gallery/lunch/<id>/attendees` - Get attendees for tagging (AJAX)
- `/member/gallery/photo/<id>/details` - Get photo details including tags (AJAX)
- `/member/gallery/photo/<id>/tag` (POST) - Add/remove member tags on photos (AJAX)

**Admin Routes (Implemented):**
- `/admin/login` - Password authentication
- `/admin/` - Admin dashboard
- `/admin/members` - Member management + secretary assignment
- `/admin/members/add` - Add member form
- `/admin/members/<id>/edit` - Edit member
- `/admin/members/set-secretary` - Assign secretary role (POST)
- `/admin/hosting-queue` - View/manage hosting queue
- `/admin/locations` - Location management
- `/admin/locations/add` - Add location (POST)
- `/admin/locations/<id>/edit` - Edit location
- `/admin/locations/<id>/delete` - Delete location (POST)
- `/admin/setup` - Initial setup wizard
- `/admin/setup/import` - CSV import for members + historical data
- `/admin/setup/export-template` - Download CSV template
- `/admin/emails` - Email template hub
- `/admin/emails/preview/<type>` - Preview email templates with sample data
- `/admin/settings` - App settings

**Secretary Routes (Implemented):**
- `/secretary/` - Secretary dashboard (upcoming lunch, reservation info)
- `/secretary/attendance` - Take attendance (simplified checklist)
- `/secretary/hosting-order` - Drag-and-drop hosting queue management
- `/secretary/hosting-order/reorder` - Save new order (AJAX)
- `/secretary/hosting-order/auto-organize` - Reset to default order (AJAX)
- `/secretary/transfer` - Transfer secretary role to another member

### Services Layer
**Location:** `app/services/`

| Service | File | Purpose |
|---------|------|---------|
| email | `email_service.py` | Brevo integration, all email sending |
| scheduler | `scheduler.py` | APScheduler jobs for automated emails |
| places | `places_service.py` | Google Places API integration |
| hosting | `hosting_service.py` | Host rotation logic, queue management |
| storage | `storage_service.py` | Cloudflare R2 photo storage (S3-compatible) |

### Templates
**Location:** `app/templates/`
**Engine:** Jinja2 with Tailwind CSS

```
templates/
├── base.html              # Base layout with nav
├── index.html             # Public home page
├── admin/
│   ├── login.html         # Admin login
│   ├── dashboard.html     # Main secretary view
│   ├── attendance.html    # Check-off interface
│   ├── members.html       # Member list
│   ├── add_member.html    # Add member form
│   ├── edit_member.html   # Edit member form
│   ├── hosting_queue.html # Full hosting queue
│   ├── setup.html         # Initial setup wizard
│   ├── import.html        # CSV import page
│   ├── emails.html        # Email templates hub
│   └── email_preview.html # Individual email preview
├── emails/                # Email templates (Brevo-compatible HTML)
│   ├── base_email.html        # Base email layout (reference only)
│   ├── host_confirmation.html # Thursday: Ask host to pick location
│   ├── secretary_reminder.html # Friday: Reservation reminder or alert
│   ├── announcement.html       # Monday: Group announcement
│   ├── rating_request.html     # Tuesday: Post-lunch rating request
│   └── magic_link.html        # Magic link login email
│   # Note: Templates use Brevo syntax {{ params.VARIABLE_NAME }}
│   # Each template includes documentation of required params at bottom
├── public/
│   ├── confirm_host.html       # Host location confirmation
│   ├── confirmation_success.html
│   ├── already_confirmed.html
│   ├── invalid_token.html
│   └── rating_thanks.html      # Rating submission thank-you
├── member/
    ├── login.html         # Magic link login form
    ├── dashboard.html     # Member dashboard with baseball lineup
    ├── lineup.html        # Full batting order
    ├── history.html       # Attendance history
    └── gallery.html       # Photo gallery with upload, tagging, filtering
```

---

## Key Algorithms

### Host Rotation Queue
**Location:** `app/services/email_jobs.py` (`get_hosting_queue()`)
**Logic:**
1. Track `attendance_since_hosting` for each member (actual attendance count)
2. Increment counter when member attends but doesn't host
3. Reset to 0 when member hosts
4. Optional `queue_position` field for manual secretary override
5. Sorting: `queue_position` first (if set), then `attendance_since_hosting` DESC
6. "Auto-organize" clears all `queue_position` values, reverting to natural order

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
| `DATABASE_URL` | PostgreSQL connection string | Railway dashboard |
| `SECRET_KEY` | Flask session encryption | Generate: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `BREVO_API_KEY` | Email API | Brevo dashboard |
| `GOOGLE_PLACES_API_KEY` | Location search | Google Cloud Console |
| `ADMIN_PASSWORD_HASH` | Admin login | Generate with bcrypt |
| `APP_URL` | Base URL for email links | Railway URL |
| `R2_ACCOUNT_ID` | Cloudflare account ID | Cloudflare dashboard |
| `R2_ACCESS_KEY_ID` | R2 access key | Cloudflare R2 API tokens |
| `R2_SECRET_ACCESS_KEY` | R2 secret key | Cloudflare R2 API tokens |
| `R2_BUCKET_NAME` | R2 bucket name | Cloudflare R2 dashboard |
| `R2_PUBLIC_URL` | Public URL for R2 bucket | Cloudflare R2 settings |

---

## Development Status

### Completed - Phase 0 ✅
- [x] Repository setup with .gitignore, .env.example
- [x] Documentation structure established (4-doc system)
- [x] Railway project linked with PostgreSQL
- [x] Flask app skeleton created (app factory pattern)
- [x] All 7 database models implemented
- [x] Initial migration created and applied locally
- [x] Templates with Tailwind CSS (base.html, index.html)
- [x] Health check endpoint (/health)
- [x] Deployed to Railway (live!)

### Completed - Phase 1 ✅
- [x] Auto-migration on Railway deployment
- [x] Admin authentication (password-based)
- [x] Secretary dashboard with quick actions
- [x] Attendance tracking interface (mobile-first)
- [x] Member management (list, add, edit)
- [x] Hosting queue display and management
- [x] Initial setup wizard (`/admin/setup`)
- [x] CSV import/export for members + historical data
- [x] Guest addition via AJAX on attendance page
- [x] Email templates with preview system

### Completed - Phase 2 (Email Automation) ✅
- [x] Brevo email service integration (`app/services/email_service.py`)
- [x] Email logging to database (EmailLog model)
- [x] 4 email job functions (`app/services/email_jobs.py`):
  - Host confirmation (Thursday 9am)
  - Secretary reminder (Friday 9am)
  - Group announcement (Monday 9am)
  - Rating request (Tuesday 6pm)
- [x] Admin email jobs page with manual triggers (`/admin/emails/jobs`)
- [x] Email logs viewer (`/admin/emails/logs`)
- [x] Host confirmation flow (`/confirm/<token>`)
  - Select from existing locations
  - Add new location with capacity check
  - Mobile-first design
- [x] App settings page (`/admin/settings`)
  - Secretary selection from members list

### Pending - Phase 2: Remaining
- [ ] Railway cron service setup (jobs are manual-only for now)
- [ ] Testing with real emails before enabling automation

### Completed - Phase 3: Location Management & Ratings
- [x] Google Places API integration (`app/services/places_service.py`)
  - Place Autocomplete (search as you type)
  - Place Details (full info for selected place)
  - Location bias for Longview, WA area
- [x] API endpoints for frontend (`app/routes/api.py`)
- [x] Enhanced host confirmation page with autocomplete
  - Search for restaurants by name
  - Auto-populate address, phone, rating, price, cuisine
  - Fallback to manual entry if needed
  - Prevents duplicate locations via google_place_id
- [x] Location management dashboard (`/admin/locations`)
  - Add locations via Google Places search
  - Manual entry fallback
  - Edit/delete existing locations
  - View all location details (rating, price, visits)
- [x] One-click rating system (`/rate/<token>/<rating>`)
  - Clickable star links in email (1-5 stars)
  - Token-based access (unique per member per lunch)
  - Auto-calculates location average rating
  - Prevents duplicate submissions
  - Simple thank-you page confirmation

### In Progress - Phase 4: Member Portal & Authentication
- [x] Magic link authentication system
  - Member enters email → receives login link → clicks → logged in
  - Token stored on Member model (`magic_link_token`, `magic_link_expires`)
  - 15-minute token expiry, single-use
  - 30-day session persistence via Flask cookies
- [x] Member portal dashboard (`/member/`)
  - Baseball-themed hosting lineup (At Bat, On Deck, In the Hole, Dugout)
  - Estimated hosting date prediction
  - Stats: lunches attended, times hosted, queue position
  - Upcoming lunch info
  - Recent attendance history preview
- [x] Full batting order page (`/member/lineup`)
- [x] Lunch attendance history (`/member/history`)
- [x] Photo gallery placeholder (`/member/gallery`)
- [x] Updated navbar with Member Login / My Portal links

### Next Up - Phase 4.2: Member Portal Visual Polish ✅ COMPLETE
- [x] **Make the member portal look WAY cooler!**
  - [x] Added "Stadium Theme" with custom CSS (`stadium-theme.css`)
  - [x] Real textures: Grass background, Brushed Metal, Wood Grain, Paper
  - [x] Custom fonts: `Graduate` (Jersey), `Share Tech Mono` (Scoreboard), `Roboto Condensed`
  - [x] **Dashboard:** 2-column layout with "Player Card" and "Scoreboard"
  - [x] **Lineup:** "Clipboard" style list with wood header
  - [x] **Stats:** "Box Score" paper style with grid layout

### Completed - Phase 4.3: Photo Gallery ✅ COMPLETE
- [x] **Photo Upload (Mobile-First)**
  - [x] Upload photos with lunch selection
  - [x] Tag members who attended (only attendees can be tagged)
  - [x] Photos stored in Cloudflare R2 (S3-compatible)
  - [x] Mobile camera/gallery access via file input
- [x] **Photo Gallery**
  - [x] Grid layout with thumbnails (responsive)
  - [x] Lightbox view for full-size photos
  - [x] Filter by location (stadium)
  - [x] Filter by tagged member
  - [x] Local timezone display for upload times
  - [x] Scroll position preservation on filter changes
- [x] **Member Tagging**
  - [x] Tag members during upload
  - [x] Tag/untag members in lightbox view
  - [x] Only lunch attendees can be tagged
  - [x] View tags on photos in lightbox
- [x] **Photo Management**
  - [x] Delete own photos
  - [x] View photo metadata (uploader, date, location)

### Completed - Phase 4.5: Final Features (December 2024)

**4.5.0: Magic Link Session Bug Fix**
- [x] Fix 30-day session persistence - added `PERMANENT_SESSION_LIFETIME` config

**4.5.1: Dashboard Quick Actions**
- [x] "Post Image" shortcut button (link to gallery upload)
- [x] "Rate Last Lunch" button (only for attended, unrated lunches)
- [x] Restrict photo uploads to attended lunches only

**4.5.2: Rating Comments Enhancement**
- [x] Member rating page with comment field (`/member/rate/<lunch_id>`)
- [x] Show member comments on location detail view (host confirmation modal)

**4.5.3: Host Swap Functionality**
- [x] Swap interface in admin (`/admin/hosting-queue/swap`)
- [x] Exchange `attendance_since_hosting` values between two members
- [x] Mobile-friendly two-step selection

**4.5.4: Member Profile System**
- [x] Profile fields added to Member model (phone, business, website, bio, profile_picture_url, profile_public)
- [x] Profile edit page (`/member/profile/edit`)
- [x] Public profile view (`/member/profile/<id>`) - any member can view, privacy controls contact info
- [x] Admin profile editing (integrated into member edit page)
- [x] Show member's uploaded photos and tagged photos on profile
- [x] Member names link to profiles throughout app (dashboard, lineup)

### DISABLED - Photo Gallery (December 2024)
Photo sharing functionality disabled per member feedback. Code preserved but blueprint unregistered.
- Gallery routes commented out in `app/__init__.py`
- Gallery links removed from member dashboard and profile pages
- Admin photo management still functional at `/admin/photos`
- To re-enable: uncomment gallery_bp import and registration in `app/__init__.py`

### Completed - Phase 4.6: Admin/Secretary Role Separation (December 2024)
- [x] **Separate Secretary Portal** (`/secretary/`)
  - Simplified dashboard with restaurant phone number for reservations
  - Attendance tracking (checkbox list, add guests)
  - Drag-and-drop hosting order management
  - Auto-organize button to reset to default order
  - Transfer secretary role to another member (with confirmation)
- [x] **Hosting Queue Improvements**
  - Added `queue_position` field for manual ordering
  - `attendance_since_hosting` preserved as actual count (never modified by dragging)
  - Central `get_hosting_queue()` function used everywhere
  - Auto-organize clears manual overrides
- [x] **Role-Based Navigation**
  - Nav shows links based on session flags (member, secretary, admin)
  - Secretary sees yellow "Secretary" link when logged in
  - Admin link only shown when admin authenticated
- [x] **Secretary Assignment**
  - Moved from Settings to Members page
  - Secretary can transfer role to another member
  - Confirmation required to prevent accidental transfers
- [x] **Bug Fixes**
  - Fixed restaurant selection visual feedback on host confirmation page
  - Fixed dev-login preserving admin authentication

### Next Up - Phase 4.7 (Optional)
- [ ] PWA Features (service worker, manifest, offline capability)
- [ ] Railway cron service setup for automated emails

---

## Local Development Commands

```bash
# Activate virtual environment
source venv/Scripts/activate  # Windows Git Bash
# or: venv\Scripts\activate   # Windows CMD

# Run development server
flask --app run:app run --port 5000

# Database migrations
flask --app run:app db migrate -m "Description"
flask --app run:app db upgrade
flask --app run:app db downgrade
```

---

*Last Updated: December 2024 - Phase 4.6 Complete (Admin/Secretary Role Separation)*
