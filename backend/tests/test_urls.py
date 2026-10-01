import asyncio
import json
import httpx
import pytest
from app.crawler import (
    _find_company_board,
    _normalize_board_jobs,
    _parse_gemini_companies,
    _board_from_url,
    canonical_url,
)
from app.models import RoleType


def test_url_canonicalization_drops_tracking_query_and_slash():
    assert canonical_url("HTTPS://Example.COM/jobs/123/?tracking=a") == "https://example.com/jobs/123"


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


def test_normalizes_entry_level_ats_metadata_for_fresher_roles():
    jobs = _normalize_board_jobs(
        "Example",
        "workable",
        "example",
        "https://boards.example.com",
        {"jobs": [{"title": "Software Engineer", "application_url": "https://jobs.example.com/1", "experience": "Entry-level"}]},
    )

    assert len(jobs) == 1
    assert jobs[0].role_type == RoleType.sde


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
