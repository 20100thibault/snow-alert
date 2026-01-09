# Product Requirements Document: Quebec City Alerts - Unified Subscription System

## Executive Summary

Evolve Snow Alert into a unified **Quebec City Alerts** platform where users enter their postal code and email once, then select which alerts they want to receive:
- **Option 1:** Snow Removal Alerts
- **Option 2:** Trash & Recycling Reminders

---

## Research Findings

### Data Availability

**Snow Removal Data**
- Already implemented via Quebec City open data API
- Real-time snow removal operations available

**Waste Collection Data**
- **Quebec City Info-Collecte Service:** https://www.ville.quebec.qc.ca/services/info-collecte/
- **No public API available** - uses server-side ASP.NET WebForms
- Requires web scraping to obtain schedule data
- Schedule lookup by postal code or address

**Collection Schedule Rules (2025-2026)**
- Winter (Oct 6 - Mar 27): Garbage every 2 weeks, alternating with recycling
- Summer: Garbage weekly, recycling every 2 weeks
- Exceptions: La Cité-Limoilou, Montmorency (Beauport), rue Maguire

### Data Acquisition Strategy

1. **Snow Removal:** Continue using existing Quebec City API
2. **Waste Collection:** Scrape Info-Collecte page, cache results

---

## Feature Requirements

### User Stories

1. As a user, I want to enter my postal code and email once
2. As a user, I want to choose which alerts I receive (snow, trash, recycling)
3. As a user, I want to update my preferences without re-entering my info
4. As a user, I want to see my current subscription status
5. As a user, I want to unsubscribe from all or specific alerts

### Unified Subscription Model

```
User enters:
├── Postal Code (required)
├── Email (required)
└── Alert Preferences:
    ├── ☑ Snow Removal Alerts
    ├── ☑ Garbage Reminders
    └── ☑ Recycling Reminders
```

### Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-01 | Single form for postal code + email + preferences | High |
| FR-02 | Checkbox selection for each alert type | High |
| FR-03 | Unified user record with alert preferences | High |
| FR-04 | Scrape Info-Collecte for waste schedules | High |
| FR-05 | Send snow alerts when operations detected | High |
| FR-06 | Send waste reminders at 6 PM day before collection | High |
| FR-07 | Allow preference updates without re-subscribing | Medium |
| FR-08 | Display next collection/operation dates | Medium |
| FR-09 | Single unsubscribe flow for all alerts | Medium |
| FR-10 | Handle seasonal schedule changes | Medium |

### Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| NFR-01 | Scraper shall respect rate limits (max 1 request per 10 seconds) |
| NFR-02 | Reminders sent within 5 minutes of scheduled time |
| NFR-03 | Graceful degradation if scraping fails |
| NFR-04 | Collection data cached for 24 hours minimum |

---

## Technical Architecture

### Database Schema Changes

**Updated users table:**
```sql
-- Modify existing users table to add preferences
ALTER TABLE users ADD COLUMN snow_alerts_enabled BOOLEAN DEFAULT TRUE;
ALTER TABLE users ADD COLUMN garbage_alerts_enabled BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN recycling_alerts_enabled BOOLEAN DEFAULT FALSE;
```

**New tables:**
```sql
-- Waste collection zones
CREATE TABLE waste_zones (
    id INTEGER PRIMARY KEY,
    zone_code TEXT UNIQUE NOT NULL,
    garbage_day TEXT NOT NULL,        -- 'monday', 'tuesday', etc.
    recycling_week TEXT NOT NULL,     -- 'odd' or 'even'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Link users to waste zones
ALTER TABLE users ADD COLUMN waste_zone_id INTEGER REFERENCES waste_zones(id);

-- Track sent reminders
CREATE TABLE reminders_sent (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    reminder_type TEXT NOT NULL,      -- 'snow', 'garbage', 'recycling'
    reference_date DATE NOT NULL,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, reminder_type, reference_date)
);
```

### New/Modified Files

