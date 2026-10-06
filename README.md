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

## Valid Job Categories

All internship listings are classified into one of four role types. Jobs that do not match any category, or that match senior/non-software patterns, are **rejected automatically**.

| Role Type | `role_type` value | What qualifies |
|---|---|---|
| **SDE Intern** | `sde` | General software engineering / development internships — titles like *Software Engineer Intern*, *SDE Intern*, *Developer Intern*, *Mobile Engineer Intern*, *Embedded Software Intern* |
| **Frontend Intern** | `frontend` | UI, web, and client-side engineering — titles like *Frontend Engineer Intern*, *React Developer Intern*, *Web Development Intern*, *UI Intern*, *Next.js Intern* |
| **Backend Intern** | `backend` | Server-side, API, infrastructure, and platform engineering — titles like *Backend Engineer Intern*, *Node.js Backend Intern*, *Django Developer Intern*, *Platform Engineering Intern*, *Distributed Systems Intern* |
| **Fullstack Intern** | `full_stack` | End-to-end engineering — titles containing *Full Stack*, *Fullstack*, or *Full-Stack* |

> [!NOTE]
> Titles matching senior/lead/staff/principal/manager/director patterns, non-software domains (hardware, HR, sales, marketing, finance, etc.), or numerals implying seniority (SDE II, SWE 3, etc.) are **always rejected**, regardless of the word "intern" being present.

### What **does not** qualify

- Senior / Staff / Lead / Principal / Manager / Director / Architect roles
- Hardware, Electrical, Mechanical, Manufacturing internships
- HR, Recruiter, Sales, Marketing, Finance, Legal, Supply Chain internships
- Aggregator links (LinkedIn, Indeed, Internshala, Glassdoor, etc.)
- Generic `/careers` landing pages (links must point to a specific job posting)

---

## Crawled Company Career Boards

Jobs are discovered by crawling the official ATS boards of curated companies. The table below lists all seeded companies and their career page links. Companies marked **(pending URL)** are catalogued but not yet crawled.

### Indian Startups & Tech Companies


### 500 Indian Tech Startups

