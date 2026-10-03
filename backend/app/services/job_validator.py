import asyncio
import logging
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qs, urlparse, urlsplit, urlunsplit
import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger("job_validator")
logger.setLevel(logging.WARNING)


@dataclass
class JobValidationResult:
    is_valid: bool
    status: str  # "active", "stale", "expired", "generic_careers", "invalid_url", "http_error", "not_individual_job"
    original_url: str
    final_url: str | None = None
    http_status: int | None = None
    is_individual_job: bool = False
    is_active: bool = False
    source: str | None = None
    source_job_id: str | None = None
    rejection_reason: str | None = None


# Generic career path segments that signify a company careers root/directory, NOT an individual posting
GENERIC_CAREERS_PATHS = {
    "",
    "/",
    "/home",
    "/index.html",
    "/index.php",
    "/careers",
    "/careers/",
    "/career",
    "/career/",
    "/jobs",
    "/jobs/",
    "/job-openings",
    "/job-openings/",
    "/openings",
    "/openings/",
    "/positions",
    "/positions/",
    "/opportunities",
    "/opportunities/",
    "/work-with-us",
    "/work-with-us/",
    "/join-us",
    "/join-us/",
    "/join",
    "/join/",
    "/careers/search",
    "/careers/search/",
    "/careers/all",
    "/careers/all/",
    "/careers/explore",
    "/careers/explore/",
    "/jobs/search",
    "/jobs/search/",
    "/jobs/all",
    "/jobs/all/",
    "/jobs/explore",
    "/jobs/explore/",
    "/about/careers",
    "/about/careers/",
    "/hiring",
    "/hiring/",
    "/join-our-team",
    "/join-our-team/",
}

GENERIC_PATH_KEYWORDS = {
    "hiring",
    "search",
    "all",
    "explore",
    "filter",
    "department",
    "departments",
    "teams",
    "team",
    "locations",
    "location",
    "apply",
    "login",
    "home",
    "about",
    "overview",
    "students",
    "university",
    "internships",
    "internship",
    "early-career",
    "join",
    "join-us",
    "work-with-us",
    "categories",
    "category",
}

# Known ATS regex patterns for exact individual job postings
ATS_JOB_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("greenhouse", re.compile(r"^https?://(?:job-boards|boards)\.greenhouse\.io/([^/?#]+)/jobs/(\d+)", re.I)),
    ("lever", re.compile(r"^https?://jobs\.lever\.co/([^/?#]+)/([0-9a-fA-F-]{10,}|[a-zA-Z0-9-]{10,})(?:/apply)?", re.I)),
    ("ashby", re.compile(r"^https?://jobs\.ashbyhq\.com/([^/?#]+)/([0-9a-fA-F-]{10,})(?:/application)?", re.I)),
    ("workable", re.compile(r"^https?://apply\.workable\.com/([^/?#]+)/j/([a-zA-Z0-9]+)", re.I)),
    ("smartrecruiters", re.compile(r"^https?://jobs\.smartrecruiters\.com/([^/?#]+)/([a-zA-Z0-9-]+)", re.I)),
    ("workday", re.compile(r"^https?://[^/]+\.myworkdayjobs\.com/(?:[a-zA-Z0-9_-]+/)?job/([^/?#]+)/([a-zA-Z0-9_-]+)", re.I)),
    ("keka", re.compile(r"^https?://[^/]+\.keka\.com/careers/jobdetails/([a-zA-Z0-9-]+)", re.I)),
    ("freshteam", re.compile(r"^https?://[^/]+\.freshteam\.com/jobs/(\d+)", re.I)),
    ("zohorecruit", re.compile(r"^https?://[^/]+\.zohorecruit\.(?:com|in)/jobs/Careers/(\d+)", re.I)),
]

# Known ATS generic board listing patterns (to immediately reject if no specific job is targeted)
ATS_GENERIC_PATTERNS = [
    re.compile(r"^https?://(?:job-boards|boards)\.greenhouse\.io/([^/?#]+)/?(?:jobs/?)?$", re.I),
    re.compile(r"^https?://jobs\.lever\.co/([^/?#]+)/?$", re.I),
    re.compile(r"^https?://jobs\.ashbyhq\.com/([^/?#]+)/?$", re.I),
    re.compile(r"^https?://apply\.workable\.com/([^/?#]+)/?$", re.I),
    re.compile(r"^https?://jobs\.smartrecruiters\.com/([^/?#]+)/?$", re.I),
    re.compile(r"^https?://[^/]+\.keka\.com/careers/?$", re.I),
    re.compile(r"^https?://[^/]+\.freshteam\.com/jobs/?$", re.I),
    re.compile(r"^https?://[^/]+\.zohorecruit\.(?:com|in)/jobs/Careers/?$", re.I),
    re.compile(r"^https?://[^/]+\.myworkdayjobs\.com/(?:[a-zA-Z0-9_-]+/)?(?:jobs)?/?$", re.I),
]

