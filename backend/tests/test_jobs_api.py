from unittest.mock import Mock

from sqlalchemy.dialects import postgresql

from app.main import jobs
from app.models import RoleType


def test_jobs_api_paginates_and_returns_dynamic_total_pages():
    db = Mock()
    db.scalar.return_value = 241
    db.scalars.return_value.all.return_value = []

    response = jobs(role_type=RoleType.ai, page=2, page_size=100, db=db)

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
    assert "jobs.source_url" not in str(compiled).split("ORDER BY")[0]