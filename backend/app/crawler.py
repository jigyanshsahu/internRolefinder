"""Public-page discovery and verification helpers.

This module intentionally makes no attempt to work around access controls. A source
that rejects ordinary access is skipped and can be rediscovered later.
"""
import asyncio
from dataclasses import dataclass
import ipaddress
import json
import re
from urllib.parse import parse_qsl, quote, urlencode, urljoin, urlsplit, urlunsplit
from bs4 import BeautifulSoup
import httpx
from app.config import get_settings
from app.classifier import classify_role
from app.models import RoleType

CATALOG_ATS = {"greenhouse", "lever", "ashby", "smartrecruiters", "workable", "recruitee"}
CLOSED_TERMS = ("job is no longer available", "position has been filled", "no longer accepting applications", "job not found", "this job has expired", "page not found")
INDIA_CITY_PATTERN = re.compile(
    r"\b(bangalore|bengaluru|hyderabad|mumbai|delhi|gurgaon|gurugram|noida|pune|chennai|kolkata|ahmedabad|jaipur|kochi|indore|thiruvananthapuram)\b",
    re.I,
)


@dataclass(frozen=True)
class ExtractedJob:
    title: str
    company: str | None
    location: str | None
    country: str | None
    is_remote: bool
    role_type: RoleType
    apply_url: str
    source_url: str


@dataclass(frozen=True)
class DiscoveredBoard:
    company_name: str
    platform: str
    slug: str
    careers_url: str


CAREERS_LINK_PATTERN = re.compile(r"\b(career|careers|jobs|job openings|open positions|join our team)\b", re.I)


def canonical_url(url: str) -> str:
    parts = urlsplit(url)
    # Preserve identifiers such as `gh_jid`; remove only common tracking fields.
    query = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True) if not (key.lower().startswith("utm_") or key.lower() in {"tracking", "gh_src"})]
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), urlencode(query), ""))


def _board_url(platform: str, slug: str) -> str:
    if platform == "greenhouse":
        return f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
    if platform == "lever":
        return f"https://api.lever.co/v0/postings/{slug}?mode=json"
    if platform == "ashby":
        return f"https://api.ashbyhq.com/posting-api/job-board/{slug}"
    if platform == "smartrecruiters":
        return f"https://api.smartrecruiters.com/v1/companies/{quote(slug, safe='')}/postings"
    if platform == "workable":
        return f"https://www.workable.com/api/accounts/{quote(slug, safe='')}"
    if platform == "workday":
        tenant, hostname, site, _locale = slug.split("|", 3)
        return f"https://{hostname}/wday/cxs/{quote(tenant, safe='')}/{quote(site, safe='')}/jobs"
    return f"https://{quote(slug, safe='')}.recruitee.com/api/offers/"


def _location_label(value: object, workplace_type: object = None, is_remote: bool = False) -> str | None:
    if isinstance(value, dict):
        value = value.get("name") or value.get("fullLocation") or ", ".join(
            str(part).strip()
            for part in (value.get("city"), value.get("state") or value.get("region"), value.get("country"))
            if isinstance(part, str) and part.strip()
        )
    if isinstance(value, str) and value.strip():
        return value.strip()[:300]
    if is_remote:
        return "Remote"
    if isinstance(workplace_type, str):
        normalized_type = workplace_type.strip().lower().replace("_", "-")
        if normalized_type in {"remote", "hybrid", "on-site", "onsite"}:
            return "On-site" if normalized_type == "onsite" else normalized_type.title()
    return None


def _country_label(value: object, location: object = None) -> str | None:
    if isinstance(value, dict):
        location = location or value.get("fullLocation") or value.get("name") or ", ".join(
            str(part).strip()
            for part in (value.get("city"), value.get("region"), value.get("country"))
            if isinstance(part, str) and part.strip()
        )
        value = value.get("country") or value.get("countryCode") or value.get("country_code")
    if isinstance(value, str) and value.strip():
        normalized = value.strip()
        if normalized.lower() in {"in", "ind", "india"}:
            return "India"
        return normalized[:150]
    if isinstance(location, str) and re.search(r"\bindia\b", location, re.I):
        return "India"
    if isinstance(location, str) and INDIA_CITY_PATTERN.search(location):
        return "India"
    return None


