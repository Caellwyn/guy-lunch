# PWA Implementation Plan - Tuesday Lunch App

## Overview

This document outlines the implementation plan for Progressive Web App (PWA) features in priority order:

1. **Add to Home Screen** - App icon and standalone mode
2. **Splash Screen** - Branded loading screen
3. **Push Notifications** - Browser-based notifications (deferred - complex)
4. **Offline Capability** - Service worker caching (deferred - low value)

---

## Phase 1: Add to Home Screen (Estimated: 1-2 hours)

### What It Does
- Allows users to "install" the web app to their phone's home screen
- App opens in **standalone mode** (no browser URL bar)
- Displays a custom app icon instead of a favicon

### Requirements

1. **manifest.json** - Web app manifest file that defines:
   - App name and short name
   - Icons (multiple sizes)
   - Theme color and background color
   - Display mode (standalone)
   - Start URL
   - Scope

2. **App Icons** - PNG images in multiple sizes:
   - 72x72 (Android minimum)
   - 96x96
   - 128x128
   - 144x144 (Android recommended)
   - 152x152 (iOS)
   - 192x192 (Android required for PWA)
   - 384x384
   - 512x512 (Android required for splash)

3. **Meta Tags** - Added to base.html:
   - `<link rel="manifest" href="/manifest.json">`
   - `<meta name="theme-color" content="#1e3a8a">`
   - iOS-specific meta tags (Apple doesn't fully support manifest.json)

### Implementation Steps

#### Step 1.1: Create App Icons
- [ ] Design a simple icon (baseball/lunch themed)
  - Option A: Use the stadium blue background with "TL" in gold
  - Option B: Simple baseball or plate icon
  - Option C: Use an AI image generator or free icon
- [ ] Generate all required sizes from a 512x512 master
- [ ] Save to `app/static/img/icons/` folder
- [ ] Create maskable icon version (for Android adaptive icons)

**Test:** Icons exist in correct sizes and look good at small sizes (72px)

#### Step 1.2: Create manifest.json
- [ ] Create `app/static/manifest.json` with all required fields
- [ ] Set `display: "standalone"` for app-like experience
- [ ] Set `start_url: "/"` (or `/member/` for logged-in experience)
- [ ] Set `scope: "/"` to include all app pages
- [ ] Configure theme_color and background_color to match stadium theme

**Test:** `manifest.json` is valid JSON and accessible at `/static/manifest.json`

#### Step 1.3: Add Meta Tags to base.html
- [ ] Add `<link rel="manifest">` pointing to manifest.json
- [ ] Add `<meta name="theme-color">` for browser UI coloring
- [ ] Add iOS-specific meta tags:
  - `<meta name="apple-mobile-web-app-capable" content="yes">`
  - `<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">`
  - `<meta name="apple-mobile-web-app-title" content="Tuesday Lunch">`
  - `<link rel="apple-touch-icon" href="...">` for each icon size

**Test:** Meta tags appear in page source when viewing base.html

#### Step 1.4: Test Add to Home Screen

**Android (Chrome):**
- [ ] Open app in Chrome
- [ ] Tap three-dot menu → "Add to Home Screen" (or "Install app")
- [ ] Verify icon appears on home screen
- [ ] Tap icon → app opens in standalone mode (no URL bar)
- [ ] Navigate within app → stays in standalone mode
- [ ] External links open in browser (not in app)

**iOS (Safari):**
- [ ] Open app in Safari
- [ ] Tap Share button → "Add to Home Screen"
- [ ] Verify icon appears on home screen
- [ ] Tap icon → app opens in standalone mode
- [ ] Note: iOS may show brief Safari UI before going standalone

**Desktop (Chrome):**
- [ ] Open app in Chrome
- [ ] Look for install icon in address bar (or three-dot menu → "Install")
- [ ] Verify app opens as separate window

### Deliverables
- `app/static/manifest.json`
- `app/static/img/icons/` folder with all icon sizes
- Updated `app/templates/base.html` with PWA meta tags

### Rollback Plan
If issues arise, simply remove the manifest link from base.html. The app continues to work as a normal website.

---

## Phase 2: Splash Screen (Estimated: 30 minutes)

### What It Does
- Shows a branded loading screen when launching from home screen
- Displays while the app loads (typically 1-3 seconds)
- Uses the icon and background color from manifest.json

### Requirements

**Android:** Automatically generated from manifest.json if:
- `background_color` is set
- `name` or `short_name` is set
- 512x512 icon is provided
- `display` is `standalone` or `fullscreen`

**iOS:** Requires separate splash screen images (more complex):
- Multiple sizes for different devices (iPhone SE, iPhone 14, iPad, etc.)
- Uses `<link rel="apple-touch-startup-image">`
- iOS splash screen support is limited and quirky

### Implementation Steps

#### Step 2.1: Verify Android Splash Screen
- [ ] Confirm manifest.json has `background_color` set
- [ ] Confirm 512x512 icon exists
- [ ] Test on Android: Install → Close → Reopen from home screen
- [ ] Verify splash screen appears with app name and icon

**Test:** Android splash screen shows stadium blue background with app icon

#### Step 2.2: iOS Splash Screen (Basic)
- [ ] Create a simple splash screen image (1125x2436 for modern iPhones)
- [ ] Add `<link rel="apple-touch-startup-image">` to base.html
- [ ] Test on iOS device

**Note:** Full iOS splash screen support requires many image sizes. For MVP, we can:
- Option A: Create just the most common size (iPhone 12/13/14)
- Option B: Skip iOS splash screen (just shows white briefly)
- Option C: Use a CSS-based splash screen (more complex)

**Test:** iOS shows branded splash (or gracefully falls back to white)

### Deliverables
- Verified Android splash screen works
- (Optional) iOS splash screen image(s)
- Updated base.html with iOS splash link if implemented

---

## Phase 3: Push Notifications (Estimated: 4-6 hours) - DEFERRED

### Why Deferred
- Requires a push notification service (Firebase, OneSignal, or custom)
- Requires HTTPS (already have via Railway)
- Requires service worker (not yet implemented)
- Requires user permission (can be annoying if done wrong)
- Email notifications already work well for this use case

### What It Would Do
- Send notifications to members' phones even when not in the app
- Examples: "You're hosting next week!", "Rate today's lunch"
- Works even when browser is closed (on Android)

### If We Implement Later
1. Set up Firebase Cloud Messaging (FCM) or similar service
2. Create service worker to receive push messages
3. Add "Enable notifications" UI with permission request
4. Store push tokens in database (new field on Member)
5. Send notifications from server via FCM API
6. Handle notification clicks (deep link to relevant page)

### Current Status: NOT IMPLEMENTING
Email works well. Push notifications add complexity without much value for 25 members.

---

## Phase 4: Offline Capability (Estimated: 3-4 hours) - DEFERRED

### Why Deferred
- Members are always at restaurants with connectivity
- No critical use case for offline access
- Adds complexity (cache management, sync conflicts)
- Service worker can cause caching headaches during development

### What It Would Do
- Cache previously viewed pages for offline access
- Cache gallery images for offline viewing
- Queue form submissions when offline, sync when back online

### If We Implement Later
1. Create service worker (`sw.js`)
2. Define caching strategy (cache-first for images, network-first for data)
3. Register service worker in base.html
4. Handle offline detection and UI feedback
5. Implement background sync for form submissions

### Current Status: NOT IMPLEMENTING
Low value for the effort. Connectivity is rarely an issue at lunch restaurants.

---

## Implementation Order

### Now (This Session)
1. **Phase 1: Add to Home Screen** - Full implementation
2. **Phase 2: Splash Screen** - Android auto, basic iOS

### Later (If Requested)
3. Phase 3: Push Notifications
4. Phase 4: Offline Capability

---

## Testing Checklist

### Phase 1: Add to Home Screen
- [ ] manifest.json is valid (use Chrome DevTools → Application → Manifest)
- [ ] All icons load correctly (no 404s in DevTools)
- [ ] Android: Can install to home screen
- [ ] Android: Opens in standalone mode
- [ ] Android: Icon looks correct on home screen
- [ ] iOS: Can add to home screen via Share menu
- [ ] iOS: Opens in standalone mode (or near-standalone)
- [ ] iOS: Icon looks correct on home screen
- [ ] Desktop Chrome: Install option appears

### Phase 2: Splash Screen
- [ ] Android: Splash screen appears on launch from home screen
- [ ] Android: Splash screen shows correct colors and icon
- [ ] iOS: Splash screen appears (if implemented) or gracefully shows white

---

## Files to Create/Modify

### New Files
- `app/static/manifest.json`
- `app/static/img/icons/icon-72x72.png`
- `app/static/img/icons/icon-96x96.png`
- `app/static/img/icons/icon-128x128.png`
- `app/static/img/icons/icon-144x144.png`
- `app/static/img/icons/icon-152x152.png`
- `app/static/img/icons/icon-192x192.png`
- `app/static/img/icons/icon-384x384.png`
- `app/static/img/icons/icon-512x512.png`
- `app/static/img/icons/icon-maskable-192x192.png` (for Android adaptive)
- `app/static/img/icons/icon-maskable-512x512.png`
- (Optional) `app/static/img/splash/` folder for iOS splash screens

### Modified Files
- `app/templates/base.html` - Add PWA meta tags

---

## Design Decisions

### Icon Design
**Recommendation:** Simple "TL" monogram on stadium blue background
- Readable at small sizes
- Matches the app's brand (Tuesday Lunch)
- Uses existing stadium-blue color (#1e3a8a)
- Gold text (#fbbf24) for contrast

### Start URL
**Options:**
- `/` - Home page (requires login)
- `/member/` - Member dashboard (auto-redirects to login if needed)

**Recommendation:** Use `/member/` as start URL so returning users land on their dashboard.

### Theme Color
**Use:** Stadium blue `#1e3a8a`
- Matches the nav bar
- Creates consistent brand experience
- Browser UI will tint to this color

### Display Mode
**Use:** `standalone`
- Removes browser UI (URL bar, navigation buttons)
- App feels native
- Alternative `fullscreen` hides status bar too (too aggressive)

---

## Revision History
- v1.0 (Dec 2024) - Initial plan