```
app/
├── database.py          # Updated with new schema + preference functions
├── routes.py            # Updated subscribe endpoint with preferences
├── waste_scraper.py     # NEW: Scrapes Info-Collecte website
├── waste_service.py     # NEW: Waste reminder business logic
├── scheduler.py         # Updated to include waste reminder job
├── email_service.py     # Updated with waste email templates
templates/
└── index.html           # Unified subscription UI
```

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/subscribe` | Subscribe with postal code, email, and preferences |
| POST | `/unsubscribe` | Unsubscribe from all alerts |
| PUT | `/preferences` | Update alert preferences |
| GET | `/status/{email}` | Get subscription status and preferences |
| GET | `/schedule/{postal_code}` | Get all schedules (snow + waste) |

### Request/Response Examples

**POST /subscribe**
```json
{
  "postal_code": "G1R 2K8",
  "email": "user@example.com",
  "preferences": {
    "snow_alerts": true,
    "garbage_alerts": true,
    "recycling_alerts": true
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "Subscribed successfully",
  "next_events": {
    "snow_removal": null,
    "garbage": "2026-01-13",
    "recycling": "2026-01-20"
  }
}
```

---

## UI/UX Design

### Unified Homepage Design

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│              ❄️ Quebec City Alerts                      │
│                                                         │
│    Stay informed about snow removal and waste           │
│    collection in your neighborhood.                     │
│                                                         │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  Subscribe to Alerts                                    │
│                                                         │
│  POSTAL CODE                                            │
│  ┌─────────────────────────────────────────────────┐   │
│  │ G1R 2K8                                         │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  EMAIL ADDRESS                                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │ you@example.com                                 │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  ─────────────────────────────────────────────────────  │
│                                                         │
│  SELECT YOUR ALERTS                                     │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │ ❄️  Snow Removal                           [✓] │   │
│  │     Get notified when snow removal is          │   │
│  │     scheduled for your street                  │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │ 🗑️  Garbage Collection                     [✓] │   │
│  │     Reminder at 6 PM the day before            │   │
│  │     garbage pickup                             │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │ ♻️  Recycling Collection                   [✓] │   │
│  │     Reminder at 6 PM the day before            │   │
│  │     recycling pickup                           │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │           Subscribe to Selected Alerts          │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  📅 Your Schedule (shown after subscription)           │
│                                                         │
│  • Next garbage pickup: Monday, January 13             │
│  • Next recycling pickup: Monday, January 20           │
│  • Snow removal: No active operations                  │
│                                                         │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  Already subscribed? Manage or unsubscribe below.      │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │ you@example.com                                 │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  [ Manage Preferences ]     [ Unsubscribe ]            │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Email Templates

**Snow Alert Email** (existing, unchanged)

**Garbage Reminder Email:**
```
Subject: Reminder: Garbage pickup tomorrow

Hi,

This is a reminder that garbage collection is scheduled for
tomorrow (Tuesday, January 14) near your location (G1R 2K8).

Please have your garbage bin at the curb by 7:00 AM.

---
Quebec City Alerts
Manage preferences: [link]
Unsubscribe: [link]
```

**Recycling Reminder Email:**
```
Subject: Reminder: Recycling pickup tomorrow

Hi,

This is a reminder that recycling collection is scheduled for
tomorrow (Tuesday, January 21) near your location (G1R 2K8).

Please have your recycling bin at the curb by 7:00 AM.

---
Quebec City Alerts
Manage preferences: [link]
Unsubscribe: [link]
```

---

## Implementation Phases

### Phase 1: Database & Schema Updates
- Add preference columns to users table
- Create waste_zones table
- Create reminders_sent table
- Update database functions

### Phase 2: Waste Scraper
- Implement Info-Collecte scraper
- Parse HTML for schedule data
- Cache schedules in database
- Add rate limiting

### Phase 3: Unified Subscription API
- Update /subscribe endpoint with preferences
- Create /preferences endpoint
- Update /unsubscribe endpoint
- Create /status endpoint

### Phase 4: Waste Reminder System
- Implement collection day calculation
- Create waste email templates
- Add waste scheduler job
- Implement duplicate prevention

### Phase 5: UI Overhaul
- Rename to "Quebec City Alerts"
- Create unified subscription form
- Add alert type selection cards
- Display schedule after subscription

### Phase 6: Testing & Deployment
- End-to-end tests
- Scraper resilience tests
- Update deployment config
- Deploy and monitor

---

## Migration Strategy

### Existing Users

All existing snow alert subscribers will:
1. Retain their subscription
2. Have `snow_alerts_enabled = TRUE` by default
3. Have `garbage_alerts_enabled = FALSE` by default
4. Have `recycling_alerts_enabled = FALSE` by default

No action required from existing users.

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Info-Collecte website changes | Scraper breaks | Monitor failures, robust parsing, fallback to cached data |
| City blocks scraping | Feature unusable | Contact city, implement respectful rate limiting |
| Schedule accuracy | Wrong reminders | Weekly refresh, user feedback mechanism |
| Migration breaks existing users | User complaints | Thorough testing, gradual rollout |

---

## Success Metrics

- Percentage of users enabling multiple alert types
- Email open rates by alert type
- User retention rate
- Reduction in missed pickups (survey)

---

## Sources

- [Quebec City Info-Collecte](https://www.ville.quebec.qc.ca/services/info-collecte/)
- [Quebec City Waste Collection](https://www.ville.quebec.qc.ca/citoyens/environnement/matieres-residuelles/collecte/)
- [Données Québec](https://www.donneesquebec.ca/)