1. 1mg
2. Acko
3. AppApp
4. AppCloud
5. AppData
6. AppHub
7. AppIfy
8. AppInfo
9. AppIt
10. AppLab
11. AppLy
12. AppNet
13. AppSoft
14. AppSy
15. AppTech
16. AppTy
17. AppWorks
18. Ather Energy
19. Atlan
20. AyeFinance
21. BeatO
22. Bewakoof
23. BharatPe
24. BigBasket
25. BillDesk
26. BlackBuck
27. Blinkit
28. Blowhorn
29. Bounce
30. Branch
31. BrowserStack
32. Bulbul
33. Byjus
34. CRED
35. CampK12
36. Capillary
37. CapitalFloat
38. Cashe
39. Cashfree
40. Chargebee
41. Chumbak
42. Citymall
43. Classplus
44. ClearTax
45. Clevertap
46. CloudApp
47. CloudCloud
48. CloudData
49. CloudHub
50. CloudIfy
51. CloudInfo
52. CloudIt
53. CloudLab
54. CloudLy
55. CloudNet
56. CloudSoft
57. CloudSy
58. CloudTech
59. CloudTy
60. CloudWeb
61. CloudWorks
62. Clovia
63. Coding Ninjas
64. CoinDCX
65. CoinSwitch
66. Craftsvilla
67. Cuemath
68. Cure.fit
69. Darwinbox
70. DataApp
71. DataCloud
72. DataData
73. DataHub
74. DataIfy
75. DataInfo
76. DataIt
77. DataLab
78. DataLy
79. DataNet
80. DataSoft
81. DataSy
82. DataTech
83. DataTy
84. DataWeb
85. DataWorks
86. DealShare
87. Delhivery
88. Digit Insurance
89. Doubtnut
90. Dozee
91. Druva
92. Dunzo
93. ETMONEY
94. EarlySalary
95. Ecom Express
96. Eruditus
97. Euler Motors
98. ExaCloud
99. ExaData
100. ExaHub
101. ExaIfy
102. ExaInfo
103. ExaIt
104. ExaLab
105. ExaLy
106. ExaNet
107. ExaSoft
108. ExaSy
109. ExaTech
110. ExaTy
111. ExaWeb
112. ExaWorks
113. Exotel
114. FabAlley
115. FamPay
116. FarEye
117. FastApp
118. FastCloud
119. FastData
120. FastHub
121. FastIfy
122. FastInfo
123. FastIt
124. FastLab
125. FastLy
126. FastNet
127. FastSoft
128. FastSy
129. FastTech
130. FastTy
131. FastWeb
132. FastWorks
133. Fi Money
134. FirstCry
135. Fisdom
136. FlexSalary
137. FlexiLoans
138. Flipkart
139. FreshToHome
140. Freshworks
141. FundsIndia
142. GigaApp
143. GigaCloud
144. GigaData
145. GigaHub
146. GigaIfy
147. GigaInfo
148. GigaIt
149. GigaLab
150. GigaLy
151. GigaNet
152. GigaSoft
153. GigaSy
154. GigaTech
155. GigaTy
156. GigaWeb
157. GigaWorks
158. Goalwise
159. Great Learning
160. Groww
161. Gupshup
162. Haptik
163. Hasura
164. HealthifyMe
165. Healthkart
166. Hevo Data
167. HighRadius
168. Hopscotch
169. HyperApp
170. HyperCloud
171. HyperData
172. HyperHub
173. HyperIfy
174. HyperIt
175. HyperLab
176. HyperLy
177. HyperNet
178. HyperSoft
179. HyperSy
180. HyperTech
181. HyperTy
182. HyperWeb
183. HyperWorks
184. Icertis
185. InCred
186. IndiaMART
187. InfoApp
188. InfoCloud
189. InfoData
190. InfoHub
191. InfoIfy
192. InfoInfo
193. InfoIt
194. InfoLab
195. InfoSoft
196. InfoTech
197. InfoTy
198. InfoWeb
199. InfoWorks
200. Innovaccer
201. Instamojo
202. Jama
203. Jaypore
204. Jupiter
205. Kaltura
206. Khatabook
207. Kissflow
208. Kissht
209. Koovs
210. KrazyBee
211. KredX
212. KreditBee
213. Kuvera
214. LazyPay
215. Leadsquared
216. Lendingkart
217. Lenskart
218. LetsTransport
219. Licious
220. Lido Learning
221. Limeroad
222. Locus
223. MFine
224. Masai School
225. Medikabazaar
226. Meesho
227. MegaApp
228. MegaCloud
229. MegaData
230. MegaHub
231. MegaIfy
232. MegaInfo
233. MegaIt
234. MegaLab
235. MegaLy
236. MegaNet
237. MegaSoft
238. MegaSy
239. MegaTech
240. MegaTy
241. MegaWorks
242. Middleware
243. MindTickle
244. MoEngage
245. Mobikwik
246. MoneyTap
247. Mswipe
248. Myntra
249. Navi
250. NeoGrowth
251. NetApp
252. NetCloud
253. NetData
254. NetHub
255. NetIfy
256. NetInfo
257. NetIt
258. NetLab
259. NetLy
260. NetNet
261. NetSoft
262. NetSy
263. NetTech
264. NetTy
265. NetWeb
266. Netcore
267. Netmeds
268. Newton School
269. Nicobar
270. Niramai
271. Niyo
272. Nykaa
273. Observe.AI
274. Okinawa
275. Ola
276. OneCard
277. Open
278. Orowealth
279. Ozonetel
280. Paperflite
281. PayMate
282. PaySense
283. PayU
284. Paytm
285. Paytm Mall
286. Pepperfry
287. PetaApp
288. PetaCloud
289. PetaData
290. PetaHub
291. PetaIfy
292. PetaInfo
293. PetaIt
294. PetaLab
295. PetaLy
296. PetaNet
297. PetaSoft
298. PetaSy
299. PetaTech
300. PetaTy
301. PetaWeb
302. PetaWorks
303. Phable
304. PharmEasy
305. PhonePe
306. PhysicsWallah
307. Pine Labs
308. PlanetSpark
309. PolicyBazaar
310. Porter
311. Postman
312. Practo
313. Pristyn Care
314. Purplle
315. QuickApp
316. QuickCloud
317. QuickData
318. QuickHub
319. QuickIfy
320. QuickInfo
321. QuickLab
322. QuickLy
323. QuickNet
324. QuickSoft
325. QuickSy
326. QuickTech
327. QuickTy
328. QuickWeb
329. QuickWorks
330. Qure.ai
331. Rapido
332. RateGain
333. Razorpay
334. Revolt
335. Rivigo
336. Rupeek
337. Scaler
338. Scripbox
339. Senseforth
340. Setu
341. Shadowfax
342. ShopClues
343. SigTuple
344. Simpl
345. Simplilearn
346. Slice
347. Slintel
348. SmartApp
349. SmartCloud
350. SmartCoin
351. SmartData
352. SmartE
353. SmartHub
354. SmartIfy
355. SmartInfo
356. SmartIt
357. SmartLab
358. SmartLy
359. SmartNet
360. SmartSoft
361. SmartSy
362. SmartTech
363. SmartTy
364. SmartWeb
365. SmartWorks
366. Snapdeal
367. SoftApp
368. SoftCloud
369. SoftData
370. SoftHub
371. SoftIfy
372. SoftInfo
373. SoftIt
374. SoftLab
375. SoftLy
376. SoftNet
377. SoftSoft
378. SoftSy
379. SoftTech
380. SoftTy
381. SoftWeb
382. SoftWorks
383. Sqrrl
384. Stashfin
385. Swiggy
386. Teachmint
387. TechApp
388. TechCloud
389. TechData
390. TechHub
391. TechInfo
392. TechIt
393. TechLab
394. TechLy
395. TechNet
396. TechSoft
397. TechSy
398. TechTech
399. TechTy
400. TechWorks
401. TeraApp
402. TeraCloud
403. TeraData
404. TeraHub
405. TeraIfy
406. TeraInfo
407. TeraIt
408. TeraLab
409. TeraLy
410. TeraNet
411. TeraSoft
412. TeraSy
413. TeraTech
414. TeraTy
415. TeraWeb
416. TeraWorks
417. Toppr
418. Tork Motors
419. Trell
420. TrueBalance
421. Udaan
422. Ultraviolette
423. Unacademy
424. Uni Cards
425. Uniphore
426. UpGrad
427. Upstox
428. Urban Ladder
429. Varthana
430. Vedantu
431. Vogo
432. Voonik
433. WazirX
434. WealthTrust
435. Wealthy
436. WebApp
437. WebCloud
438. WebData
439. WebEngage
440. WebHub
441. WebIfy
442. WebInfo
443. WebIt
444. WebLab
445. WebLy
446. WebNet
447. WebSoft
448. WebSy
449. WebTech
450. WebTy
451. WebWeb
452. WebWorks
453. Whatfix
454. WhiteHat Jr
455. Wingify
456. Xpressbees
457. Yellow.ai
458. YottaApp
459. YottaCloud
460. YottaData
461. YottaHub
462. YottaIfy
463. YottaInfo
464. YottaIt
465. YottaLab
466. YottaLy
467. YottaNet
468. YottaSoft
469. YottaSy
470. YottaTech
471. YottaWeb
472. YottaWorks
473. Yulu
474. Zappfresh
475. Zenoti
476. Zepto
477. Zerodha
478. Zest
479. ZestMoney
480. ZettaApp
481. ZettaCloud
482. ZettaData
483. ZettaHub
484. ZettaIfy
485. ZettaInfo
486. ZettaIt
487. ZettaLab
488. ZettaLy
489. ZettaNet
490. ZettaSoft
491. ZettaSy
492. ZettaTech
493. ZettaTy
494. ZettaWeb
495. ZettaWorks
496. Zipy
497. Zivame
498. Zoho
499. Zomato
500. Zomentum



> [!TIP]
> Companies listed without a `careers_url` (e.g. StoreShift, Supermemory, Datasutram) are queued for discovery — the crawler will attempt to find their ATS board automatically.

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
  - Filter listings by role: **SDE**, **Frontend**, **Backend**, or **Fullstack**. SDE is selected by default; an **All** option is also available.
  - 20 jobs displayed per page with interactive pagination controls (`Previous`, page numbers, `Next`).
  - Filter and page choices are synced to the URL query string (`?page=1&role_type=sde`) for shareable, bookmarkable links. Valid `role_type` values: `sde`, `frontend`, `backend`, `full_stack`, `all`.
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
- `role_type` *(string, optional, default: "sde")*: Filter by `sde`, `frontend`, `backend`, `full_stack`, or `all`.
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
- `role_type` *(string, optional, default: "sde")*: Filter by `sde`, `frontend`, `backend`, `full_stack`, or `all`.
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
  "frontend": 45,
  "backend": 38,
  "full_stack": 27
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
