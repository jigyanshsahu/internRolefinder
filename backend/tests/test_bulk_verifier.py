from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4
from app.services.bulk_verifier import deduplicate_jobs


def test_deduplicate_jobs_removes_identical_urls_and_roles():
    id1 = uuid4()
    id2 = uuid4()
    id3 = uuid4()

    job1 = SimpleNamespace(
        id=id1,
        company="Acme Corp",
        title="Software Engineer Intern",
        location="Remote",
        apply_url="https://jobs.ashbyhq.com/acme/111",
        last_checked_at=100,
    )
    # Duplicate URL
    job2 = SimpleNamespace(
        id=id2,
        company="Acme Corp",
        title="Software Engineer Intern",
        location="Remote",
        apply_url="https://jobs.ashbyhq.com/acme/111?source=web",
        last_checked_at=90,
    )
    # Distinct job
    job3 = SimpleNamespace(
        id=id3,
        company="Acme Corp",
        title="Frontend Intern",
        location="Remote",
        apply_url="https://jobs.ashbyhq.com/acme/222",
        last_checked_at=100,
    )

    db = Mock()
    db.scalars.return_value.all.return_value = [job1, job2, job3]

    removed = deduplicate_jobs(db)
    assert removed == 1
    db.execute.assert_called_once()
    db.commit.assert_called_once()
