# Tuesday Lunch Scheduler - Project Plan

## Executive Summary

**Project Name:** Tuesday Lunch Scheduler  
**Developer:** Josh Caellwyn (The AI Guy)  
**Target Users:** 25-member business networking lunch group in Longview, WA  
**Primary Goal:** Automate weekly lunch coordination, attendance tracking, and host rotation  
**Secondary Goal:** Demonstrate technical capabilities to network of successful business owners  

**Key Value Propositions:**
- Eliminates manual email coordination
- Automates host rotation based on attendance
- Tracks location ratings and preferences
- Provides analytics on group behavior
- Professional, polished interface that showcases technical competency

---

## How to Use This Plan

**This plan is designed to be followed linearly by an AI coding assistant or human developer.**

### For AI Coding Assistants:
- Follow phases in numerical order (Phase 0 → Phase 1 → Phase 2 → etc.)
- Complete all tasks in a phase before moving to the next
- Use the testable milestones to verify each step is complete
- Refer to dependencies section if unsure about order
- Code examples are in the Appendix (use as reference, not prescriptive)

### For Human Developers:
- Read the entire plan first to understand the big picture
- Check the Pre-Flight Checklist before starting
- Work through phases sequentially on weekends
- Test each feature on mobile as you build (don't wait)
- Review "Common Pitfalls to Avoid" before starting each phase
- Adjust timeline based on your pace (estimates are averages)

### Key Principles:
1. **Mobile-first:** Design for phone, enhance for desktop
2. **Test as you go:** Don't batch testing at the end
3. **Simple first:** Build minimum viable feature, refine later
4. **Real data:** Use actual member names/restaurants from the start
5. **Feedback early:** Show secretary the dashboard in Phase 1

### Progress Tracking:
- Mark checkboxes [ ] as you complete tasks
- Update milestones ✓ when verified
- Track time spent vs. estimates
- Note deviations or issues in project log (create one)

### When Stuck:
- Check "Common Pitfalls" section
- Review dependencies (maybe you're missing a prerequisite)
- Simplify the approach (aim for MVP, not perfection)
- Test on real devices if it's a mobile issue

---

## Project Overview

### Problem Statement
A weekly business lunch group of ~25 members currently manages coordination through manual emails. Host rotation is tracked informally, attendance is not systematically recorded, and there's no historical data on locations or preferences. The secretary role involves significant manual effort each week.

### Solution
A custom web application that automates the entire weekly workflow:
- **Thursday:** Auto-email next host for location confirmation
- **Friday:** Alert secretary to make reservation
- **Monday:** Send professional announcement to all members
- **Tuesday:** Track attendance and collect ratings

### Success Metrics
- Zero manual emails after automation is live
- 100% host confirmation rate (with backup system)
- Secretary time reduced from ~30 min/week to ~5 min/week
- Positive feedback from lunch group members
- At least 2 consulting leads generated from visibility

---

## Technical Architecture

### Technology Stack

**Backend:**
- **Framework:** Python Flask or Node.js/Express
- **Database:** PostgreSQL (for analytics) or SQLite (for simplicity)
- **Hosting:** Railway, Render, or Heroku
- **Image Storage:** Local filesystem (MVP) → AWS S3/Cloudflare R2 (production)

**Frontend (MOBILE-FIRST):**
- **Framework:** Minimal - Flask templates with Tailwind CSS
- **CSS:** Tailwind CSS (mobile-first responsive utilities)
- **Interactive elements:** HTMX for dynamic updates (optional)
- **Maps/Charts:** Folium (maps), Plotly (charts)
- **PWA:** Service worker, manifest.json, offline capability
- **Image handling:** Client-side compression before upload

**External Services:**
- **Email:** Brevo (free tier: 300 emails/day)
- **Maps:** Google Places API + Google Maps Static API
- **Scheduling:** APScheduler or cron jobs
- **Image optimization:** PIL/Pillow for thumbnails

**Development:**
- **Version Control:** Git + GitHub
- **Environment:** Python 3.11+ or Node 18+
- **Testing:** pytest or jest + real device testing (iOS/Android)
- **Mobile testing:** Chrome DevTools + physical devices

### Data Model

**Members Table:**
- id (PK)
- name
- email
- member_type ('regular', 'guest', 'inactive')
- attendance_since_hosting (integer)
- last_hosted_date (timestamp)
- total_hosting_count (integer)
- first_attended (date)
- created_at, updated_at

**Locations Table:**
- id (PK)
- name
- address
- phone
- google_place_id
- google_rating (decimal)
- price_level (1-4)
- cuisine_type
- group_friendly (boolean)
- last_visited (date)
- visit_count (integer)
- avg_group_rating (decimal)
- created_at, updated_at

**Lunches Table:**
- id (PK)
- date (date)
- location_id (FK)
- host_id (FK to members)
- expected_attendance (integer)
- actual_attendance (integer)
- reservation_confirmed (boolean)
- status ('planned', 'completed', 'cancelled')
- created_at, updated_at

**Attendance Table:**
- id (PK)
- lunch_id (FK)
- member_id (FK)
- was_host (boolean)
- created_at

**Ratings Table:**
- id (PK)
- lunch_id (FK)
- member_id (FK)
- rating (1-5)
- comment (text, optional)
- created_at

**Photos Table:**
- id (PK)
- lunch_id (FK)
- uploaded_by (member_id FK)
- file_url (varchar)
- thumbnail_url (varchar)
- caption (text, optional)
- created_at, updated_at

**Photo_Tags Table:**
- id (PK)
- photo_id (FK)
- member_id (FK)
- created_at

---

## Project Phases

### Phase 0: Setup & Infrastructure (2-3 hours)
**Goal:** Development environment ready, basic app skeleton deployed

### Phase 1: MVP - Core Functionality (Weekend 1: 8-12 hours)
**Goal:** Functional attendance tracking and hosting queue with manual email capability

### Phase 2: Automation & Email (Weekend 2: 6-8 hours)
**Goal:** Automated weekly email workflow

### Phase 3: Location Management & Ratings (Weekend 3: 6-8 hours)
**Goal:** Google Places integration and rating system

### Phase 4: Analytics, Auth & Polish (Weekend 4: 8 hours)
**Goal:** Member authentication, data visualizations, UI improvements

### Phase 5: Photo Gallery (Weekend 5: 8 hours)
**Goal:** Photo upload, gallery, member portal

### Phase 6: Production & Handoff (Week 6: 4 hours)
**Goal:** Live deployment, secretary training, monitoring setup

---

## Phase Dependencies & Critical Path

**Understanding dependencies helps ensure you build in the right order:**

```
Phase 0 (Setup)
    ↓
Phase 1 (Database & Core UI)
    ↓
Phase 2 (Email Automation) ← Requires Phase 1 (member data, lunch records)
    ↓
Phase 3 (Locations & Ratings) ← Requires Phase 2 (emails for rating requests)
    ↓
Phase 4.0 (Authentication) ← Standalone, but needed before 4.3
    ↓
Phase 4.1-4.2 (Analytics & Polish) ← Can be done in parallel with 4.0
    ↓
Phase 4.3 (Photo Gallery) ← REQUIRES Phase 4.0 (authentication)
    ↓
Phase 5 (Testing & Deploy) ← Requires everything above
```

**Critical Path (must be done in order):**
1. Phase 0 → Phase 1 → Phase 2 (Core system must work first)
2. Phase 4.0 → Phase 4.3 (Auth required before photos)

**Can be done in parallel or flexible order:**
- Phase 4.1 (Analytics) can be done anytime after Phase 1
- Phase 4.2 (UI Polish) can be done anytime
- Phase 3 (Locations/Ratings) and Phase 4.0 (Auth) could swap order

---

## Pre-Flight Checklist

**Before starting Phase 0, ensure you have:**

- [ ] **Real data collected:**
  - List of 25 member names and email addresses
  - List of 5-10 known restaurant locations (name, address, phone)
  - Historical data: dates of last 3-4 lunches, who hosted, where, who attended
  - Current hosting rotation (who's next in line)

- [ ] **Accounts created:**
  - GitHub account (for code repository)
  - Railway/Render/Heroku account (for hosting - can do during Phase 0)
  - Brevo account (for emails - can do during Phase 0)
  - Google Cloud account (for Places API - can wait until Phase 3)

- [ ] **Tools installed:**
  - Python 3.11+ or Node.js 18+ (check: `python --version` or `node --version`)
  - Git (check: `git --version`)
  - PostgreSQL client (optional, can use hosting platform's database)
  - Code editor (VS Code, PyCharm, etc.)

- [ ] **Time commitment:**
  - 5 weekends available (can be non-consecutive)
  - Each weekend: 6-10 hours of focused development time
  - Total project time: 40-50 hours spread over 5-6 weeks

- [ ] **Communication:**
  - Secretary identified and willing to participate in testing
  - Lunch group aware you're building this (optional but recommended)
  - Permission to send test emails to a few members

**If any of these are not ready, complete them before starting Phase 0.**

---

## Detailed Phase Breakdown

## Phase 0: Setup & Infrastructure

### Setup Tasks
- [ ] **Create GitHub repository**
  - Initialize with .gitignore (Python/Node)
  - Add README with project description
  - Set up main/dev branch structure

- [ ] **Set up local development environment**
  - Install Python 3.11+ or Node 18+
  - Create virtual environment
  - Initialize project structure
  - Create .env file template
  - Document required environment variables

- [ ] **Configure environment variables**
  - DATABASE_URL (will set up next)
  - SECRET_KEY (generate random string)
  - ADMIN_PASSWORD_HASH (generate bcrypt hash)
  - APP_URL (localhost for now)
  - BREVO_API_KEY (will get in later step)
  - GOOGLE_PLACES_API_KEY (will get in Phase 3)

- [ ] **Choose and configure database**
  - Decision: PostgreSQL (production-ready) vs SQLite (simple)
  - Set up local database
  - Create database schema migration system (Alembic/Flask-Migrate)
  - Test database connection

- [ ] **Deploy basic "Hello World" app**
  - Create Railway/Render/Heroku account
  - Deploy skeleton app
  - Set up environment variables in hosting platform
  - Verify deployment works
  - Set up continuous deployment from GitHub

- [ ] **Set up Brevo account**
  - Create account (free tier)
  - Verify sender email (use your domain or personal email)
  - Get API key
  - Add API key to .env
  - Test sending one email

### Testable Milestones
- ✓ App accessible at live URL (shows "Hello World")
- ✓ Database connection works (can execute simple query)
- ✓ Can send test email via Brevo (check inbox)
- ✓ Environment variables properly configured locally and in production
- ✓ Git repository has initial commit
- ✓ Continuous deployment works (push to GitHub triggers deploy)

---

## Phase 1: MVP - Core Functionality

**Target Completion:** End of Weekend 1  
**Estimated Time:** 8-12 hours

### 1.1: Database Schema & Seed Data (2-3 hours)

**Dependencies:** Phase 0 complete (database connection working)

- [x] **Design and document data model** ✅
  - Review the data model in this plan
  - Create ERD (Entity Relationship Diagram) if helpful
  - Confirm all tables and relationships

- [x] **Create database migrations** ✅
  - Members table (id, name, email, member_type, attendance_since_hosting, last_hosted_date, total_hosting_count, first_attended, created_at, updated_at)
  - Locations table (id, name, address, phone, google_place_id, google_rating, price_level, cuisine_type, group_friendly, last_visited, visit_count, avg_group_rating, created_at, updated_at)
  - Lunches table (id, date, location_id FK, host_id FK, expected_attendance, actual_attendance, reservation_confirmed, status, created_at, updated_at)
  - Attendance table (id, lunch_id FK, member_id FK, was_host, created_at)
  - Ratings table (id, lunch_id FK, member_id FK, rating, comment, created_at)
  - Photos table (id, lunch_id FK, uploaded_by FK, file_url, thumbnail_url, caption, created_at, updated_at)
  - Photo_Tags table (id, photo_id FK, member_id FK, created_at)
  - Run migrations to create all tables

- [x] **Prepare seed data** ✅ (via CSV import system)
  - Collect real data: 25 member names and emails from lunch group
  - List 5-10 known restaurant locations with addresses
  - Create 3-4 historical lunch records (dates in past)
  - Set realistic attendance counts for each member (e.g., 5-20)
  - Identify who hosted those past lunches

- [x] **Load seed data into database** ✅ (via CSV import at /admin/setup/import)
  - Insert all 25 members (member_type = 'regular')
  - Insert locations
  - Insert historical lunches
  - Insert attendance records for historical lunches
  - Verify attendance_since_hosting counts are correct

- [x] **Write basic database query functions** ✅
  - Get all active members (member_type = 'regular', ordered by name)
  - Get hosting queue (ordered by attendance_since_hosting DESC, then by name)
  - Get next host (member with highest attendance_since_hosting)
  - Get backup host (member with second highest)
  - Get all locations (ordered by name)
  - Get upcoming lunches (status = 'planned')

**Testable Milestones:**
- ✓ All database tables created successfully (run `\dt` in psql or equivalent)
- ✓ Seed data inserted: 25 members, 5+ locations, 3+ historical lunches
- ✓ Query for next host returns expected person (manually verify math)
- ✓ Query for member list returns all 25 members alphabetically
- ✓ Hosting queue sorted correctly (person with most attendance first)
- ✓ Can retrieve lunch history with host names and locations
- ✓ Database relationships work (can join lunches to locations and members)

### 1.2: Secretary Dashboard - Attendance Tracker (4 hours)

- [x] **Create dashboard route/view** ✅
  - Admin authentication (simple password for MVP)
  - Dashboard homepage
  - Navigation menu
  - **MOBILE-FIRST: Works on phone first, desktop second**

- [x] **Build attendance tracking interface** ✅
  - Display current week's lunch info
  - Show checkbox list of all active members
  - **Large touch targets (44px minimum) for phone tapping**
  - Mark host with special indicator
  - "Add guest/new member" quick form
  - Display expected vs actual attendance count
  - Save button (full-width on mobile)

- [x] **Implement attendance save logic** ✅
  - Insert attendance records for checked members
  - Update member.attendance_since_hosting counters
  - If host checked: set last_hosted_date, reset counter to 0
  - If new member added: create member record
  - Update lunch.actual_attendance

- [ ] **Build guest → member conversion** (partial - can edit member_type manually)
  - Show guests who attended 3+ times
  - "Convert to Member" button (mobile-friendly)
  - Retain attendance credits
  - Add to email list flag

- [ ] **Mobile testing**
  - Test on iPhone Safari
  - Test on Android Chrome
  - Verify all touch targets adequate
  - No horizontal scrolling
  - Forms submit without zooming

**Testable Milestones:**
- ✓ Can log in to dashboard on phone
- ✓ Can check off attendees and save on phone
- ✓ All buttons easily tappable on mobile
- ✓ Member counters update correctly
- ✓ Host counter resets when marked as hosted
- ✓ Can add guest with name/email on phone
- ✓ Can add new regular member
- ✓ Guest with 3 attendances shows conversion prompt
- ✓ Works on both iOS and Android

### 1.3: Hosting Queue Management (2 hours)

- [x] **Display hosting queue** ✅
  - Show next 5 hosts in order
  - Display attendance count for each
  - Show last hosted date
  - Highlight next host and backup

- [ ] **Manual override capability**
  - "Swap Hosts" button
  - Select two members to swap positions
  - Confirm and update

- [x] **View hosting history** ✅ (partial - shows recent lunches on dashboard)
  - List of past lunches with host names
  - Filter by date range
  - Show hosting frequency per member

**Testable Milestones:**
- ✓ Hosting queue displays correctly ordered
- ✓ Next host identified accurately
- ✓ Can manually swap two hosts
- ✓ Queue re-sorts correctly after swap
- ✓ Hosting history shows accurate data

### 1.5: Initial Setup & CSV Import (Added)

- [x] **Initial setup wizard** ✅ (`/admin/setup`)
  - Status overview (member count, historical data status)
  - Step-by-step guide for new groups
  - Links to all setup functions

- [x] **CSV import/export system** ✅ (`/admin/setup/import`)
  - Download CSV template with current members
  - Upload CSV to add/update members
  - Parse and validate: name, email, member_type, attendance_since_hosting, last_hosted_date, total_hosting_count, first_attended
  - Error handling with row-level feedback
  - Re-runnable (updates existing, adds new)

**Testable Milestones:**
- ✓ Can download CSV template
- ✓ Can upload CSV and see members added
- ✓ Re-upload updates existing members by email
- ✓ Invalid data shows clear error messages

### 1.4: Email Templates (Preview Only) (2 hours)

- [x] **Create email templates (HTML)** ✅
  - Thursday host confirmation email
  - Friday secretary reminder email
  - Monday group announcement email
  - Tuesday rating request email

- [x] **Build email preview system** ✅
  - Route to preview each email type (`/admin/emails`)
  - Populate with sample data from database
  - Desktop/mobile preview toggle
  - Add "The AI Guy" branding footer

- [ ] **Manual send capability** (deferred to Phase 2 - requires Brevo)
  - Secretary can trigger send from dashboard
  - Select email type
  - Preview before send
  - Confirm and send

**Testable Milestones:**
- ✓ All 4 email templates render correctly
- ✓ Templates look professional on mobile
- ✓ Can preview emails with real data
- ✓ Branding footer displays correctly
- ⏳ Manual send via Brevo (Phase 2)

### 1.5: Basic Member Management (1 hour)

- [ ] **Member list view**
  - Show all members with status
  - Display attendance count, last hosted
  - Mark as active/inactive

- [ ] **Edit member**
  - Update name, email
  - Change member type
  - Manually adjust attendance count (for corrections)

**Testable Milestones:**
- ✓ Can view all members
- ✓ Can edit member details
- ✓ Can mark member inactive
- ✓ Inactive members don't show in attendance tracker

---

## Phase 2: Automation & Email

**Target Completion:** End of Weekend 2  
**Estimated Time:** 6-8 hours

### 2.1: Scheduled Email Jobs (3-4 hours)

**Dependencies:** Phase 1 complete (database with members, lunches, locations)

- [ ] **Set up scheduling system**
  - Choose: APScheduler (Python) or node-cron (Node.js)
  - Install and configure in your app
  - Create job management system (functions to run at scheduled times)
  - **For MVP:** Test by triggering jobs manually (don't wait for cron)
  - Set up cron expressions for each job (but test manually first)

- [ ] **Create email templates (if not done in Phase 1.4)**
  - Review templates created in 1.4
  - Ensure they accept dynamic data (host name, location, date, etc.)
  - Test rendering with sample data

- [ ] **Job 1: Thursday 9am - Host Confirmation Email**
  - Function: `send_host_confirmation_email()`
  - Logic:
    1. Calculate next Tuesday's date
    2. Query: Get next host from hosting queue
    3. Create or update lunch record for next Tuesday (status='planned')
    4. Generate unique confirmation token
    5. Create email with host name, date, confirmation link
    6. Send via Brevo
    7. Log email sent (save to database)
  - Test: Run function manually, verify email received
  - Test: Check lunch record created in database

- [ ] **Job 2: Friday 9am - Secretary Reminder (Conditional)**
  - Function: `send_secretary_reminder()`
  - Logic:
    1. Query: Get next Tuesday's lunch record
    2. Check: Is location confirmed? (24 hours since Thursday email)
    3. **If confirmed:** Send reservation reminder email to secretary
       - Include: restaurant name, phone, address
       - Include: expected attendance (average of last 4 weeks)
       - Include: host name
    4. **If NOT confirmed:** Send alert email to secretary
       - Include: "Host [name] has not responded"
       - Include: backup host (next in queue)
       - Include: options (contact host, use backup, secretary chooses)
    5. Log email sent
  - Test: Create lunch with confirmed location, run function, verify correct email
  - Test: Create lunch without confirmed location, run function, verify alert email

- [ ] **Job 3: Monday 9am - Group Announcement**
  - Function: `send_group_announcement()`
  - Logic:
    1. Query: Get next Tuesday's lunch (should be confirmed by now)
    2. Query: Get all active members (member_type='regular')
    3. For location: get rating, last visit date, average attendance
    4. Generate Google Maps embed URL for location
    5. Create email with all details
    6. Send to all active members (batch send via Brevo)
    7. Log emails sent
  - Test: Run function, verify email sent to all members
  - Test: Check maps embed displays correctly in email

- [ ] **Job 4: Tuesday 6pm - Rating Request (Conditional)**
  - Function: `send_rating_requests()`
  - Logic:
    1. Query: Get today's lunch record
    2. Check: Has attendance been logged? (required)
    3. **If attendance logged:**
       - Query: Get members who attended (from attendance table)
       - For each attendee: generate unique rating token
       - Create rating request email with lunch details
       - Send to attendees only (not all members)
       - Log emails sent
    4. **If attendance NOT logged yet:**
       - Skip (will try again tomorrow or secretary can trigger manually)
  - Test: Log attendance for a lunch, run function, verify emails to attendees only
  - Test: Run function without attendance logged, verify no emails sent

- [ ] **Schedule jobs in production**
  - Configure cron expressions:
    - Thursday 9am: `0 9 * * THU`
    - Friday 9am: `0 9 * * FRI`
    - Monday 9am: `0 9 * * MON`
    - Tuesday 6pm: `0 18 * * TUE`
  - **For MVP:** Keep manual trigger capability for testing
  - Add admin dashboard button to manually trigger any job
  - Document how to trigger jobs manually

**Testable Milestones:**
- ✓ All 4 email job functions created and working
- ✓ Thursday email: Can manually trigger, email received, lunch record created
- ✓ Friday email: Correctly detects confirmed vs not-confirmed, sends appropriate email
- ✓ Monday email: Sends to all active members, maps embed displays
- ✓ Tuesday email: Only sends to logged attendees, not all members
- ✓ All emails contain accurate dynamic data (names, locations, dates)
- ✓ All emails logged in database with timestamp
- ✓ Scheduled jobs configured (but test manually before trusting cron)
- ✓ Admin can manually trigger any job from dashboard (for testing/emergencies)

### 2.2: Host Confirmation Flow (2 hours)

- [ ] **Confirmation landing page (MOBILE-FIRST)**
  - Unique token in email link
  - Display: "You're hosting [date]"
  - Location selection form
  - **Optimized for phone - host will check this on mobile**

- [ ] **Location selection interface**
  - Radio buttons for previous locations (large touch targets)
  - Display: rating, last visit, Google rating, price
  - **Mobile-friendly layout - stacked cards, not table**
  - "Suggest new location" option (text input)
  - Capacity confirmation checkbox (for new locations)
  - **Clear visual hierarchy on small screens**

- [ ] **Save confirmation**
  - Update lunch record with location and confirmation status
  - If new location: create location record (manual Google lookup for MVP)
  - Send confirmation email to host
  - Trigger secretary Friday email early if confirmed

- [ ] **Mobile testing**
  - Verify email link opens correctly on phone
  - Test form submission on mobile
  - Ensure radio buttons easy to tap
  - No zoom required to read text

**Testable Milestones:**
- ✓ Host can access confirmation page from email link on phone
- ✓ Can select from previous locations on mobile
- ✓ Radio buttons and checkboxes easy to tap
- ✓ Can suggest new location with capacity check
- ✓ Confirmation saves and updates lunch record
- ✓ Secretary gets Friday email after confirmation
- ✓ Page renders well on iPhone and Android

### 2.3: Email Tracking & Logs (1 hour)

- [ ] **Create email_logs table**
  - id, email_type, recipient, sent_at, delivery_status
  - lunch_id (FK, optional)

- [ ] **Log all sent emails**
  - Record in database
  - Track Brevo message ID
  - Handle Brevo webhooks (optional)

- [ ] **Display in dashboard**
  - Recent emails sent
  - Delivery status
  - Resend capability

**Testable Milestones:**
- ✓ All sent emails logged in database
- ✓ Can view email log in dashboard
- ✓ Can resend failed emails

---

## Phase 3: Location Management & Ratings

**Target Completion:** End of Weekend 3  
**Estimated Time:** 6-8 hours

### 3.1: Google Places Integration (3 hours)

- [ ] **Set up Google Cloud project**
  - Enable Places API
  - Enable Maps Static API
  - Get API key
  - Set up billing (free tier $200/month)
  - Restrict API key to domain

- [ ] **Location search autocomplete**
  - Add Google Places autocomplete to "new location" input
  - Display: name, address, rating, price, cuisine
  - Preview before adding

- [ ] **Fetch place details**
  - When new location selected, fetch full details
  - Store: google_place_id, rating, price_level, address, phone
  - Auto-populate location record

- [ ] **Generate map embeds**
  - Function to create Google Maps Static API URL
  - Embed in Monday announcement email
  - Include in dashboard

**Testable Milestones:**
- ✓ Google Places autocomplete works in form
- ✓ Selecting a place fetches full details
- ✓ New location saves with Google data
- ✓ Map embed displays correctly in email
- ✓ API usage stays within free tier limits

### 3.2: Rating System (2 hours)

- [ ] **Rating submission page**
  - Unique token link from Tuesday email
  - Display: lunch date, location
  - 5-star rating selector (visual stars)
  - Optional comment text area
  - Submit button

- [ ] **Save rating**
  - Insert into ratings table
  - Recalculate location.avg_group_rating
  - Thank you confirmation

- [ ] **Display ratings in location list**
  - Show average rating per location
  - Show number of ratings
  - Display recent comments (optional)

**Testable Milestones:**
- ✓ Can access rating page from email link
- ✓ Can submit 5-star rating with comment
- ✓ Rating saves to database
- ✓ Location average rating recalculates correctly
- ✓ Ratings display in location selection form

### 3.3: Location Management Dashboard (1 hour)

- [ ] **Locations list view**
  - All locations with ratings, visit count
  - Sort by: rating, last visited, visit count
  - Filter by: group-friendly, price level

- [ ] **Edit location**
  - Update details manually
  - Mark as group-friendly
  - Add notes (optional)

- [ ] **Location history**
  - View all lunches at this location
  - See attendance trends
  - Rating history

**Testable Milestones:**
- ✓ Can view all locations
- ✓ Can edit location details
- ✓ Can filter/sort locations
- ✓ Location history displays correctly

---

## Phase 4: Analytics & Polish

**Target Completion:** End of Weekend 4  
**Estimated Time:** 8-12 hours  
**Dependencies:** Phases 1-3 complete (emails automated, locations integrated, ratings working)

### 4.0: Member Authentication System (2 hours)

**Why this comes first:** Photo gallery (4.3) requires members to log in. Build auth system before gallery.

- [ ] **Choose authentication approach**
  - **Recommended: Magic link** (passwordless, mobile-friendly, more secure)
  - Alternative: Simple password with "remember me"
  - Document choice and reasoning

- [ ] **Implement magic link authentication**
  - Create login page (mobile-first UI)
  - User enters email address
  - Generate unique token, store in database with expiration (15 min)
  - Send email with login link containing token
  - Token validation endpoint
  - Create session on successful login
  - Session management (cookies, 30 day expiration)

- [ ] **Or implement password authentication**
  - Create login page with email/password form
  - Hash passwords with bcrypt
  - Session management
  - "Remember me" functionality
  - Password reset flow (optional for MVP)

- [ ] **Implement logout**
  - Logout button in member portal
  - Clear session
  - Redirect to login page

- [ ] **Protect member-only routes**
  - Decorator/middleware to require authentication
  - Redirect to login if not authenticated
  - Apply to: photo upload, gallery, profile pages

- [ ] **Member session UI**
  - Show "Logged in as [Name]" in header
  - Logout button always visible
  - Remember login state across visits

**Testable Milestones:**
- ✓ Can request login link and receive email (or enter password)
- ✓ Login link/password works and creates session
- ✓ Session persists across page refreshes
- ✓ Can logout successfully
- ✓ Protected routes redirect to login when not authenticated
- ✓ Login flow works smoothly on mobile (iPhone and Android)
- ✓ Session expires after 30 days of inactivity
- ✓ UI shows current logged-in member name

---

### 4.1: Data Visualizations (3 hours)

**Dependencies:** Phase 4.0 complete (needed if analytics shown in member portal)

- [ ] **Interactive map (Folium)**
  - Pin for each location visited
  - Popup shows: name, rating, visit count, last visit
  - Color-code by rating or visit frequency
  - Embed in dashboard

- [ ] **Attendance charts (Plotly)**
  - Attendance over time (line chart)
  - Average by location (bar chart)
  - Member participation (who attends most)

- [ ] **Location analytics**
  - Most/least popular locations
  - Rating distribution
  - Price level distribution
  - Cuisine variety

- [ ] **Member analytics**
  - Individual attendance history
  - Hosting frequency
  - Rating patterns (harsh vs generous)

**Testable Milestones:**
- ✓ Folium map displays all visited locations
- ✓ Map pins clickable with details
- ✓ Charts render correctly
- ✓ Charts update with new data
- ✓ Analytics accessible from dashboard

### 4.2: UI Polish (Mobile-First) (2 hours)

- [ ] **Apply Tailwind CSS (mobile-first)**
  - Consistent color scheme (professional blues/grays)
  - **Responsive design: design for mobile, enhance for desktop**
  - Clean typography (readable on small screens)
  - Proper spacing and alignment
  - Touch-friendly UI elements throughout

- [ ] **Improve email templates**
  - Better visual hierarchy
  - Use color sparingly (brand colors)
  - **Ensure mobile rendering (most will read on phone)**
  - Test across email clients (Gmail app, iOS Mail)
  - Responsive email layout

- [ ] **Add loading states**
  - Spinner for async operations
  - Disabled buttons during submit
  - Success/error toast notifications (mobile-friendly)
  - **Don't block UI - show progress**

- [ ] **Error handling UI**
  - Friendly error messages
  - Validation feedback (visible on mobile)
  - 404 and error pages
  - **Mobile-optimized error states**

- [ ] **Accessibility**
  - Proper contrast ratios
  - Touch targets 44px minimum
  - Form labels associated correctly
  - Works with screen readers

**Testable Milestones:**
- ✓ Dashboard looks professional on phone
- ✓ Dashboard looks professional on desktop (secondary)
- ✓ Emails render correctly in Gmail app
- ✓ Emails render correctly in iOS Mail
- ✓ Loading states appear during saves
- ✓ Error messages display appropriately on mobile
- ✓ All touch targets meet 44px minimum
- ✓ Color contrast passes WCAG AA

### 4.3: Photo Gallery & Member Portal (6-8 hours)

**THIS IS THE KILLER FEATURE - Mobile-first design is critical**  
**Dependencies:** Phase 4.0 complete (member authentication required)

**4.3.1: Photo Upload (Mobile-First) (3 hours)**

- [ ] **Choose and set up image storage**
  - **Recommended for MVP:** Local filesystem
    - Create `/static/uploads/` directory in project
    - Ensure directory is writable
    - Configure app to serve static files from this directory
  - **Alternative:** AWS S3/Cloudflare R2 (if you want to start with cloud storage)
  - **Decision point:** Local is simpler for MVP, migrate to cloud later if needed

- [ ] **Create file upload route and basic validation**
  - Create route: `POST /upload-photo`
  - Require authentication (check if user logged in)
  - Accept: `multipart/form-data`
  - Validate file types: Allow only jpg, jpeg, png, gif, webp
  - Validate file size: Maximum 10MB per file
  - Accept multiple files (up to 10 at once)
  - Return error for invalid files with clear message

- [ ] **Implement client-side image compression (JavaScript)**
  - Add compression function before upload (see Appendix for code)
  - Target: Max 1920px width, 80% JPEG quality
  - Result: Compressed images < 2MB each
  - Show compression progress to user
  - Test: Upload 8MB photo, verify it's compressed to < 2MB before sending

- [ ] **Build mobile-optimized upload form**
  - **File input:**
    - `<input type="file" accept="image/*" capture="camera" multiple>`
    - On iOS: Opens camera or photo library
    - On Android: Opens camera or gallery
    - Allows multiple file selection
  - **Lunch date selector:**
    - Dropdown showing recent lunches (last 8 weeks)
    - Format: "Dec 17, 2024 - Zulo's Board Game Cafe"
    - Default: Most recent Tuesday (query database for this)
    - If no lunch this week yet, show upcoming Tuesday
  - **Caption field (optional):**
    - Text input, placeholder: "Add a caption..."
    - Max length: 200 characters
    - autocomplete="off" (prevents autofill on mobile)
  - **Member tagging:**
    - Query database: Get members who attended selected lunch
    - Display: Large checkboxes (44px touch targets)
    - Pre-select the uploader (current logged-in user)
    - Allow tagging only members who were actually there
  - **Upload button:**
    - Full-width on mobile, auto-width on desktop
    - Text: "Upload X Photos" (X = number of files selected)
    - Disabled during upload
    - Shows progress: "Uploading 2 of 5..."

- [ ] **Implement server-side upload processing**
  - For each uploaded file:
    1. Re-validate file type and size on server (don't trust client)
    2. Generate unique filename to prevent collisions:
       - Format: `{timestamp}_{random_8char}_{sanitized_original}.jpg`
       - Example: `1702846392_a3f9k2m1_lunch.jpg`
       - Sanitize: Remove spaces, special chars from original name
    3. Save file to uploads directory
    4. Generate thumbnail using Pillow/PIL:
       - Max dimensions: 300x300px (maintains aspect ratio)
       - Save as: `{filename}_thumb.jpg`
       - Quality: 85%
    5. Store file paths (relative to static directory)
  - See Appendix for thumbnail generation code

- [ ] **Save photo metadata to database**
  - Insert into `photos` table:
    - `lunch_id`: From form dropdown
    - `uploaded_by`: Current logged-in member ID
    - `file_url`: Path to full image (e.g., `/static/uploads/image.jpg`)
    - `thumbnail_url`: Path to thumbnail
    - `caption`: From form (can be empty)
    - `created_at`: Current timestamp
  - Get the inserted photo ID
  - For each tagged member:
    - Insert into `photo_tags` table:
      - `photo_id`: Just inserted
      - `member_id`: Tagged member ID
  - Commit transaction (all or nothing)

- [ ] **Handle errors and edge cases**
  - Invalid file type: Return error "Please upload JPG, PNG, or GIF only"
  - File too large: Return error "Images must be under 10MB"
  - No files selected: Return error "Please select at least one photo"
  - Database error: Log error, show generic "Upload failed" message
  - Disk full: Log error, show "Server storage full" message
  - Allow user to retry without losing form data (caption, tags, lunch selection)

- [ ] **Test on real mobile devices**
  - **iPhone (Safari):**
    - Tap "Choose Files" → should show "Take Photo" and "Photo Library" options
    - Take new photo with camera
    - Upload from photo library
    - Select multiple photos (3-5 at once)
    - Verify images compress before upload (check in browser network tab)
    - Confirm upload completes successfully
  - **Android (Chrome):**
    - Same tests as iPhone
    - Verify camera access permission requested
    - Confirm multiple file selection works
  - **Both devices:**
    - Check progress indicator shows during upload
    - Verify success message appears after completion
    - Confirm photos immediately appear in gallery
    - Test on cellular connection (not just WiFi)

**Testable Milestones:**
- ✓ Upload route created and requires authentication
- ✓ File validation rejects non-image files with clear error
- ✓ Files larger than 10MB rejected with error message
- ✓ Client-side compression working (images < 2MB before upload)
- ✓ Multiple images can be uploaded simultaneously (test with 5 photos)
- ✓ Thumbnail generation works (all thumbnails 300x300 or smaller)
- ✓ Photos saved to database with correct lunch_id and uploader
- ✓ Member tags saved correctly (verify in photo_tags table)
- ✓ Caption saved if provided, NULL if empty
- ✓ Can upload from iPhone camera (test on real device)
- ✓ Can upload from iPhone photo library (test on real device)
- ✓ Can upload from Android camera (test on real device)
- ✓ Can upload from Android gallery (test on real device)
- ✓ Upload progress indicator displays and updates correctly
- ✓ Success message shows after upload
- ✓ Error messages display for all error scenarios
- ✓ Uploaded photos immediately visible in gallery (refresh gallery page)
- ✓ Uploader attribution displays: "Photo by [Name]"

**4.3.2: Photo Gallery (Mobile-First) (2 hours)**

- [ ] **Gallery home (mobile-optimized)**
  - Timeline view (most recent first)
  - Grouped by lunch date
  - Large thumbnails (full width on mobile)
  - Tap to view full photo
  - Infinite scroll or pagination

- [ ] **Individual photo view**
  - Full-screen photo
  - Swipe left/right for next/previous
  - Display: location, date, uploader
  - Show tagged members
  - Download button
  - Delete (if you uploaded it)
  - Back to gallery

- [ ] **Browse filters (mobile-friendly)**
  - By date (timeline - default view)
  - By location (list of locations → photos)
  - By member (your photos, photos you're tagged in)
  - Simple tab navigation at top

- [ ] **Gallery UI polish**
  - Responsive grid (1 col mobile, 3 cols desktop)
  - Lazy loading images
  - Smooth transitions
  - Touch-optimized (swipe, pinch-zoom)

**Testable Milestones:**
- ✓ Gallery displays all photos
- ✓ Photos grouped by lunch
- ✓ Can tap photo to view full screen
- ✓ Can swipe between photos
- ✓ Can filter by location on mobile
- ✓ Can filter by member on mobile
- ✓ Images load fast on cellular
- ✓ Can download photos
- ✓ Can delete own photos
- ✓ Works smoothly on phone

**4.3.3: Member Portal Dashboard (1 hour)**

- [ ] **Personal dashboard (mobile-first)**
  - Your stats (lunches attended, photos uploaded, times tagged)
  - Countdown to next time you host
  - Recent photos from group
  - Upcoming lunch info
  - **Bottom navigation: Home | Gallery | Upload | Profile**

- [ ] **Quick actions**
  - [Upload Photo] - prominent button
  - [View Gallery]
  - [Rate Last Lunch] (if not done)

- [ ] **Profile page**
  - Your attendance history
  - Your uploaded photos
  - Photos you're tagged in
  - Edit profile (name, email)

**Testable Milestones:**
- ✓ Dashboard displays correctly on phone
- ✓ Stats are accurate
- ✓ Can navigate to upload from dashboard
- ✓ Can navigate to gallery from dashboard
- ✓ Bottom nav works on mobile
- ✓ Profile shows accurate data

**4.3.4: PWA Features (Optional, 1 hour)**

- [ ] **Progressive Web App setup**
  - Create manifest.json
  - Add service worker for offline capability
  - Add to home screen support (iOS/Android)
  - App icon (192x192, 512x512)
  - Splash screen

- [ ] **Offline capability**
  - Cache recently viewed photos
  - Queue uploads when offline
  - Sync when back online

**Testable Milestones:**
- ✓ Can "Add to Home Screen" on iPhone
- ✓ Can "Add to Home Screen" on Android
- ✓ App icon displays correctly
- ✓ Works in standalone mode (no browser chrome)
- ✓ Previously viewed photos available offline

**4.3.5: Mobile Testing (Critical, 1 hour)**

- [ ] **Comprehensive mobile testing**
  - Test on real iPhone (Safari)
  - Test on real Android (Chrome)
  - Test camera upload
  - Test gallery upload
  - Test swipe gestures
  - Test all touch targets (minimum 44px)
  - Test on slow 3G connection
  - Verify no horizontal scrolling anywhere
  - Check text readability without zoom

**Testable Milestones:**
- ✓ Everything works on iPhone Safari
- ✓ Everything works on Android Chrome  
- ✓ Camera access works
- ✓ Photos upload on cellular connection
- ✓ Images don't take forever to load
- ✓ All buttons easy to tap
- ✓ No zoom required to use any feature
- ✓ Swipe gestures feel natural

---

## Phase 5: Production & Handoff

**Target Completion:** After testing period  
**Estimated Time:** 2-3 hours

### 5.1: Testing & Bug Fixes (Variable)

- [ ] **Error handling review**
  - Review all user-facing forms for validation
  - Add try/catch blocks around database operations
  - Add try/catch around external API calls (Brevo, Google Places)
  - Implement error logging (to file or service like Sentry)
  - Test error scenarios: invalid email, failed upload, database error
  - Ensure friendly error messages (not stack traces) shown to users

- [ ] **End-to-end testing**
  - Full weekly cycle with test data
  - Thursday: Host receives confirmation email and selects location
  - Friday: Secretary receives reservation reminder
  - Monday: All members receive announcement email
  - Tuesday: Secretary tracks attendance
  - Tuesday evening: Attendees receive rating request
  - Verify all emails send correctly and contain accurate data

- [ ] **Mobile-specific testing (CRITICAL)**
  - Test on real iPhone (Safari browser, iOS 15+)
  - Test on real Android phone (Chrome browser, Android 10+)
  - Test camera access and photo upload from device
  - Test photo gallery browsing and swiping gestures
  - Test on slow cellular connection (use Chrome DevTools throttling + real 3G/4G)
  - Verify all touch targets adequate (44px minimum, use browser inspect)
  - Check that no horizontal scrolling occurs on any page
  - Test form submissions without zoom (use browser zoom level check)
  - Verify images load quickly on mobile (< 3 seconds on 3G)
  - Test PWA "Add to Home Screen" if implemented (both iOS and Android)

- [ ] **Cross-browser testing**
  - iOS Safari (primary - test all features)
  - Android Chrome (primary - test all features)
  - Desktop Chrome (secondary - verify nothing broken)
  - Desktop Safari (secondary - verify nothing broken)
  - Firefox (optional - quick smoke test)

- [ ] **Load testing (light)**
  - Verify app handles 25 simultaneous users (use simple load testing tool)
  - Check email sending doesn't hit rate limits (25 emails at once for Monday announcement)
  - Test multiple photo uploads simultaneously (5 users uploading at once)
  - Verify thumbnail generation doesn't slow down server excessively

- [ ] **Security review**
  - Secure admin password (bcrypt hash, test login works)
  - Validate all user inputs (test with malicious input like `<script>alert('xss')</script>`)
  - Prevent SQL injection (use parameterized queries, test with SQL injection attempts)
  - Rate limit API endpoints (prevent abuse, test with rapid requests)
  - **Secure file upload:**
    - Validate image file types (only jpg, png, gif, webp allowed)
    - Enforce max file size (e.g., 10MB)
    - Sanitize filenames (remove special characters)
    - Prevent path traversal attacks
  - Prevent unauthorized photo deletion (only uploader can delete their photos)
  - Test authentication bypass attempts
  - Verify sessions expire correctly

**Testable Milestones:**
- ✓ All error scenarios display friendly messages (no stack traces to users)
- ✓ Errors logged to file/service for debugging
- ✓ Full weekly cycle completes without errors
- ✓ All features work on iPhone Safari (test every page and interaction)
- ✓ All features work on Android Chrome (test every page and interaction)
- ✓ No horizontal scrolling on any page on mobile
- ✓ All buttons/links easily tappable (no mis-taps during testing)
- ✓ App handles 25 concurrent users without crashing
- ✓ Security tests pass (no XSS, SQL injection, unauthorized access)
- ✓ File uploads properly validated (malicious files rejected)

### 5.2: Documentation (2 hours)

- [ ] **Secretary user guide**
  - How to log in to admin dashboard
  - How to track attendance each Tuesday
  - How to add guests and convert to members
  - How to manage members (mark inactive, update emails)
  - How to handle host no-shows (Friday backup process)
  - How to manually resend emails if needed
  - How to view hosting queue and make swaps
  - How to confirm reservations in the system
  - Troubleshooting common issues (email not sending, etc.)
  - Include screenshots for each step
  - Format as PDF or simple webpage

- [ ] **Member quick-start guide**
  - How to log in (magic link or password)
  - How to upload photos from phone
  - How to browse photo gallery
  - How to submit ratings
  - How to view your stats
  - Keep it to one page (members won't read more)

- [ ] **Technical README for future maintenance**
  - Architecture overview (what each component does)
  - How to run locally (step-by-step setup)
  - How to deploy to production
  - Environment variables needed and where to get them
  - How to run database migrations
  - How to access production logs
  - How to backup and restore database
  - How to add a new member manually in database
  - Common issues and solutions

- [ ] **Email template documentation**
  - List all email types (Thursday, Friday, Monday, Tuesday)
  - Where templates are stored in code
  - How to edit email content
  - How to preview changes before sending

**Testable Milestones:**
- ✓ Secretary guide complete with screenshots
- ✓ Member quick-start guide fits on one page
- ✓ Technical README allows someone else to set up locally
- ✓ All environment variables documented
- ✓ Backup/restore procedure tested and documented

### 5.3: Deployment & Training (2 hours)

- [ ] **Production deployment**
  - Deploy latest code to production (Railway/Render/Heroku)
  - Set up production database (if not already done)
  - Run migrations on production database
  - Load production seed data (real 25 members, real locations)
  - Configure all environment variables in production
  - Set up automated daily database backups
  - Configure monitoring/alerts (UptimeRobot or similar - free tier)
  - Test production deployment (visit app, verify database connection)

- [ ] **Production smoke test**
  - Verify app loads and displays correctly
  - Test admin login works
  - Test member login works
  - Upload a test photo
  - Send a test email (to yourself, not the whole group yet)
  - Check all scheduled jobs configured correctly (but don't trigger yet)

- [ ] **Secretary training session (1 hour live session)**
  - Schedule 1-hour call or in-person meeting with secretary
  - Live walkthrough of admin dashboard
  - Practice tracking attendance together
  - Practice adding a guest and converting to member
  - Show how to handle host no-show scenario
  - Demonstrate how to resend an email if needed
  - Q&A session for any questions
  - Provide login credentials securely
  - Share secretary user guide document

- [ ] **Soft launch (2-3 weeks with oversight)**
  - Enable scheduled emails for next lunch cycle
  - Monitor first Thursday email (host confirmation)
  - Monitor first Friday email (secretary reminder)
  - Monitor first Monday email (group announcement)
  - Be available for troubleshooting during first 2-3 weeks
  - Collect feedback from secretary and members
  - Make adjustments based on feedback

- [ ] **Official announcement to group**
  - After 2-3 successful weeks, announce to full group
  - Send email explaining new system
  - Provide member quick-start guide
  - Encourage members to log in and explore
  - Highlight photo gallery feature
  - Invite feedback and suggestions

**Testable Milestones:**
- ✓ Production app stable and accessible at public URL
- ✓ All environment variables set in production
- ✓ Database backups configured (verify backup file created)
- ✓ Monitoring alerts set up (get test alert)
- ✓ Secretary can use system independently after training
- ✓ Secretary successfully tracks attendance for first real lunch
- ✓ First automated weekly cycle completes successfully (all 4 emails sent)
- ✓ No critical bugs reported during soft launch
- ✓ At least 5 members upload photos in first 2 weeks
- ✓ Positive feedback from at least 3 members

---

## Timeline & Milestones

### Weekend 1: MVP Foundation
**Friday Evening (3 hours):**
- Phase 0: Setup & Infrastructure complete
- Database schema created
- App deployed to production (skeleton)

**Saturday (6 hours):**
- Phase 1.1: Database seeded with real data
- Phase 1.2: Attendance tracker functional
- Phase 1.3: Hosting queue working

**Sunday (3 hours):**
- Phase 1.4: Email templates previewing
- Phase 1.5: Member management working
- **MVP Demo Ready:** Show secretary the dashboard

### Weekend 2: Automation
**Saturday (4 hours):**
- Phase 2.1: Scheduled email jobs configured
- Phase 2.2: Host confirmation flow complete

**Sunday (3 hours):**
- Phase 2.3: Email tracking implemented
- **Full automation test:** Run through one week cycle manually

### Weekend 3: Integration
**Saturday (4 hours):**
- Phase 3.1: Google Places integrated
- Phase 3.2: Rating system functional

**Sunday (2 hours):**
- Phase 3.3: Location management polished
- **Feature complete:** All core functionality working

### Weekend 4: Polish & Authentication
**Saturday (4 hours):**
- Phase 4.0: Member authentication system (2 hours)
- Phase 4.1: Start analytics and visualizations (2 hours)

**Sunday (4 hours):**
- Phase 4.1: Complete analytics and visualizations (1 hour)
- Phase 4.2: UI improvements (mobile-first polish) (2 hours)
- Phase 4.3: Begin photo gallery (upload setup) (1 hour)

**Total Weekend 4: 8 hours**

### Weekend 5: Photo Gallery
**Saturday (4 hours):**
- Phase 4.3: Photo upload completion (2 hours)
- Phase 4.3: Photo gallery views (2 hours)

**Sunday (4 hours):**
- Phase 4.3: Member portal dashboard (1 hour)
- Phase 4.3: PWA features (optional) (1 hour)
- Phase 4.3: Mobile testing (1 hour)
- Bug fixes and refinements (1 hour)

**Total Weekend 5: 8 hours**  
**DEMO READY:** Full feature set including photo gallery

### Week 6: Final Testing & Launch
**During week:**
- Phase 5: Testing, documentation, deployment
- Mobile testing on real devices (iPhone, Android)
- Secretary training and handoff
- **Go-live:** First fully automated week with photo uploads

---

## Risk Assessment & Mitigation

### Technical Risks

**Risk:** Google Places API costs exceed budget  
**Mitigation:** 
- Cache location data aggressively
- Use free tier ($200/month should be plenty for 1 lookup/week)
- Set billing alerts at $50

**Risk:** Email delivery issues (spam filters)  
**Mitigation:**
- Use Brevo with verified domain
- Keep email content professional
- Avoid spam trigger words
- Implement SPF/DKIM records

**Risk:** Database corruption or data loss  
**Mitigation:**
- Daily automated backups
- Version control for schema migrations
- Keep seed data script for recovery

### User Adoption Risks

**Risk:** Secretary finds system too complex  
**Mitigation:**
- Keep MVP extremely simple
- Provide thorough training
- Offer to be "on call" for first month
- Have manual backup process documented

**Risk:** Members don't respond to confirmation emails  
**Mitigation:**
- Backup host system
- Secretary can manually select location
- Clear deadline communication (24 hours)

**Risk:** Low rating participation  
**Mitigation:**
- Make rating super easy (one click)
- Keep it optional
- Focus on locations data, ratings are bonus

---

## Success Criteria

### Technical Success
- ✓ Zero downtime during operating hours (Mon-Fri 8am-8pm)
- ✓ All scheduled emails send within 5 minutes of scheduled time
- ✓ Page load times under 2 seconds on mobile cellular
- ✓ **Mobile-responsive on iOS Safari and Android Chrome**
- ✓ Data accuracy: hosting queue always mathematically correct
- ✓ **Photo uploads work reliably from mobile devices**
- ✓ **Images compressed to < 2MB before upload**

### User Success
- ✓ Secretary reports time savings (30 min → 5 min per week)
- ✓ 100% of lunches have confirmed location by Monday
- ✓ 80%+ attendance tracking completion rate
- ✓ At least 50% rating participation after 4 weeks
- ✓ Zero complaints about email spam or quality
- ✓ **At least 60% of members upload photos within first month**
- ✓ **Average 5+ photos uploaded per lunch**
- ✓ **Members check app at least weekly (photo engagement)**

### Business Success (Marketing Value)
- ✓ Positive feedback from at least 5 lunch members
- ✓ At least 2 "What else can you build?" conversations
- ✓ At least 1 consulting lead generated within 3 months
- ✓ Project becomes portfolio piece with live demo
- ✓ "The AI Guy" brand reinforced in local business community
- ✓ **Photo gallery becomes the "show off" feature** ("Check out what Josh built")
- ✓ **Word-of-mouth spreads beyond lunch group** (people show friends the app)

---

## Post-Launch Roadmap

### Phase 6: Advanced Features (Future)
- **Photo enhancements:**
  - Face detection for auto-tagging (AWS Rekognition)
  - Photo comments/reactions
  - Photo albums by theme/event
  - Slideshow mode
  - Share photos to social media
  - Print photo book feature
- **Communication:**
  - AI phone reservation system (using Gemini or similar)
  - SMS notifications as backup to email
  - Push notifications (PWA)
  - In-app messaging/comments
- **Analytics & insights:**
  - "You visited 47 restaurants this year"
  - Member participation leaderboards (friendly competition)
  - Location recommendation engine
  - Expense tracking for hosts
- **Integration:**
  - Calendar integration (add to personal calendars)
  - Slack/Discord integration
  - Export data (CSV, PDF reports)
- **Social features:**
  - Dietary restrictions tracking
  - "This Day in Lunch History" feature
  - Member profiles
  - Favorite location voting

### Maintenance Plan
- **Weekly:** Monitor error logs, check scheduled jobs ran successfully
- **Monthly:** Review analytics, check for errors, verify mobile performance
- **Quarterly:** Update dependencies, security patches, add requested features based on feedback
- **Annually:** Review with lunch group, plan major feature additions

### Scaling Considerations
- If group grows beyond 50 members: optimize database queries
- If photo storage exceeds 10GB: migrate to S3/R2
- If email volume exceeds Brevo free tier: upgrade plan or switch provider
- Consider caching layer (Redis) for frequently accessed data

---

## Notes & Decisions Log

### Key Technical Decisions
- **Why Flask over Django?** Simpler, faster for small project. Don't need admin panel since building custom UI.
- **Why PostgreSQL over SQLite?** Better for analytics queries, more production-ready, easy to scale.
- **Why Tailwind over Bootstrap?** More modern, better for custom design, smaller bundle size, excellent mobile-first utilities.
- **Why Brevo over AWS SES?** Simpler API, better free tier, easier setup for small volume.
- **Why mobile-first?** Users are contractors/business owners who live on their phones, not at desks. Photo uploads happen at restaurants. Desktop is secondary use case.
- **Why local storage then S3?** Start simple for MVP, migrate to S3 when storage needs grow. Premature optimization wastes time.
- **Why client-side image compression?** Save bandwidth on mobile uploads, reduce server load, better UX (faster uploads on cellular).

### Design Decisions
- **Why not mobile app?** Web is sufficient, accessible from any device, no app store approval needed, easier to maintain.
- **Why manual reservation vs automated?** AI calling is cool but risky for MVP. Human confirmation ensures quality. Can add later as Phase 6.
- **Why rating optional?** Don't want to add friction. Locations data valuable even without ratings.
- **Why allow all members to upload photos?** Crowdsourced content = more photos, better engagement, community ownership. Trust model works for professional group.
- **Why photo gallery is not optional?** This is the engagement hook. Scheduling is useful, photos are memorable. Photos create the word-of-mouth marketing.
- **Why PWA over native app?** No app store friction, works cross-platform, easier to maintain, "Add to Home Screen" gives app-like experience.

---

## Common Pitfalls to Avoid

### Technical Pitfalls

**1. Not testing on real mobile devices early enough**
- **Problem:** Desktop Chrome DevTools mobile emulation != real iPhone/Android
- **Solution:** Test on real devices starting in Phase 1, not just Phase 5
- **Why it matters:** Touch interactions, camera access, form zoom behavior all differ

**2. Hardcoding values instead of using environment variables**
- **Problem:** Secrets committed to Git, can't deploy to different environments
- **Solution:** Use .env file for all config (API keys, database URL, domain)
- **Check:** Can you deploy to a fresh environment without changing code?

**3. Not validating user input**
- **Problem:** Bad data breaks the app, security vulnerabilities
- **Solution:** Validate emails, file types, text length on backend
- **Check:** Try submitting forms with malicious/invalid data

**4. Forgetting to update hosting queue after attendance tracking**
- **Problem:** Wrong person selected as next host
- **Solution:** Ensure attendance save updates all member counters atomically
- **Check:** Manually verify queue after saving attendance

**5. Email links breaking in different email clients**
- **Problem:** Links work in Gmail but not Outlook or iPhone Mail
- **Solution:** Use absolute URLs (not relative), test in multiple clients
- **Check:** Send test emails to your Gmail, Outlook, and iPhone

**6. Not compressing images before upload**
- **Problem:** 12MB iPhone photos eat bandwidth and storage
- **Solution:** Compress client-side before upload (see code examples)
- **Check:** Upload photo from phone, verify file size < 2MB

**7. Database migrations not reversible**
- **Problem:** Can't roll back if migration breaks production
- **Solution:** Write both upgrade and downgrade for each migration
- **Check:** Test rollback locally before deploying

### Process Pitfalls

**8. Skipping mobile testing until the end**
- **Problem:** Discover major mobile issues too late to fix easily
- **Solution:** Test every feature on mobile as you build it
- **When:** Every phase should include mobile testing milestone

**9. Building features without feedback**
- **Problem:** Build something nobody wants or doesn't work for real users
- **Solution:** Show secretary the dashboard early (Phase 1), get feedback
- **When:** After Phase 1, do a quick demo to 1-2 members

**10. Not documenting as you go**
- **Problem:** Forget how things work by Phase 5
- **Solution:** Write README notes during development, not after
- **When:** Add to docs every time you make a decision

**11. Overengineering early phases**
- **Problem:** Spend 20 hours on perfect database schema, never finish Phase 1
- **Solution:** Build minimum viable version first, refine later
- **Check:** Does this feature need to be perfect for MVP?

**12. Neglecting error handling**
- **Problem:** App crashes when Brevo is down or file upload fails
- **Solution:** Add try/catch blocks and user-friendly error messages
- **When:** Add basic error handling as you code, comprehensive review in Phase 5

### User Experience Pitfalls

**13. Assuming users will read instructions**
- **Problem:** Secretary doesn't understand how to use dashboard
- **Solution:** Make UI self-explanatory, add tooltips/hints
- **Check:** Can someone use it without reading a manual?

**14. Making touch targets too small**
- **Problem:** Users mis-tap buttons on phone
- **Solution:** Minimum 44px touch targets, add padding
- **Check:** Use browser inspector to measure button sizes

**15. Not optimizing for slow connections**
- **Problem:** App unusable on 3G cellular
- **Solution:** Compress images, minimize requests, show loading states
- **Check:** Test on throttled 3G connection

---

## Appendix: Quick Reference

### Environment Variables Needed
```
DATABASE_URL=postgresql://...
BREVO_API_KEY=SG...
GOOGLE_PLACES_API_KEY=AIza...
ADMIN_PASSWORD_HASH=bcrypt...
SECRET_KEY=random-string...
APP_URL=https://lunch-scheduler.railway.app
```

### Database Backup Command
```bash
pg_dump $DATABASE_URL > backup-$(date +%Y%m%d).sql
```

### Deploy Command
```bash
git push railway main
# or
git push heroku main
```

### Local Development
```bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
flask db upgrade
flask run
```

### Client-Side Image Compression (JavaScript)
```javascript
// Compress image before upload to save bandwidth on mobile
async function compressImage(file, maxWidth = 1920, quality = 0.8) {
  return new Promise((resolve) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const img = new Image();
      img.onload = () => {
        const canvas = document.createElement('canvas');
        let width = img.width;
        let height = img.height;
        
        if (width > maxWidth) {
          height = (height * maxWidth) / width;
          width = maxWidth;
        }
        
        canvas.width = width;
        canvas.height = height;
        
        const ctx = canvas.getContext('2d');
        ctx.drawImage(img, 0, 0, width, height);
        
        canvas.toBlob((blob) => resolve(blob), 'image/jpeg', quality);
      };
      img.src = e.target.result;
    };
    reader.readAsDataURL(file);
  });
}

// Usage in upload form
document.querySelector('input[type="file"]').addEventListener('change', async (e) => {
  const files = Array.from(e.target.files);
  const compressed = await Promise.all(files.map(f => compressImage(f)));
  // Upload compressed blobs instead of original files
});
```

### Thumbnail Generation (Python/Pillow)
```python
from PIL import Image
import os

def create_thumbnail(image_path, thumb_size=(300, 300)):
    """Generate thumbnail from uploaded image"""
    img = Image.open(image_path)
    img.thumbnail(thumb_size, Image.Resampling.LANCZOS)
    
    # Save with _thumb suffix
    base, ext = os.path.splitext(image_path)
    thumb_path = f"{base}_thumb{ext}"
    img.save(thumb_path, quality=85, optimize=True)
    
    return thumb_path
```

---

**Document Version:** 1.0  
**Last Updated:** December 6, 2024  
**Author:** Josh Caellwyn  
**Status:** Ready for Development
