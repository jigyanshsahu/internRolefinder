import asyncio
import json
import httpx
import pytest
from app.crawler import (
    _discover_company_boards,
    _fetch_schema_board,
    _find_company_board,
    _normalize_board_jobs,
    _normalize_schema_jobs,
    _parse_gemini_companies,
    _active_from_response,
    _board_from_url,
    _board_url,
    canonical_url,
)
from app.types import RoleType


def test_url_canonicalization_drops_tracking_query_and_slash():
    assert canonical_url("HTTPS://Example.COM/jobs/123/?tracking=a") == "https://example.com/jobs/123"


@pytest.mark.parametrize(
    ("status_code", "text", "expected"),
    [
        (200, "Apply for this role", True),
        (200, "This job is no longer available", False),
        (404, "Not found", False),
        (403, "Access denied", None),
        (503, "Service unavailable", None),
    ],
)
def test_job_verification_distinguishes_closed_from_unavailable(status_code, text, expected):
    assert _active_from_response(status_code, text) is expected


@pytest.mark.parametrize(
    ("platform", "payload", "expected_location"),
    [
        ("greenhouse", {"jobs": [{"id": 1, "title": "Software Engineer Intern", "location": {"name": "New York, NY"}}]}, "New York, NY"),
        ("lever", [{"text": "Software Engineer Intern", "applyUrl": "https://jobs.example.com/1", "categories": {"location": "Seattle, WA"}}], "Seattle, WA"),
        ("ashby", {"jobs": [{"title": "Software Engineer Intern", "applyUrl": "https://jobs.example.com/1", "isRemote": True}]}, "Remote"),
        ("smartrecruiters", {"content": [{"id": "123", "name": "Software Engineer Intern", "company": {"identifier": "ExampleCo"}, "location": {"fullLocation": "Bengaluru, India"}}]}, "Bengaluru, India"),
        ("workable", {"jobs": [{"title": "Software Engineer Intern", "application_url": "https://apply.example.com/1", "city": "Bengaluru", "state": "Karnataka", "country": "India"}]}, "Bengaluru, Karnataka, India"),
        ("recruitee", {"offers": [{"title": "Software Engineer Intern", "careers_apply_url": "https://jobs.example.com/1", "remote": True}]}, "Remote"),
    ],
)
def test_normalizes_job_location(platform, payload, expected_location):
    jobs = _normalize_board_jobs("Example", platform, "example", "https://boards.example.com", payload)

    assert jobs[0].location == expected_location
    assert jobs[0].country == ("India" if platform in {"smartrecruiters", "workable"} else None)
    assert jobs[0].is_remote == (platform in {"ashby", "recruitee"})
    if platform == "smartrecruiters":
        assert jobs[0].apply_url == "https://jobs.smartrecruiters.com/ExampleCo/123-software-engineer-intern"


def test_rejects_entry_level_software_role_without_internship():
    jobs = _normalize_board_jobs(
        "Example",
        "workable",
        "example",
        "https://boards.example.com",
        {"jobs": [{"title": "Software Engineer", "application_url": "https://jobs.example.com/1", "experience": "Entry-level"}]},
    )

    assert jobs == []


def test_normalizes_workday_internship_posting():
    jobs = _normalize_board_jobs(
        "Example",
        "workday",
        "example|example.wd5.myworkdayjobs.com|External|en-US",
        "https://example.wd5.myworkdayjobs.com/wday/cxs/example/External/jobs",
        {
            "jobPostings": [{
                "title": "Software Engineer Intern",
                "externalPath": "/job/Bengaluru/Software-Engineer-Intern_R123",
                "locationsText": "Bengaluru, India",
                "remoteType": "Onsite",
                "bulletFields": ["Internship"],
            }, {
                "title": "Software Engineer Intern",
                "locationsText": "Bengaluru, India",
                "bulletFields": ["Internship"],
            }],
        },
    )

    assert len(jobs) == 1
    assert jobs[0].apply_url == "https://example.wd5.myworkdayjobs.com/en-US/External/job/Bengaluru/Software-Engineer-Intern_R123"
    assert jobs[0].country == "India"
    assert jobs[0].role_type == RoleType.sde


def test_workday_board_url_uses_tenant_and_site():
    assert _board_url("workday", "example|example.wd5.myworkdayjobs.com|External|en-US") == (
        "https://example.wd5.myworkdayjobs.com/wday/cxs/example/External/jobs"
    )


def test_normalizes_schema_job_posting_and_canonicalizes_apply_url():
    html = f'<script type="application/ld+json">{json.dumps({"@type": "JobPosting", "title": "Software Engineer Intern", "employmentType": "Internship", "url": "/jobs/swe-intern?utm_source=careers", "jobLocation": {"address": {"addressLocality": "Bengaluru", "addressRegion": "Karnataka", "addressCountry": "India"}}})}</script>'

    jobs = _normalize_schema_jobs("Example", "https://example.in/jobs/swe-intern", "https://example.in/careers", html)

    assert len(jobs) == 1
    assert jobs[0].apply_url == "https://example.in/jobs/swe-intern"
    assert jobs[0].location == "Bengaluru, Karnataka, India"
    assert jobs[0].country == "India"
    assert jobs[0].role_type == RoleType.sde