def _is_remote(location: object, remote_flag: bool = False, workplace_type: object = None) -> bool:
    if remote_flag:
        return True
    if isinstance(workplace_type, str) and workplace_type.strip().lower() == "remote":
        return True
    return isinstance(location, str) and bool(re.search(r"\bremote\b", location, re.I))


def _role_context(*values: object) -> str:
    return " ".join(value for value in values if isinstance(value, str))


def _parse_gemini_companies(payload: object) -> list[dict[str, str]]:
    if not isinstance(payload, dict):
        return []
    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        return []
    content = candidates[0].get("content") if isinstance(candidates[0], dict) else None
    parts = content.get("parts") if isinstance(content, dict) else None
    response_text = next((part.get("text") for part in parts or [] if isinstance(part, dict) and isinstance(part.get("text"), str)), None)
    if not response_text:
        return []
    try:
        result = json.loads(response_text)
    except ValueError:
        return []
    companies = result.get("companies") if isinstance(result, dict) else None
    if not isinstance(companies, list):
        return []
    verified_candidates = []
    for company in companies:
        if not isinstance(company, dict):
            continue
        name = company.get("name")
        website = company.get("website")
        if not isinstance(name, str) or not name.strip() or not isinstance(website, str):
            continue
        website = website.strip()
        if not urlsplit(website).scheme:
            website = f"https://{website}"
        parsed_url = urlsplit(website)
        hostname = parsed_url.hostname
        if parsed_url.scheme not in {"http", "https"} or not hostname or "." not in hostname:
            continue
        try:
            ipaddress.ip_address(hostname)
        except ValueError:
            verified_candidates.append({"name": name.strip()[:300], "website": website})
    return verified_candidates


def _board_from_url(url: str) -> tuple[str, str] | None:
    parsed_url = urlsplit(url)
    hostname = (parsed_url.hostname or "").lower()
    path_parts = [part for part in parsed_url.path.split("/") if part]
    if hostname in {"boards.greenhouse.io", "job-boards.greenhouse.io"} and path_parts:
        return "greenhouse", path_parts[0]
    if hostname == "jobs.lever.co" and path_parts:
        return "lever", path_parts[0]
    if hostname == "jobs.ashbyhq.com" and path_parts:
        return "ashby", path_parts[0]
    if hostname == "jobs.smartrecruiters.com" and path_parts:
        return "smartrecruiters", path_parts[0]
    if hostname == "apply.workable.com" and path_parts:
        return "workable", path_parts[0]
    if hostname.endswith(".workable.com") and hostname != "www.workable.com":
        return "workable", hostname.removesuffix(".workable.com")
    if hostname.endswith(".recruitee.com"):
        return "recruitee", hostname.removesuffix(".recruitee.com")
    if hostname.endswith(".myworkdayjobs.com") and len(path_parts) >= 2:
        tenant = hostname.split(".", 1)[0]
        return "workday", f"{tenant}|{hostname}|{path_parts[1]}|{path_parts[0]}"
    return None


def _same_company_host(candidate_url: str, link_url: str) -> bool:
    candidate_host = (urlsplit(candidate_url).hostname or "").lower().removeprefix("www.")
    link_host = (urlsplit(link_url).hostname or "").lower().removeprefix("www.")
    return bool(candidate_host and link_host and (link_host == candidate_host or link_host.endswith(f".{candidate_host}") or candidate_host.endswith(f".{link_host}")))


def _links_from_page(page_url: str, html: str) -> tuple[list[str], list[str]]:
    ats_links = []
    careers_pages = []
    soup = BeautifulSoup(html, "html.parser")
    for anchor in soup.find_all("a", href=True):
        link_url = urljoin(page_url, anchor["href"])
        if urlsplit(link_url).scheme not in {"http", "https"}:
            continue
        if _board_from_url(link_url):
            ats_links.append(link_url)
        elif CAREERS_LINK_PATTERN.search(f"{anchor.get_text(' ', strip=True)} {link_url}") and _same_company_host(page_url, link_url):
            careers_pages.append(link_url)
    return ats_links, careers_pages


