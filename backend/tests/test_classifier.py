from app.classifier import classify_role
from app.models import RoleType


def test_classifies_frontend_internship_as_sde():
    assert classify_role("Frontend Engineering Intern") == RoleType.sde


def test_rejects_senior_role():
    assert classify_role("Senior Backend Engineer") is None


def test_rejects_senior_internship():
    assert classify_role("Senior Backend Engineer Intern") is None


def test_classifies_sde():
    assert classify_role("Software Development Engineer Intern") == RoleType.sde


def test_classifies_ai_internship():
    assert classify_role("Machine Learning Intern") == RoleType.ai


def test_classifies_non_engineering_fresher_as_other():
    assert classify_role("Marketing Fresher") == RoleType.other


def test_rejects_regular_full_time_role():
    assert classify_role("Software Engineer") is None


def test_classifies_entry_level_from_job_metadata():
    assert classify_role("Software Engineer", "Entry-level") == RoleType.sde
