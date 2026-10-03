"""Tests for the Job URL Validator Service.

Covers all required test scenarios:
- valid individual job URL
- 404 URL
- 410 URL
- redirect to valid job
- redirect to careers homepage
- expired job page
- Ashby job
- Lever job
- Greenhouse job
- company-specific job page
"""
import asyncio
import httpx
from app.services.job_validator import (
    validate_job_url,
    is_generic_careers_url,
    detect_individual_job_url,
    detect_closed_content,
    inspect_page_for_individual_job,
)


def test_valid_individual_job_url():
    """Verify that a valid individual job posting is accepted."""
    html_content = """
    <!DOCTYPE html>
    <html>
      <head><title>Software Engineer Intern - Acme Corp</title></head>
      <body>
        <h1>Software Engineer Intern</h1>
        <p>Job Description: We are looking for an intern...</p>
        <button>Apply for this job</button>
      </body>
    </html>
    """
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, text=html_content, request=request)
    )

    async def run():
        async with httpx.AsyncClient(transport=transport) as client:
            return await validate_job_url(
                "https://careers.acme.com/jobs/sde-intern-12345",
                company="Acme Corp",
                title="Software Engineer Intern",
                client=client,
            )

    res = asyncio.run(run())
    assert res.is_valid is True
    assert res.status == "active"
    assert res.is_individual_job is True
    assert res.is_active is True
    assert res.http_status == 200


def test_404_url():
    """Verify that a 404 response is marked stale and rejected."""
    transport = httpx.MockTransport(
        lambda request: httpx.Response(404, text="Not Found", request=request)
    )

    async def run():
        async with httpx.AsyncClient(transport=transport) as client:
            return await validate_job_url(
                "https://jobs.lever.co/acme/00000000-0000-0000-0000-000000000000",
                company="Acme",
                client=client,
            )

    res = asyncio.run(run())
    assert res.is_valid is False
    assert res.status == "stale"
    assert "404" in res.rejection_reason


def test_410_url():
    """Verify that a 410 Gone response is marked stale and rejected."""
    transport = httpx.MockTransport(
        lambda request: httpx.Response(410, text="Gone", request=request)
    )

    async def run():
        async with httpx.AsyncClient(transport=transport) as client:
            return await validate_job_url(
                "https://boards.greenhouse.io/acme/jobs/999999",
                company="Acme",
                client=client,
            )

    res = asyncio.run(run())
    assert res.is_valid is False
    assert res.status == "stale"
    assert "410" in res.rejection_reason


def test_403_url():
    """Verify that a 403 Forbidden response is rejected and not listed."""
    transport = httpx.MockTransport(
        lambda request: httpx.Response(403, text="Forbidden", request=request)
    )

    async def run():
        async with httpx.AsyncClient(transport=transport) as client:
            return await validate_job_url(
                "https://job-boards.greenhouse.io/acme/jobs/12345",
                company="Acme",
                client=client,
            )

    res = asyncio.run(run())
    assert res.is_valid is False
    assert res.status == "error_403"
    assert "403" in res.rejection_reason


def test_redirect_to_valid_job():
    """Verify that a tracking link redirecting to a valid job detail page is preserved and accepted."""
    final_html = """
    <html>
      <head><title>Backend Intern - Stripe</title></head>
      <body>
        <h1>Backend Intern</h1>
        <a href="#apply">Apply Now</a>
      </body>
    </html>
    """

    def handler(request: httpx.Request) -> httpx.Response:
        if "track" in str(request.url):
            return httpx.Response(
                302,
                headers={"Location": "https://jobs.lever.co/stripe/12345678-abcd-1234-abcd-1234567890ab"},
                request=request,
            )
        return httpx.Response(200, text=final_html, request=request)

    transport = httpx.MockTransport(handler)

    async def run():
        async with httpx.AsyncClient(transport=transport, follow_redirects=True) as client:
            return await validate_job_url(
                "https://track.acme.com/apply/stripe-intern",
                company="Stripe",
                client=client,
            )

    res = asyncio.run(run())
    assert res.is_valid is True
    assert res.status == "active"
    assert "jobs.lever.co/stripe" in res.final_url
    assert res.source == "lever"
    assert res.source_job_id == "12345678-abcd-1234-abcd-1234567890ab"


def test_redirect_to_careers_homepage():
    """Verify that an expired link redirecting to a generic careers page is rejected."""
    def handler(request: httpx.Request) -> httpx.Response:
        if "old-job" in str(request.url):
            return httpx.Response(
                302,
                headers={"Location": "https://company.com/careers"},
                request=request,
            )
        return httpx.Response(200, text="<h1>Careers at Company</h1>", request=request)

    transport = httpx.MockTransport(handler)

    async def run():
        async with httpx.AsyncClient(transport=transport, follow_redirects=True) as client:
            return await validate_job_url(
                "https://company.com/jobs/old-job-1234",
                company="Company",
                client=client,
            )

    res = asyncio.run(run())
    assert res.is_valid is False
    assert res.status == "generic_careers"
    assert "generic careers page" in res.rejection_reason


def test_expired_job_page():
    """Verify that a 200 response with 'position closed' text is rejected as expired."""
    html_content = """
    <html>
      <head><title>Job Closed</title></head>
      <body>
        <div class="alert">This position is closed and no longer accepting applications.</div>
      </body>
    </html>
    """
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, text=html_content, request=request)
    )

    async def run():
        async with httpx.AsyncClient(transport=transport) as client:
            return await validate_job_url(
                "https://company.com/jobs/sde-intern-555",
                company="Company",
                client=client,
            )

    res = asyncio.run(run())
    assert res.is_valid is False
    assert res.status == "expired"
    assert "closed" in res.rejection_reason or "no longer accepting" in res.rejection_reason