def _job_links_from_page(page_url: str, html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for anchor in soup.find_all("a", href=True):
        link_url = urljoin(page_url, anchor["href"])
        if urlsplit(link_url).scheme not in {"http", "https"} or not _same_company_host(page_url, link_url):
            continue
        label = f"{anchor.get_text(' ', strip=True)} {urlsplit(link_url).path}"
        if re.search(r"\b(job|position|opening|intern|role)\b", label, re.I):
            links.append(canonical_url(link_url))
    return list(dict.fromkeys(links))


def _schema_job_postings(value: object) -> list[dict]:
    if isinstance(value, list):
        return [posting for item in value for posting in _schema_job_postings(item)]
    if not isinstance(value, dict):
        return []
    job_type = value.get("@type")
    postings = [value] if job_type == "JobPosting" or isinstance(job_type, list) and "JobPosting" in job_type else []
    for key in ("@graph", "mainEntity", "itemListElement", "item"):
        postings.extend(_schema_job_postings(value.get(key)))
    return postings


def _schema_text(value: object) -> str:
    if isinstance(value, str):
        return BeautifulSoup(value, "html.parser").get_text(" ", strip=True)
    if isinstance(value, dict):
        return " ".join(_schema_text(part) for part in value.values())
    if isinstance(value, list):
        return " ".join(_schema_text(part) for part in value)
    return ""


def _schema_location(posting: dict) -> tuple[str | None, bool]:
    places = posting.get("jobLocation")
    if isinstance(places, dict):
        places = [places]
    labels = []
    for place in places if isinstance(places, list) else []:
        if not isinstance(place, dict):
            continue
        address = place.get("address")
        if isinstance(address, str):
            labels.append(address)
        elif isinstance(address, dict):
            country = address.get("addressCountry")
            if isinstance(country, dict):
                country = country.get("name")
            parts = (address.get("addressLocality"), address.get("addressRegion"), country)
            labels.append(", ".join(str(part).strip() for part in parts if isinstance(part, str) and part.strip()))
    location_type = _schema_text(posting.get("jobLocationType")).lower()
    remote = "telecommute" in location_type or "remote" in location_type
    location = _location_label(", ".join(label for label in labels if label))
    return location or ("Remote" if remote else None), remote


def _normalize_schema_jobs(company: str, page_url: str, source_url: str, html: str) -> list[ExtractedJob]:
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for script in soup.find_all("script", attrs={"type": re.compile(r"application/ld\+json", re.I)}):
        try:
            payload = json.loads(script.string or script.get_text())
        except (TypeError, ValueError):
            continue
        for posting in _schema_job_postings(payload):
            title = posting.get("title")
            if not isinstance(title, str) or not title.strip():
                continue
            role_context = " ".join(
                _schema_text(posting.get(field))
                for field in ("employmentType", "experienceRequirements", "qualifications", "educationRequirements", "description")
            )
            role_type = classify_role(title, role_context)
            apply_url = posting.get("url")
            if not isinstance(apply_url, str) or not apply_url.strip():
                apply_url = page_url
            apply_url = urljoin(page_url, apply_url)
            if not role_type or urlsplit(apply_url).scheme not in {"http", "https"}:
                continue
            location, remote = _schema_location(posting)
            results.append(ExtractedJob(
                title=title.strip()[:500],
                company=company[:300],
                location=location,
                country=_country_label(None, location),
                is_remote=remote,
                role_type=role_type,
                apply_url=canonical_url(apply_url),
                source_url=canonical_url(source_url),
            ))
    return results


async def _fetch_schema_board(client: httpx.AsyncClient, board: dict[str, str]) -> list[ExtractedJob]:
    careers_url = board.get("careers_url", "")
    if urlsplit(careers_url).scheme not in {"http", "https"}:
        return []
    try:
        response = await client.get(careers_url)
        if response.status_code != 200 or "text/html" not in response.headers.get("content-type", "text/html"):
            return []
        if not _same_company_host(careers_url, str(response.url)):
            return []
        jobs = _normalize_schema_jobs(board["name"], str(response.url), careers_url, response.text)
        detail_urls = _job_links_from_page(str(response.url), response.text)[:8]
        for detail_url in detail_urls:
            try:
                detail = await client.get(detail_url)
            except httpx.HTTPError:
                continue
            if detail.status_code == 200 and "text/html" in detail.headers.get("content-type", "text/html") and _same_company_host(careers_url, str(detail.url)):
                jobs.extend(_normalize_schema_jobs(board["name"], str(detail.url), careers_url, detail.text))
        unique_jobs = {job.apply_url: job for job in jobs}
        return list(unique_jobs.values())
    except (httpx.HTTPError, ValueError):
        return []


async def _find_company_board(client: httpx.AsyncClient, name: str, website: str) -> DiscoveredBoard | None:
    try:
        homepage = await client.get(website)
        if homepage.status_code != 200 or "text/html" not in homepage.headers.get("content-type", "text/html"):
            return None
        homepage_url = str(homepage.url)
        ats_links, careers_pages = _links_from_page(homepage_url, homepage.text)
        pages_to_check = list(dict.fromkeys(careers_pages))[:4]
        for careers_page in pages_to_check:
            response = await client.get(careers_page)
            if response.status_code == 200 and "text/html" in response.headers.get("content-type", "text/html"):
                page_ats_links, _ = _links_from_page(str(response.url), response.text)
                ats_links.extend(page_ats_links)
        for ats_link in ats_links:
            board = _board_from_url(ats_link)
            if board:
                platform, slug = board
                return DiscoveredBoard(company_name=name, platform=platform, slug=slug, careers_url=ats_link)
        if pages_to_check:
            return DiscoveredBoard(
                company_name=name,
                platform="schema",
                slug=urlsplit(homepage_url).hostname or homepage_url,
                careers_url=pages_to_check[0],
            )
    except (httpx.HTTPError, ValueError):
        return None
    return None


async def discover_indian_startup_boards() -> list[DiscoveredBoard]:
    settings = get_settings()
    api_key = settings.gemini_api_key.get_secret_value() if settings.gemini_api_key else ""
    if not api_key.strip():
        return []
    limit = min(max(settings.startup_discovery_limit, 1), 100)
    prompt = (
        f"List up to {limit} currently active, early-stage technology product startups headquartered in India. "
        "Prioritize seed-to-Series-B companies likely to hire software interns. "
        "Return only companies with an official website you are confident about. "
        "Exclude multinational corporations, IT services/consulting firms, staffing firms, job boards, and accelerators. "
        "Do not invent company names or URLs. "
        'Return JSON matching {"companies":[{"name":"Company name","website":"https://official-domain"}]}. '
        "These are discovery candidates; the application will verify official career links before crawling."
    )
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{quote(settings.gemini_model, safe='')}:generateContent"
    headers = {"x-goog-api-key": api_key}
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.2},
    }
    async with httpx.AsyncClient(timeout=30, follow_redirects=True, headers={"User-Agent": "InternRoleFinderBot/1.0 (+startup-discovery)"}) as client:
        response = await client.post(api_url, headers=headers, json=body)
        response.raise_for_status()
        companies = _parse_gemini_companies(response.json())[:limit]
        semaphore = asyncio.Semaphore(5)

        async def find_board(company: dict[str, str]) -> DiscoveredBoard | None:
            async with semaphore:
                return await _find_company_board(client, company["name"], company["website"])

        discovered = await asyncio.gather(*(find_board(company) for company in companies))
    boards: dict[tuple[str, str], DiscoveredBoard] = {}
    for board in discovered:
        if board:
            boards.setdefault((board.platform, board.slug), board)
    return list(boards.values())