# Phrases that indicate a posting is closed, expired, or non-existent
CLOSED_PHRASES = (
    "job is no longer available",
    "position has been filled",
    "position has been closed",
    "position is closed",
    "no longer accepting applications",
    "not accepting applications",
    "job not found",
    "this job has expired",
    "page not found",
    "this position is closed",
    "posting has closed",
    "job expired",
    "opening is closed",
    "job closed",
    "position closed",
    "role closed",
    "application closed",
    "applications are closed",
    "no longer active",
    "this role is no longer available",
    "this listing has expired",
    "the job you are looking for is no longer available",
    "the position you are looking for has been filled",
    "this requisition is closed",
    "this opening has been filled",
    "career opportunity is no longer available",
    "job opening has ended",
    "sorry, this job is no longer available",
    "this posting is no longer available",
    "this job post is no longer available",
    "this posting has been removed",
    "this job is expired",
    "this job is closed",
    "job posting has expired",
    "posting is no longer active",
    "we are no longer accepting applications for this position",
    "this job has been removed",
    "this opening is no longer accepting applications",
)

AGGREGATOR_DOMAINS = {
    "linkedin.com", "indeed.com", "glassdoor.com", "internshala.com",
    "naukri.com", "wellfound.com", "angel.co", "cutshort.io",
    "foundit.in", "simplyhired.com", "simplyhired.co.in", "shine.com",
    "instahyre.com", "cuvette.tech", "jobaaj.com", "unstop.com",
    "timesjobs.com", "freshersworld.com", "hirist.tech", "hirist.com",
    "ziprecruiter.com", "monster.com", "careerbuilder.com",
}


def is_generic_careers_url(url: str) -> tuple[bool, str | None]:
    """Check if a URL points to a company homepage or generic careers / job listing page."""
    if not url:
        return True, "empty url"

    parsed = urlsplit(url)
    if parsed.scheme not in ("http", "https"):
        return True, "invalid scheme"

    host = (parsed.hostname or "").lower()
    path = parsed.path.rstrip("/")
    query = parsed.query.lower()

    # Aggregator check
    if any(host == d or host.endswith(f".{d}") for d in AGGREGATOR_DOMAINS):
        return True, "job aggregator domain"

    # Greenhouse error redirect query
    if "error=true" in query and ("greenhouse.io" in host):
        return True, "greenhouse error redirect"

    # Exact generic career paths
    clean_path = parsed.path.lower()
    if clean_path in GENERIC_CAREERS_PATHS or clean_path.rstrip("/") in GENERIC_CAREERS_PATHS:
        return True, "generic careers page"

    # Root / homepage check
    if not path or path == "/":
        return True, "homepage"

    # ATS generic board patterns
    clean_url = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))
    for pattern in ATS_GENERIC_PATTERNS:
        if pattern.match(clean_url):
            return True, "generic ATS board listing page"

    # Endings check: any path ending in a generic word without a specific job query param
    path_segments = [p.lower() for p in parsed.path.strip("/").split("/") if p]
    if path_segments:
        last_seg = path_segments[-1]
        has_job_id_param = any(k in query for k in ("gh_jid", "job_id", "jobid", "jid", "requisitionid", "id"))
        generic_endings = {
            "careers", "career", "jobs", "job", "job-openings", "openings",
            "positions", "opportunities", "work-with-us", "join-us", "join",
            "hiring", "current-openings", "explore", "search", "all", "job-search",
            "view-all", "find-jobs",
        }
        if last_seg in generic_endings and not has_job_id_param:
            return True, "generic careers page"

    return False, None


