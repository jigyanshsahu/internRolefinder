# InternRoleFinder

An automated directory of verified software internship application links, categorized into **SDE Intern**, **Frontend Intern**, **Backend Intern**, and **Fullstack Intern** roles. Non-software and senior roles are rejected. Listings link directly to employer applications and prioritize verified startup boards.

---

## Features

- **Focused Software Intern Categories**:
  - **SDE Intern**: General software engineering and development internships.
  - **Frontend Intern**: UI, frontend, and web engineering internships.
  - **Backend Intern**: Backend, infrastructure, API, and systems internships.
  - **Fullstack Intern**: Full-stack engineering internships.
- **Direct Employer ATS Links**:
  - Ingestion directly from official employer portals (Greenhouse, Lever, Ashby, Keka, Freshteam, Zoho Recruit, SmartRecruiters, Workable, Recruitee, Workday, and Schema.org JobPosting).
  - No aggregators (LinkedIn, Indeed, Internshala, etc. are rejected).
- **Workplace Filters**:
  - Default view displays all verified locations (on-site, hybrid, remote).
  - One-click toggle to filter for remote positions.
- **Application Tracker (`/applied`)**:
  - Keep track of applied roles and interview stages directly in the app.

---

## Architecture & Tech Stack

| Component | Technology | Description |
|---|---|---|
| **Frontend** | Next.js 15 (App Router), React 19, TypeScript, Tailwind CSS | Responsive UI with real-time role filtering, pagination (20 jobs/page), URL state synchronization, and application tracking |
| **Backend API** | FastAPI, SQLAlchemy 2.0, Pydantic Settings, HTTPX, BeautifulSoup4 | RESTful API with automated schema migration, health checks, and pagination |
| **Database** | PostgreSQL 16 | Relational storage for active jobs and discovered startup ATS boards |
| **Task Queue & Scheduler** | Celery 5.4, Celery Beat, Redis 7 | Scheduled crawling, periodic link verification, and AI startup discovery |
| **Containerization** | Docker, Docker Compose | Multi-container setup for one-command deployment |

---

## Quickstart (Docker Compose)

### 1. Configure Environment

Copy the example environment configuration:

```bash
cp .env.example .env
```

*(Optional)* To enable automated discovery of Indian startup career boards, set `GEMINI_API_KEY` in `.env`. Leave it blank if you only want to use the public company catalog.

### 2. Launch the Application

```bash
docker compose up --build
```

### 3. Access Services