def _normalize_board_jobs(company: str, platform: str, slug: str, source_url: str, payload: object) -> list[ExtractedJob]:
    if platform == "greenhouse":
        items = payload.get("jobs", []) if isinstance(payload, dict) else []
        # The API's `absolute_url` can be a shared employer careers route. The
        # Greenhouse-hosted per-job route always identifies the actual posting.
        mappings = (
            (
                item.get("title", ""),
                f"https://job-boards.greenhouse.io/{slug}/jobs/{item['id']}",
                _location_label(item.get("location")),
                _country_label(item.get("location"), item.get("location", {}).get("name") if isinstance(item.get("location"), dict) else None),
                _is_remote(item.get("location", {}).get("name") if isinstance(item.get("location"), dict) else item.get("location")),
                "",
            )
            for item in items
            if item.get("id")
        )
    elif platform == "lever":
        items = payload if isinstance(payload, list) else []
        mappings = (
            (
                item.get("text", ""),
                item.get("applyUrl") or item.get("hostedUrl"),
                _location_label(item.get("categories", {}).get("location") if isinstance(item.get("categories"), dict) else None, item.get("workplaceType")),
                _country_label(None, item.get("categories", {}).get("location") if isinstance(item.get("categories"), dict) else None),
                _is_remote(item.get("categories", {}).get("location") if isinstance(item.get("categories"), dict) else None, workplace_type=item.get("workplaceType")),
                _role_context(item.get("categories", {}).get("commitment"), item.get("categories", {}).get("team")) if isinstance(item.get("categories"), dict) else "",
            )
            for item in items
        )
    elif platform == "ashby":
        items = payload.get("jobs", []) if isinstance(payload, dict) else []
        mappings = (
            (
                item.get("title", ""),
                item.get("applyUrl") or item.get("jobUrl"),
                _location_label(item.get("location"), is_remote=item.get("isRemote") is True),
                _country_label(None, item.get("location")),
                _is_remote(item.get("location"), remote_flag=item.get("isRemote") is True),
                _role_context(item.get("employmentType"), item.get("department")),
            )
            for item in items
        )
    elif platform == "smartrecruiters":
        items = payload.get("content", []) if isinstance(payload, dict) else []
        mappings = (
            (
                item.get("name", ""),
                item.get("applyUrl") or item.get("postingUrl") or (
                    f"https://jobs.smartrecruiters.com/{quote(item.get('company', {}).get('identifier', slug), safe='')}/"
                    f"{item.get('id')}-{re.sub(r'[^a-z0-9]+', '-', item.get('name', '').lower()).strip('-')}"
                    if item.get("id") and isinstance(item.get("name"), str)
                    else None
                ),
                _location_label(
                    item.get("location"),
                    "hybrid" if isinstance(item.get("location"), dict) and item["location"].get("hybrid") else None,
                    is_remote=isinstance(item.get("location"), dict) and item["location"].get("remote") is True,
                ),
                _country_label(item.get("location")),
                _is_remote(None, remote_flag=isinstance(item.get("location"), dict) and item["location"].get("remote") is True),
                _role_context(
                    item.get("typeOfEmployment", {}).get("label") if isinstance(item.get("typeOfEmployment"), dict) else None,
                    item.get("experienceLevel", {}).get("label") if isinstance(item.get("experienceLevel"), dict) else None,
                ),
            )
            for item in items
        )
    elif platform == "workable":
        items = payload.get("jobs", []) if isinstance(payload, dict) else []
        mappings = (
            (
                item.get("title", ""),
                item.get("application_url") or item.get("url"),
                _location_label(
                    {"city": item.get("city"), "state": item.get("state"), "country": item.get("country")},
                    is_remote=item.get("telecommuting") is True,
                ),
                _country_label(item.get("country")),
                _is_remote(None, remote_flag=item.get("telecommuting") is True, workplace_type=item.get("workplace_type")),
                _role_context(item.get("employment_type"), item.get("experience"), item.get("workplace_type")),
            )
            for item in items
        )
    elif platform == "recruitee":
        items = payload.get("offers", []) if isinstance(payload, dict) else []
        mappings = (
            (
                item.get("title", ""),
                item.get("careers_apply_url") or item.get("careers_url"),
                _location_label(
                    item.get("location"),
                    "hybrid" if item.get("hybrid") is True else None,
                    is_remote=item.get("remote") is True,
                ),
                _country_label(item.get("country") or item.get("country_code"), item.get("location")),
                _is_remote(item.get("location"), remote_flag=item.get("remote") is True),
                _role_context(item.get("employment_type_code"), item.get("experience_code")),
            )
            for item in items
        )
    elif platform == "workday":
        items = payload.get("jobPostings", []) if isinstance(payload, dict) else []
        _, hostname, site, locale = slug.split("|", 3)
        mappings = (
            (
                item.get("title", ""),
                f"https://{hostname}/{locale}/{quote(site, safe='')}{item['externalPath']}"
                if isinstance(item.get("externalPath"), str) else None,
                _location_label(item.get("locationsText"), item.get("remoteType")),
                _country_label(None, item.get("locationsText")),
                _is_remote(item.get("locationsText"), workplace_type=item.get("remoteType")),
                _role_context(
                    item.get("employmentType"),
                    " ".join(value for value in item.get("bulletFields", []) if isinstance(value, str))
                    if isinstance(item.get("bulletFields"), list) else "",
                ),
            )
            for item in items
        )
    else:
        return []

    results = []
    for title, apply_url, location, country, is_remote, role_context in mappings:
        if not isinstance(title, str) or not isinstance(apply_url, str):
            continue
        role_type = classify_role(title, role_context)
        if role_type and apply_url.startswith(("http://", "https://")):
            results.append(ExtractedJob(title=title[:500], company=company[:300], location=location, country=country, is_remote=is_remote, role_type=role_type, apply_url=canonical_url(apply_url), source_url=source_url))
    return results


