import pytest
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


def test_classifies_forward_deployed_engineering_as_ai():
    assert classify_role("Forward Deployed Software Engineer, Internship") == RoleType.ai


def test_rejects_non_software_fresher():
    assert classify_role("Marketing Fresher") is None


def test_rejects_regular_full_time_role():
    assert classify_role("Software Engineer") is None


def test_classifies_entry_level_from_job_metadata():
    assert classify_role("Software Engineer", "Entry-level") == RoleType.sde


@pytest.mark.parametrize("title", [
    "Hardware Engineer Intern",
    "Embedded Hardware Intern",
    "HR Intern",
    "Human Resources Intern",
    "Process Planner Intern",
    "Sr. Software Engineer Intern",
    "Senior Software Engineer Intern",
])
def test_rejects_non_software_and_senior_internships(title):
    assert classify_role(title) is None


def test_rejects_generic_engineering_internship_without_software_signal():
    assert classify_role("Engineer Intern") is None
