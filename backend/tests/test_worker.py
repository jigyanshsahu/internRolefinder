from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock

from sqlalchemy.dialects import postgresql

from app.models import RoleType
from app.worker import _upsert_discovered_jobs, purge_stale_jobs


def test_expiration_deletes_jobs_older_than_verification_cutoff():
    cutoff = datetime(2026, 10, 1, tzinfo=timezone.utc)
    result = Mock(rowcount=4)
    db = Mock()
    db.execute.return_value = result

    assert purge_stale_jobs(db, cutoff) == 4

    statement = db.execute.call_args.args[0]
    compiled = statement.compile(dialect=postgresql.dialect())
    assert "DELETE FROM jobs" in str(compiled)
    assert "jobs.last_checked_at <" in str(compiled)
    assert compiled.params["last_checked_at_1"] == cutoff


def test_discovered_jobs_use_conflict_safe_upsert_and_deduplicate_urls():
    job = SimpleNamespace(
        title="Software Engineer Intern",
        company="Example",
        location="Remote",
        country=None,
        is_remote=True,
        role_type=RoleType.sde,
        apply_url="HTTPS://EXAMPLE.COM/jobs/1/",
        source_url="https://jobs.example.com",
    )
    db = Mock()
    db.scalars.return_value.all.return_value = []

    assert _upsert_discovered_jobs(db, [job, job]) == 1

    statement = db.execute.call_args.args[0]
    compiled = statement.compile(dialect=postgresql.dialect())
    assert "ON CONFLICT (apply_url) DO UPDATE" in str(compiled)
    assert compiled.params.get("apply_url_m0") == "https://example.com/jobs/1"