def test_normalizes_nested_schema_job_postings():
    html = f'<script type="application/ld+json">{json.dumps({"@graph": [{"@type": ["Thing", "JobPosting"], "title": "Software Engineer Intern, Machine Learning", "description": "Internship", "url": "https://example.in/jobs/ml-intern", "jobLocationType": "TELECOMMUTE"}]})}</script>'

    jobs = _normalize_schema_jobs("Example", "https://example.in/careers", "https://example.in/careers", html)

    assert len(jobs) == 1
    assert jobs[0].is_remote is True
    assert jobs[0].location == "Remote"
    assert jobs[0].role_type == RoleType.sde


def test_schema_location_label_remote_sets_remote_flag():
    posting = {
        "@type": "JobPosting",
        "title": "Software Engineer Intern",
        "employmentType": "Internship",
        "url": "https://example.in/jobs/remote-intern",
        "jobLocation": {"address": {"addressLocality": "Remote"}},
    }
    html = f'<script type="application/ld+json">{json.dumps(posting)}</script>'

    jobs = _normalize_schema_jobs("Example", "https://example.in/careers", "https://example.in/careers", html)

    assert len(jobs) == 1
    assert jobs[0].location == "Remote"
    assert jobs[0].is_remote is True


def test_fetch_schema_board_reads_same_company_detail_pages_and_deduplicates():
    posting = {
        "@type": "JobPosting",
        "title": "Software Engineer Intern",
        "employmentType": "Internship",
        "url": "https://example.in/jobs/swe-intern",
    }

    async def run_discovery():
        async def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/careers":
                html = f'<a href="/jobs/swe-intern">Software Engineer Intern</a><script type="application/ld+json">{json.dumps(posting)}</script>'
                return httpx.Response(200, headers={"content-type": "text/html"}, text=html)
            if request.url.path == "/jobs/swe-intern":
                html = f'<script type="application/ld+json">{json.dumps(posting)}</script>'
                return httpx.Response(200, headers={"content-type": "text/html"}, text=html)
            return httpx.Response(404)

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=True) as client:
            return await _fetch_schema_board(
                client,
                {"name": "Example", "platform": "schema", "slug": "example.in", "careers_url": "https://example.in/careers"},
            )

    jobs = asyncio.run(run_discovery())

    assert len(jobs) == 1
    assert jobs[0].apply_url == "https://example.in/jobs/swe-intern"


@pytest.mark.parametrize("location", ["Bangalore", "Bengaluru", "Onsite in Bangalore"])
def test_recognizes_indian_city_as_country(location):
    jobs = _normalize_board_jobs(
        "Example",
        "lever",
        "example",
        "https://boards.example.com",
        [{"text": "Software Engineer Intern", "applyUrl": "https://jobs.example.com/1", "categories": {"location": location}}],
    )

    assert jobs[0].country == "India"


def test_parses_gemini_companies_and_rejects_unsafe_websites():
    payload = {
        "candidates": [{
            "content": {
                "parts": [{
                    "text": json.dumps({
                        "companies": [
                            {"name": "Example Startup", "website": "example.in"},
                            {"name": "Local Address", "website": "http://127.0.0.1"},
                            {"name": "Bad Scheme", "website": "javascript:alert(1)"},
                        ]
                    })
                }]
            }
        }]
    }

    assert _parse_gemini_companies(payload) == [
        {"name": "Example Startup", "website": "https://example.in"}
    ]


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://job-boards.greenhouse.io/acme/jobs/123", ("greenhouse", "acme")),
        ("https://jobs.lever.co/acme/123", ("lever", "acme")),
        ("https://jobs.ashbyhq.com/acme", ("ashby", "acme")),
        ("https://jobs.smartrecruiters.com/acme/123-role", ("smartrecruiters", "acme")),
        ("https://apply.workable.com/acme/jobs/123", ("workable", "acme")),
        ("https://acme.recruitee.com/o/intern", ("recruitee", "acme")),
        ("https://acme.wd5.myworkdayjobs.com/en-US/External/job/India/Intern_R123", ("workday", "acme|acme.wd5.myworkdayjobs.com|External|en-US")),
        ("https://zluri.keka.com/careers/", ("keka", "zluri")),
        ("https://spotdraft.freshteam.com/jobs", ("freshteam", "spotdraft")),
        ("https://agnikul.zohorecruit.in/jobs/Careers", ("zohorecruit", "agnikul|in")),
        ("https://example.zohorecruit.com/jobs/Careers", ("zohorecruit", "example|com")),
        ("https://www.linkedin.com/jobs/view/12345", None),
        ("https://internshala.com/internship/detail/123", None),
        ("https://wellfound.com/company/acme/jobs", None),
        ("https://example.in/careers", None),
    ],
)
def test_recognizes_supported_careers_boards(url, expected):
    assert _board_from_url(url) == expected