def detect_individual_job_url(url: str) -> tuple[bool, str | None, str | None]:
    """Inspect URL structure to detect if it matches a known individual job posting."""
    parsed = urlsplit(url)
    clean_url = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))

    for source_name, pattern in ATS_JOB_PATTERNS:
        match = pattern.search(clean_url)
        if match:
            groups = match.groups()
            job_id = groups[-1] if groups else None
            return True, source_name, job_id

    # Check for general company-specific job detail path patterns
    path = parsed.path.lower().rstrip("/")
    # Pattern: /.../(job|jobs|position|positions|posting|postings|opening|openings|career|careers)/{identifier}
    general_match = re.search(r"/(?:job|jobs|position|positions|posting|postings|opening|openings|career|careers)/([a-zA-Z0-9_-]{3,})$", path)
    if general_match:
        ident = general_match.group(1).lower()
        if ident not in GENERIC_PATH_KEYWORDS and not ident.isdigit() and len(ident) >= 3:
            return True, "direct", ident
        elif ident.isdigit():
            return True, "direct", ident

    return False, None, None


def detect_closed_content(status_code: int, text: str, final_url: str) -> tuple[bool, str | None]:
    """Analyze page content for indications that the job has expired or closed."""
    if status_code in (404, 410):
        return True, f"HTTP {status_code}"

    if status_code >= 400:
        return True, f"HTTP {status_code}"

    # Greenhouse error redirect
    if "error=true" in final_url and "greenhouse.io" in final_url:
        return True, "redirected to Greenhouse board error page"

    # Ashby SPA specific closed check
    if "ashbyhq.com" in final_url:
        if '"posting":null' in text:
            return True, "Ashby posting is null"
        if "<title>Jobs</title>" in text or "<title>Jobs </title>" in text:
            return True, "Ashby page has no active job"

    # Text phrase checks
    text_lower = text.lower()
    for phrase in CLOSED_PHRASES:
        if phrase in text_lower:
            return True, phrase

    return False, None


def inspect_page_for_individual_job(html: str, final_url: str) -> bool:
    """Inspect HTML to verify that the page actually represents an individual job posting."""
    # If URL is a verified ATS job URL pattern, it is definitely an individual job
    is_ats_job, _, _ = detect_individual_job_url(final_url)
    if is_ats_job:
        return True

    soup = BeautifulSoup(html[:100_000], "html.parser")

    # Check 1: Schema.org JobPosting microdata / JSON-LD
    for script in soup.find_all("script", attrs={"type": re.compile(r"application/ld\+json", re.I)}):
        content = script.string or script.get_text() or ""
        if '"@type":"JobPosting"' in content.replace(" ", "") or '"@type": "JobPosting"' in content:
            return True

    # Check 2: Form or button indicating job application
    apply_cues = soup.find_all(["button", "a", "h1", "h2"], string=re.compile(r"(apply for this job|apply now|submit application|apply online)", re.I))
    if apply_cues:
        return True

    # Check 3: Does page contain distinct job listing cards indicating it's a listing page?
    listing_indicators = soup.find_all(string=re.compile(r"(search open positions|filter by department|search jobs|current openings \(\d+\)|browse all jobs)", re.I))
    job_links = [a for a in soup.find_all("a", href=True) if re.search(r"/(?:job|jobs|position)/", a["href"], re.I)]
    if listing_indicators and len(job_links) >= 5:
        # Page is a generic listing of multiple jobs
        return False

    # Default fallback: check if title or headings look like a single job
    title = (soup.title.string if soup.title else "") or ""
    if any(k in title.lower() for k in ["careers", "job search", "current openings", "explore opportunities", "open positions"]):
        return False

    return True