def test_ashby_job():
    """Verify Ashby exact job resolution and generic/expired rejection."""
    valid_html = """
    <html>
      <head><title>Software Engineer Intern @ Creatify</title></head>
      <body>
        <script>window.__appData = {"posting":{"title":"Software Engineer Intern"}};</script>
        <h1>Software Engineer Intern</h1>
      </body>
    </html>
    """
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, text=valid_html, request=request)
    )

    async def run_valid():
        async with httpx.AsyncClient(transport=transport) as client:
            return await validate_job_url(
                "https://jobs.ashbyhq.com/creatify/75a1f1ad-13d2-4513-952c-71b6dfcaa84f",
                company="Creatify",
                client=client,
            )

    valid_res = asyncio.run(run_valid())
    assert valid_res.is_valid is True
    assert valid_res.source == "ashby"
    assert valid_res.source_job_id == "75a1f1ad-13d2-4513-952c-71b6dfcaa84f"

    # Generic board URL must be rejected immediately without network call
    generic_res = asyncio.run(validate_job_url("https://jobs.ashbyhq.com/creatify"))
    assert generic_res.is_valid is False
    assert generic_res.status == "generic_careers"

    # Expired Ashby job with "posting":null
    expired_html = '<html><head><title>Jobs</title></head><body><script>window.__appData = {"posting":null};</script></body></html>'
    expired_transport = httpx.MockTransport(
        lambda request: httpx.Response(200, text=expired_html, request=request)
    )

    async def run_expired():
        async with httpx.AsyncClient(transport=expired_transport) as client:
            return await validate_job_url(
                "https://jobs.ashbyhq.com/creatify/00000000-0000-0000-0000-000000000000",
                client=client,
            )

    exp_res = asyncio.run(run_expired())
    assert exp_res.is_valid is False
    assert exp_res.status == "expired"


def test_lever_job():
    """Verify Lever exact job resolution and generic board rejection."""
    valid_html = "<html><head><title>Frontend Intern</title></head><body><a class='postings-btn' href='#'>Apply for this job</a></body></html>"
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, text=valid_html, request=request)
    )

    async def run_valid():
        async with httpx.AsyncClient(transport=transport) as client:
            return await validate_job_url(
                "https://jobs.lever.co/belvederetrading/10746b3d-1760-4573-9b63-b93f5a5e4fc0",
                company="Belvedere Trading",
                client=client,
            )

    valid_res = asyncio.run(run_valid())
    assert valid_res.is_valid is True
    assert valid_res.source == "lever"
    assert valid_res.source_job_id == "10746b3d-1760-4573-9b63-b93f5a5e4fc0"

    # Generic Lever board rejected
    generic_res = asyncio.run(validate_job_url("https://jobs.lever.co/belvederetrading"))
    assert generic_res.is_valid is False
    assert generic_res.status == "generic_careers"


def test_greenhouse_job():
    """Verify Greenhouse exact job resolution and error redirect rejection."""
    valid_html = "<html><head><title>ML Intern</title></head><body><form id='application_form'>Apply</form></body></html>"
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, text=valid_html, request=request)
    )

    async def run_valid():
        async with httpx.AsyncClient(transport=transport) as client:
            return await validate_job_url(
                "https://job-boards.greenhouse.io/cssmerge/jobs/8693034002",
                company="Atoms",
                client=client,
            )

    valid_res = asyncio.run(run_valid())
    assert valid_res.is_valid is True
    assert valid_res.source == "greenhouse"
    assert valid_res.source_job_id == "8693034002"

    # Greenhouse generic board / jobs listing rejected
    generic_res = asyncio.run(validate_job_url("https://boards.greenhouse.io/hackerrank/jobs"))
    assert generic_res.is_valid is False
    assert generic_res.status == "generic_careers"

    # Greenhouse error redirect rejected
    def error_redirect(request: httpx.Request) -> httpx.Response:
        if "error=true" in str(request.url):
            return httpx.Response(200, text="<html><body>No jobs found</body></html>", request=request)
        return httpx.Response(
            302,
            headers={"Location": "https://job-boards.greenhouse.io/cssmerge?error=true"},
            request=request,
        )
    err_transport = httpx.MockTransport(error_redirect)

    async def run_err():
        async with httpx.AsyncClient(transport=err_transport, follow_redirects=True) as client:
            return await validate_job_url(
                "https://job-boards.greenhouse.io/cssmerge/jobs/00000000",
                client=client,
            )

    err_res = asyncio.run(run_err())
    assert err_res.is_valid is False
    assert err_res.status in ("generic_careers", "expired")


def test_company_specific_job_page():
    """Verify company-specific career detail pages vs generic listings."""
    job_html = """
    <html>
      <head>
        <title>Software Engineering Intern - Tesla</title>
        <script type="application/ld+json">
          {"@context": "https://schema.org", "@type": "JobPosting", "title": "Software Engineering Intern"}
        </script>
      </head>
      <body>
        <h1>Software Engineering Intern</h1>
        <button>Apply Online</button>
      </body>
    </html>
    """
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, text=job_html, request=request)
    )

    async def run_job():
        async with httpx.AsyncClient(transport=transport) as client:
            return await validate_job_url(
                "https://www.tesla.com/careers/search/job/software-engineering-internship-12345",
                company="Tesla",
                client=client,
            )

    res = asyncio.run(run_job())
    assert res.is_valid is True
    assert res.is_individual_job is True

    # Generic careers homepage
    gen_res = asyncio.run(validate_job_url("https://www.tesla.com/careers"))
    assert gen_res.is_valid is False
    assert gen_res.status == "generic_careers"