async def discover_jobs_from_public_ats(extra_boards: list[dict[str, str]] | None = None) -> list[ExtractedJob]:
    """Fetch published jobs from free Greenhouse, Lever, and Ashby job feeds.

    The company board catalog is a public, daily refreshed list. Each role is still
    read directly from its employer's public ATS endpoint, not from a search API.
    """
    settings = get_settings()
    headers = {"User-Agent": "InternRoleFinderBot/1.0 (+public-ats-indexer)"}
    async with httpx.AsyncClient(timeout=25, follow_redirects=True, headers=headers) as client:
        catalog_response = await client.get(settings.public_ats_company_catalog_url)
        catalog_response.raise_for_status()
        catalog_boards = [entry for entry in catalog_response.json() if entry.get("platform") in CATALOG_ATS and entry.get("slug")]
        boards = catalog_boards + (extra_boards or [])
        semaphore = asyncio.Semaphore(8)

        async def fetch_board(board: dict) -> list[ExtractedJob]:
            async with semaphore:
                platform, slug, company = board["platform"], board["slug"], board["name"]
                if platform == "schema":
                    return await _fetch_schema_board(client, board)
                source_url = _board_url(platform, slug)
                try:
                    if platform == "workday":
                        jobs: list[ExtractedJob] = []
                        offset = 0
                        while True:
                            response = await client.post(
                                source_url,
                                json={"appliedFacets": {}, "limit": 20, "offset": offset, "searchText": ""},
                            )
                            if response.status_code != 200:
                                break
                            payload = response.json()
                            items = payload.get("jobPostings", []) if isinstance(payload, dict) else []
                            jobs.extend(_normalize_board_jobs(company, platform, slug, source_url, payload))
                            total = payload.get("total", 0) if isinstance(payload, dict) else 0
                            if not items or offset + len(items) >= total:
                                break
                            offset += len(items)
                        return jobs
                    if platform == "smartrecruiters":
                        jobs: list[ExtractedJob] = []
                        offset = 0
                        while True:
                            response = await client.get(source_url, params={"limit": 100, "offset": offset, "destination": "PUBLIC"})
                            if response.status_code != 200:
                                break
                            payload = response.json()
                            items = payload.get("content", []) if isinstance(payload, dict) else []
                            jobs.extend(_normalize_board_jobs(company, platform, slug, source_url, payload))
                            if not items or offset + len(items) >= payload.get("totalFound", 0):
                                break
                            offset += len(items)
                        return jobs
                    response = await client.get(source_url)
                    if response.status_code != 200:
                        return []
                    return _normalize_board_jobs(company, platform, slug, source_url, response.json())
                except (httpx.HTTPError, ValueError):
                    return []

        boards_result = await asyncio.gather(*(fetch_board(board) for board in boards))
    jobs: dict[str, ExtractedJob] = {}
    for batch in boards_result:
        for job in batch:
            jobs.setdefault(job.apply_url, job)
    return list(jobs.values())


async def is_active(url: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True, headers={"User-Agent": "InternRoleFinderBot/1.0 (+public-link-indexer)"}) as client:
            response = await client.get(url)
    except httpx.HTTPError:
        # A request failure is not proof that a job expired; the worker leaves it for later retry.
        return True
    if response.status_code in (404, 410):
        return False
    # Rate limits, server errors, and blocked/unauthenticated pages are not evidence
    # that an application closed. Keep the record for a future scheduled retry.
    if response.status_code != 200:
        return True
    text = response.text.lower()
    return response.status_code < 400 and not any(term in text for term in CLOSED_TERMS)
