import pytest
from app.classifier import classify_role
from app.types import RoleType


def test_classifies_frontend_internship_as_sde():
    assert classify_role("Frontend Engineering Intern") == RoleType.sde


def test_rejects_senior_role():
    assert classify_role("Senior Backend Engineer") is None


def test_rejects_senior_internship():
    assert classify_role("Senior Backend Engineer Intern") is None


def test_classifies_sde():
    assert classify_role("Software Development Engineer Intern") == RoleType.sde


def test_classifies_software_engineering_internship_in_ai_area():
    assert classify_role("Software Engineer Intern, AI") == RoleType.ai


def test_rejects_non_developer_ai_internships():
    assert classify_role("Machine Learning Intern") is None
    assert classify_role("Data Scientist Intern") is None
    assert classify_role("AI Intern") is None
    assert classify_role("Machine Learning Engineer Intern") is None


def test_classifies_forward_deployed_engineering_as_ai():
    assert classify_role("Forward Deployed Software Engineer, Internship") == RoleType.sde


def test_rejects_non_software_fresher():
    assert classify_role("Marketing Fresher") is None


def test_rejects_business_development_internship():
    assert classify_role("Business Development Intern") is None


def test_rejects_regular_full_time_role():
    assert classify_role("Software Engineer") is None


def test_rejects_entry_level_software_role_without_internship():
    assert classify_role("Software Engineer", "Entry-level") is None


def test_rejects_coop_software_role_without_internship():
    assert classify_role("Software Engineer Co-op") is None


def test_requires_internship_in_title_even_when_metadata_mentions_it():
    assert classify_role("Software Engineer", "Internship") is None


@pytest.mark.parametrize("title", [
    "Hardware Engineer Intern",
    "Embedded Hardware Intern",
    "HR Intern",
    "Human Resources Intern",
    "Process Planner Intern",
    "Robotics Intern",
    "Data Engineer Intern",
    "DevOps Intern",
    "Sr. Software Engineer Intern",
    "Senior Software Engineer Intern",
])
def test_rejects_non_software_and_senior_internships(title):
    assert classify_role(title) is None


def test_rejects_generic_engineering_internship_without_software_signal():
    assert classify_role("Engineer Intern") is None