async def validate_job_url(
    url: str,
    company: str | None = None,
    title: str | None = None,
    client: httpx.AsyncClient | None = None,
) -> JobValidationResult:
    """Validate a job URL following redirects, verifying it is an active, individual posting."""
    orig_url = (url or "").strip()
    company_name = company or "Unknown"

    # Step 1: Pre-validation on original URL
    is_gen, gen_reason = is_generic_careers_url(orig_url)
    if is_gen:
        res = JobValidationResult(
            is_valid=False,
            status="generic_careers",
            original_url=orig_url,
            final_url=orig_url,
            rejection_reason=f"original URL is a {gen_reason}",
        )
        _log_validation_result(company_name, title, res)
        return res

    # Step 2: HTTP request with redirect following
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "ngrok-skip-browser-warning": "true",
    }

    should_close_client = False
    if client is None:
        client = httpx.AsyncClient(timeout=15, follow_redirects=True, headers=headers)
        should_close_client = True

    try:
        response = await client.get(orig_url)
    except httpx.TimeoutException:
        res = JobValidationResult(
            is_valid=False,
            status="stale",
            original_url=orig_url,
            rejection_reason="connection timeout",
        )
        _log_validation_result(company_name, title, res)
        return res
    except httpx.HTTPError as exc:
        res = JobValidationResult(
            is_valid=False,
            status="stale",
            original_url=orig_url,
            rejection_reason=f"HTTP connection error: {exc.__class__.__name__}",
        )
        _log_validation_result(company_name, title, res)
        return res
    finally:
        if should_close_client:
            await client.aclose()

    final_url = str(response.url)
    status_code = response.status_code

    # Step 3: Check HTTP Status
    if status_code in (404, 410):
        res = JobValidationResult(
            is_valid=False,
            status="stale",
            original_url=orig_url,
            final_url=final_url,
            http_status=status_code,
            rejection_reason=f"HTTP status {status_code}",
        )
        _log_validation_result(company_name, title, res)
        return res

    if status_code == 403:
        res = JobValidationResult(
            is_valid=False,
            status="error_403",
            original_url=orig_url,
            final_url=final_url,
            http_status=403,
            rejection_reason="HTTP error status 403 Forbidden (access blocked)",
        )
        _log_validation_result(company_name, title, res)
        return res

    if status_code >= 400:
        res = JobValidationResult(
            is_valid=False,
            status="http_error",
            original_url=orig_url,
            final_url=final_url,
            http_status=status_code,
            rejection_reason=f"HTTP error status {status_code}",
        )
        _log_validation_result(company_name, title, res)
        return res

    # Step 4: Check if final URL redirected to a generic careers page or homepage
    is_final_gen, final_gen_reason = is_generic_careers_url(final_url)
    if is_final_gen:
        res = JobValidationResult(
            is_valid=False,
            status="generic_careers",
            original_url=orig_url,
            final_url=final_url,
            http_status=status_code,
            rejection_reason=f"redirected to {final_gen_reason}",
        )
        _log_validation_result(company_name, title, res)
        return res

    # Step 5: Check closed content / expired markers
    is_closed, closed_reason = detect_closed_content(status_code, response.text, final_url)
    if is_closed:
        res = JobValidationResult(
            is_valid=False,
            status="expired",
            original_url=orig_url,
            final_url=final_url,
            http_status=status_code,
            rejection_reason=f"closed/expired job page: {closed_reason}",
        )
        _log_validation_result(company_name, title, res)
        return res

    # Step 6: Verify page is an individual job posting
    is_individual = inspect_page_for_individual_job(response.text, final_url)
    if not is_individual:
        res = JobValidationResult(
            is_valid=False,
            status="not_individual_job",
            original_url=orig_url,
            final_url=final_url,
            http_status=status_code,
            is_individual_job=False,
            rejection_reason="page is a generic listing/search page, not an individual job posting",
        )
        _log_validation_result(company_name, title, res)
        return res

    # Step 7: Identify source and job ID
    _, source, source_job_id = detect_individual_job_url(final_url)
    if not source:
        # Check original URL if final URL had query/masking
        _, source, source_job_id = detect_individual_job_url(orig_url)

    res = JobValidationResult(
        is_valid=True,
        status="active",
        original_url=orig_url,
        final_url=final_url,
        http_status=status_code,
        is_individual_job=True,
        is_active=True,
        source=source or "direct",
        source_job_id=source_job_id,
        rejection_reason=None,
    )
    _log_validation_result(company_name, title, res)
    return res


def validate_job_url_sync(
    url: str,
    company: str | None = None,
    title: str | None = None,
) -> JobValidationResult:
    """Synchronous convenience wrapper for validate_job_url."""
    return asyncio.run(validate_job_url(url, company=company, title=title))


def _log_validation_result(company: str, title: str | None, res: JobValidationResult) -> None:
    """Log validation output at debug level to avoid flooding production logs."""
    if res.is_valid:
        logger.debug(
            f"[JOB VALIDATION]\n"
            f"Company: {company}\n"
            f"Source: {res.source or 'Direct'}\n"
            f"Job ID: {res.source_job_id or 'N/A'}\n"
            f"Original URL: {res.original_url}\n"
            f"Final URL: {res.final_url}\n"
            f"Status: {res.http_status or 200}\n"
            f"Is individual job page: true\n"
            f"Is active: true\n"
        )
    else:
        logger.debug(
            f"[JOB REJECTED]\n"
            f"Company: {company}\n"
            f"Title: {title or 'N/A'}\n"
            f"Original URL: {res.original_url}\n"
            f"Final URL: {res.final_url or res.original_url}\n"
            f"Reason: {res.rejection_reason}\n"
        )