def test_discovers_ats_board_from_official_careers_page():
    async def run_discovery():
        async def handler(request: httpx.Request) -> httpx.Response:
            if request.url.host == "example.in" and request.url.path == "/":
                return httpx.Response(
                    200,
                    headers={"content-type": "text/html"},
                    text='<a href="https://example.in/careers">Careers</a>',
                )
            if request.url.path == "/careers":
                return httpx.Response(
                    200,
                    headers={"content-type": "text/html"},
                    text='<a href="https://jobs.lever.co/example-startup">Open roles</a>',
                )
            return httpx.Response(404)

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=True) as client:
            return await _find_company_board(client, "Example Startup", "https://example.in")

    board = asyncio.run(run_discovery())

    assert board is not None
    assert (board.company_name, board.platform, board.slug) == ("Example Startup", "lever", "example-startup")


def test_discovers_custom_careers_page_without_ats_board():
    async def run_discovery():
        async def handler(request: httpx.Request) -> httpx.Response:
            if request.url.host == "example.in" and request.url.path == "/":
                return httpx.Response(
                    200,
                    headers={"content-type": "text/html"},
                    text='<a href="https://example.in/careers">Careers</a>',
                )
            if request.url.path == "/careers":
                return httpx.Response(
                    200,
                    headers={"content-type": "text/html"},
                    text='<a href="/jobs/software-engineer-intern">Software Engineer Intern</a>',
                )
            return httpx.Response(404)

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=True) as client:
            return await _find_company_board(client, "Example Startup", "https://example.in")

    board = asyncio.run(run_discovery())

    assert board is not None
    assert (board.platform, board.slug, board.careers_url) == (
        "schema",
        "example.in",
        "https://example.in/careers",
    )


def test_company_seed_uses_verified_direct_ats_url():
    async def run_discovery():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(404))) as client:
            return await _discover_company_boards(client, [{
                "company_name": "Merkle Science",
                "website_url": "https://www.merklescience.com",
                "careers_url": "https://jobs.lever.co/merklescience",
            }])

    result = asyncio.run(run_discovery())[0]

    assert result.status == "board_found"
    assert result.board is not None
    assert (result.board.platform, result.board.slug) == ("lever", "merklescience")


def test_company_seed_reports_missing_official_website_without_requesting_it():
    async def run_discovery():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(500))) as client:
            return await _discover_company_boards(client, [{
                "company_name": "Unverified Startup",
                "website_url": None,
                "careers_url": None,
            }])

    result = asyncio.run(run_discovery())[0]

    assert result.status == "needs_official_url"
    assert result.board is None


def test_normalizes_freshteam_internship():
    payload = {
        "jobs": [
            {
                "id": "1001",
                "title": "Software Engineer Intern",
                "branch": "Bengaluru, India",
                "remote": True,
                "job_type": "internship",
            }
        ]
    }
    jobs = _normalize_board_jobs("SpotDraft", "freshteam", "spotdraft", "https://spotdraft.freshteam.com/jobs", payload)
    assert len(jobs) == 1
    assert jobs[0].title == "Software Engineer Intern"
    assert jobs[0].apply_url == "https://spotdraft.freshteam.com/jobs/1001"
    assert jobs[0].is_remote is True
    assert jobs[0].country == "India"
    assert jobs[0].role_type == RoleType.sde


def test_normalizes_keka_internship():
    payload = {
        "jobPostings": [
            {
                "id": "2002",
                "title": "Software Engineer Intern, AI",
                "location": "Remote, India",
                "isRemote": True,
                "jobType": "Internship",
            }
        ]
    }
    jobs = _normalize_board_jobs("Zluri", "keka", "zluri", "https://zluri.keka.com/careers/api/jobpostings", payload)
    assert len(jobs) == 1
    assert jobs[0].title == "Software Engineer Intern, AI"
    assert jobs[0].apply_url == "https://zluri.keka.com/careers/jobdetails/2002"
    assert jobs[0].is_remote is True
    assert jobs[0].role_type == RoleType.sde


def test_normalizes_zohorecruit_internship():
    payload = {
        "data": [
            {
                "id": "3003",
                "Job_Title": "Full Stack Engineer Intern",
                "City": "Chennai",
                "Country": "India",
                "Remote_Job": False,
                "Job_Type": "Internship",
            }
        ]
    }
    jobs = _normalize_board_jobs("Agnikul Cosmos", "zohorecruit", "agnikul|in", "https://agnikul.zohorecruit.in/jobs/Careers", payload)
    assert len(jobs) == 1
    assert jobs[0].title == "Full Stack Engineer Intern"
    assert jobs[0].apply_url == "https://agnikul.zohorecruit.in/jobs/Careers/3003"
    assert jobs[0].country == "India"
    assert jobs[0].role_type == RoleType.full_stack

