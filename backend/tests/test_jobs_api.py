from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from sqlalchemy.dialects import postgresql

from app.main import company_seeds, jobs
from app.models import RoleType


def test_jobs_api_paginates_and_returns_dynamic_total_pages():
    db = Mock()
    db.scalar.return_value = 241
    db.scalars.return_value.all.return_value = []

    response = jobs(role_type=RoleType.frontend, page=2, page_size=100, db=db)

    assert response.page == 2
    assert response.page_size == 100
    assert response.total == 241
    assert response.total_pages == 3
    query = db.scalars.call_args.args[0]
    compiled_query = str(query.compile(dialect=postgresql.dialect()))
    assert "LIMIT" in compiled_query
    assert "OFFSET" in compiled_query
    assert "jobs.country" in compiled_query
    assert "jobs.is_remote" in compiled_query


def test_jobs_api_clamps_page_after_result_count_shrinks():
    db = Mock()
    db.scalar.return_value = 250
    db.scalars.return_value.all.return_value = []

    response = jobs(role_type="sde", page=99, page_size=100, db=db)

    assert response.page == 3
    assert response.total_pages == 3


def test_jobs_api_prioritizes_discovered_startup_boards():
    startup_board = Mock(platform="greenhouse", slug="early-stage-company")
    startup_boards_result = Mock()
    startup_boards_result.all.return_value = [startup_board]
    jobs_result = Mock()
    jobs_result.all.return_value = []
    db = Mock()
    db.scalar.return_value = 1
    db.scalars.side_effect = [startup_boards_result, jobs_result]

    jobs(role_type="sde", page=1, page_size=20, db=db)

    query = db.scalars.call_args.args[0]
    compiled = query.compile(dialect=postgresql.dialect())
    assert "jobs.source_url" in str(compiled)
    assert "early-stage-company" in str(compiled.params)
    statement = str(compiled)
    where_clause = statement.split("WHERE", 1)[1].split("ORDER BY", 1)[0]
    assert "jobs.source_url" not in where_clause
    ordering = statement.split("ORDER BY", 1)[1]
    assert ordering.index("jobs.is_remote") < ordering.index("jobs.source_url")


def test_jobs_api_can_filter_by_remote_only():
    db = Mock()
    db.scalar.return_value = 50
    db.scalars.return_value.all.return_value = []

    jobs(role_type="sde", remote_only=True, page=1, page_size=20, db=db)

    query = db.scalars.call_args.args[0]
    compiled = query.compile(dialect=postgresql.dialect())
    statement = str(compiled)
    where_clause = statement.split("WHERE", 1)[1].split("ORDER BY", 1)[0]
    assert "jobs.is_remote is true" in where_clause.lower() or "jobs.is_remote = true" in where_clause.lower()


def test_jobs_api_defaults_to_all_workplaces():
    db = Mock()
    db.scalar.return_value = 50
    db.scalars.return_value.all.return_value = []

    jobs(role_type="sde", remote_only=False, page=1, page_size=20, db=db)

    query = db.scalars.call_args.args[0]
    compiled = query.compile(dialect=postgresql.dialect())
    statement = str(compiled)
    where_clause = statement.split("WHERE", 1)[1].split("ORDER BY", 1)[0]
    assert "jobs.is_remote" not in where_clause.lower()


def test_company_seed_status_api_returns_source_and_freshness_fields():
    seed = SimpleNamespace(
        id=uuid4(),
        company_name="Drivetrain",
        website_url="https://www.drivetrain.ai",
        careers_url="https://jobs.lever.co/drivetrain",
        enabled=True,
        status="board_found",
        last_checked_at=None,
        last_error=None,
    )
    db = Mock()
    db.scalars.return_value.all.return_value = [seed]

    response = company_seeds(db)

    assert response[0].company_name == "Drivetrain"
    assert response[0].status == "board_found"
    assert str(response[0].careers_url) == "https://jobs.lever.co/drivetrain"


def test_jobs_api_sorts_by_direct_portal_first():
    db = Mock()
    db.scalar.return_value = 10
    db.scalars.return_value.all.return_value = []

    jobs(role_type="sde", sort_by="direct_portal", page=1, page_size=20, db=db)

    query = db.scalars.call_args.args[0]
    compiled = query.compile(dialect=postgresql.dialect())
    statement = str(compiled)
    ordering = statement.split("ORDER BY", 1)[1]
    # Check that direct portal condition is present in the first CASE clause of ORDER BY
    assert "jobs.apply_url" in ordering
    assert any("greenhouse" in str(v) for v in compiled.params.values())
    assert any("workday" in str(v) for v in compiled.params.values())


def test_invalidate_single_job():
    from app.main import invalidate_single_job
    mock_job = Mock(id=uuid4(), title="Test Intern", company="Acme", status="active")
    db = Mock()
    db.scalar.return_value = mock_job

    res = invalidate_single_job(job_id=mock_job.id, db=db)
    assert res["status"] == "ok"
    assert mock_job.status == "invalidated"
    db.commit.assert_called_once()


def test_redirect_to_career_page():
    from app.main import redirect_to_career_page
    mock_job = Mock(
        id=uuid4(),
        title="Frontend Intern",
        company="Swiggy",
        apply_url="https://careers.swiggy.com?role=frontend-intern",
        status="active",
    )
    db = Mock()
    db.scalar.return_value = mock_job

    res = redirect_to_career_page(job_id=mock_job.id, db=db)
    assert res.status_code == 307
    assert res.headers["location"] == "https://careers.swiggy.com"


def test_career_url_resolution():
    from app.career_urls import get_career_url
    assert get_career_url("Swiggy", "https://careers.swiggy.com/jobs/xyz") == "https://careers.swiggy.com"
    assert get_career_url("Razorpay", "https://razorpay.com/jobs?role=dev") == "https://razorpay.com/jobs"
    assert get_career_url(None, "https://jobs.ashbyhq.com/org123/456") == "https://jobs.ashbyhq.com/org123"
    assert get_career_url(None, "https://job-boards.greenhouse.io/natera/jobs/123") == "https://job-boards.greenhouse.io/natera"
    assert get_career_url(None, "https://jobs.lever.co/palantir/abc") == "https://jobs.lever.co/palantir"