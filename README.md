# InternRoleFinder

An automated directory of currently verified internship and fresher application links, grouped into SDE, AI, and Other roles.

## Start locally

1. Optionally copy `.env.example` to `.env` to configure a search provider or change defaults.
2. Run `docker compose up --build`.
3. Open `http://localhost:3000`. The API docs are at `http://localhost:8000/docs`.

The API creates its tables on startup. The background worker loads an automatically refreshed public company-board catalog, then fetches current jobs from supported public ATS feeds. No account, API key, or billing setup is required.

## Free public ATS discovery

The crawler currently supports these public job-board feeds, filtering each employer's published roles locally for internships and explicit fresher, graduate, or entry-level roles:

- Greenhouse: `boards-api.greenhouse.io`
- Lever: `api.lever.co`
- Ashby: `api.ashbyhq.com`
- SmartRecruiters: `api.smartrecruiters.com`
- Workable: `www.workable.com/api/accounts`
- Recruitee: `{company}.recruitee.com/api/offers`

The default catalog URL is in `.env.example`. It is a public list of company boards that refreshes independently; the crawler checks those boards every six hours. The catalog is global and has no country metadata, so this is not a complete directory of Indian startups. India-based postings are included when a listed company publishes them through a supported ATS. The application verifies direct application URLs before showing a listing and removes expired ones on the scheduled recheck.

To discover additional Indian startup boards, set `GEMINI_API_KEY` in your local `.env` file. Gemini suggests company names and official websites; the crawler visits those websites and saves a company only when its own homepage or careers page links to a supported ATS board. New board discovery runs at startup and every 168 hours by default, then triggers a job crawl. Set `GEMINI_API_KEY` to an empty value to disable this optional discovery. The key is passed to the backend as an environment variable and should never be committed.

The job browser displays up to 100 jobs per page. The Celery worker logs warnings and errors by default; change its `--loglevel` in `docker-compose.yml` to `info` when diagnosing crawl activity.

## Commands

```bash
docker compose up --build
docker compose down
docker compose run --rm api pytest
```

## Design

- The crawler stores only minimal job data and canonical direct application links.
- Links are checked at scheduled intervals. Closed/expired links are deleted after validation; temporary failures are retried.
- Only publicly accessible pages are fetched. The crawler does not attempt to bypass logins, CAPTCHAs, robots restrictions, or anti-bot controls.