- **Web Application**: [http://localhost:3000](http://localhost:3000)
- **Applied Internships**: [http://localhost:3000/applied](http://localhost:3000/applied)
- **Interactive API Docs (Swagger UI)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **API Health Check**: [http://localhost:8000/api/health](http://localhost:8000/api/health)

On startup, database tables and enum values are created automatically, and an initial discovery/crawl task is triggered.

---

## User Interface & Navigation

- **Browse Roles (`/`)**:
  - Filter listings by role: **SDE** or **AI**. SDE is selected by default; there is no All category.
  - 20 jobs displayed per page with interactive pagination controls (`Previous`, page numbers, `Next`).
  - Filter and page choices are synced to the URL query string (`?page=1&role_type=sde`) for shareable, bookmarkable links.
  - Click **Apply ↗** to open the direct application link in a new tab.
  - Click **Mark applied** to track the position locally.
- **Applied Internships (`/applied`)**:
  - View all marked positions in one place.
  - Remove applied positions anytime with the **Remove** button.

---

## Environment Variables Reference

| Variable | Default | Description |
|---|---|---|
| `POSTGRES_DB` | `internrolefinder` | PostgreSQL database name |
| `POSTGRES_USER` | `internrolefinder` | PostgreSQL username |
| `POSTGRES_PASSWORD` | `change-me` | PostgreSQL password |
| `DATABASE_URL` | `postgresql+psycopg://internrolefinder:change-me@db:5432/internrolefinder` | PostgreSQL database connection string |
| `REDIS_URL` | `redis://redis:6379/0` | Redis broker and backend URL |
| `FRONTEND_ORIGIN` | `http://localhost:3000` | Allowed CORS origin for the FastAPI backend |
| `PUBLIC_ATS_COMPANY_CATALOG_URL` | `https://raw.githubusercontent.com/ConorsCode/open-jobs-data/main/companies.json` | Remote JSON catalog of company ATS boards |
| `GEMINI_API_KEY` | *(empty)* | Optional key for the legacy manual Gemini discovery task; curated source discovery does not require it |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Model used only by the legacy manual Gemini discovery task |
| `STARTUP_DISCOVERY_LIMIT` | `40` | Maximum candidates used only by the legacy manual Gemini discovery task |
| `STARTUP_DISCOVERY_INTERVAL_HOURS` | `168` | Interval between curated company-source discovery cycles (default: 7 days) |
| `CRAWL_INTERVAL_MINUTES` | `360` | Interval between job-board crawl cycles (default: 6 hours) |
| `VERIFY_INTERVAL_MINUTES` | `180` | Interval between link health checks (default: 3 hours) |
| `VERIFICATION_MAX_AGE_HOURS` | `24` | Maximum hours a job is retained without re-verification |

---

## API Endpoints

### `GET /api/jobs`
Retrieve software developer internships that were confirmed active within the configured verification window. Remote roles are filtered by default; listings older than 24 hours are omitted by default.

**Query Parameters:**
- `role_type` *(string, optional, default: "sde")*: Filter by `sde` or `ai`.
- `remote_only` *(bool, optional, default: true)*: Filter to remote opportunities only.
- `skills` *(string, optional)*: Comma-separated skill keywords to match (e.g. `python,react,pytorch`).
- `location_eligibility` *(string, optional)*: Filter by location preference (`any_remote`, `india`, `international`).
- `internship_dates` *(string, optional)*: Filter by target term (`summer_2026`, `immediate`, `fall_2026`, `winter_2027`).
- `sort_by` *(string, optional, default: "priority")*: Sort order (`priority`, `fit`, `freshness`).
- `page` *(int, optional, default: 1)*: 1-indexed page number.
- `page_size` *(int, optional, default: 100, max: 100)*: Items per page.

**Response Schema (`JobPageOut`):**
```json
{
  "items": [
    {
      "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "title": "Software Engineer Intern",
      "company": "Example Company",
      "location": "Bengaluru, India",
      "country": "India",
      "is_remote": true,
      "role_type": "sde",
      "apply_url": "https://boards.greenhouse.io/exampleai/jobs/12345",
      "first_seen_at": "2026-10-01T12:00:00Z",
      "last_checked_at": "2026-10-01T12:30:00Z",
      "fit_score": 95,
      "matched_skills": ["python", "react"]
    }
  ],
  "page": 1,
  "page_size": 20,
  "total": 56,
  "total_pages": 3
}
```

### `GET /api/jobs/alerts`
Returns newly verified matching roles discovered within a recent time window (default: past 24 hours), enabling fast notification and early applications.

**Query Parameters:**
- `role_type` *(string, optional, default: "sde")*: Filter by `sde` or `ai`.
- `remote_only` *(bool, optional, default: true)*: Remote-only alert toggle.
- `hours` *(int, optional, default: 24, min: 1, max: 168)*: Hours window.

**Response Schema (`JobAlertsOut`):**
```json
{
  "items": [...],
  "total_new": 6,
  "last_checked_at": "2026-10-02T12:00:00Z"
}
```

### `GET /api/companies/seeds`
View the curated company source registry, including official website/careers URLs and the latest crawl status. Names without a verified official website remain listed for review but are not crawled.

Each source status is one of `queued`, `board_found`, `career_page_found`, `no_supported_careers`, or `needs_official_url`.

### `GET /api/jobs/summary`
Returns counts of active verified listings by role type.

**Response Schema (`SummaryOut`):**
```json
{
  "sde": 140,
  "ai": 35
}
```

### `GET /api/health`
Basic health status check.
```json
{
  "status": "ok"
}
```

---

## Local Development (Without Docker)

### Prerequisites
- Python 3.11+
- Node.js 18+ and npm
- Running PostgreSQL 16 instance
- Running Redis 7 instance

### 1. Backend

```bash
cd backend

# Create and activate virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run FastAPI API server
uvicorn app.main:app --reload --port 8000

# Run Celery worker (in a separate terminal)
celery -A app.worker.celery_app worker --loglevel=info

# Run Celery beat scheduler (in a separate terminal)
celery -A app.worker.celery_app beat --loglevel=info
```

### 2. Frontend

```bash
cd frontend

# Install dependencies
npm install

# Run Next.js development server
npm run dev
```

Frontend runs on `http://localhost:3000` and proxies requests to `http://localhost:8000`.

---

## Testing

Execute the test suite inside the API container:

```bash
docker compose run --rm api pytest
```

Or locally with a virtual environment:

```bash
cd backend
pytest
```

### Test Suite Overview:
- `backend/tests/test_classifier.py`: Validates strict software internship/fresher classification, SDE/AI grouping, and non-software/senior exclusions.
- `backend/tests/test_urls.py`: Tests ATS response parsing across Greenhouse, Lever, Ashby, SmartRecruiters, Workable, and Recruitee; verifies location matching for Indian cities; and tests Gemini response sanitization.
- `backend/tests/test_jobs_api.py`: Tests pagination math, total page clamping, database query construction, and priority sorting.

---

## Crawler Ethics & Design

- **Direct Application Links**: Only stores canonical application links directly pointing to official ATS boards.
- **Privacy & Hygiene**: Removes ad-tracking and referral query parameters (`utm_*`, `gh_src`, etc.) while retaining job identifiers (`gh_jid`, posting tokens).
- **Public Feeds Only**: Ingests exclusively from open, public job boards and official career pages. Makes no attempts to bypass authentication, CAPTCHAs, or access controls.
- **Graceful Fault Tolerance**: Skips unreachable or rate-limited endpoints without interrupting active crawls. Existing listings remain cached and available in PostgreSQL.
