import pytest
from app.classifier import classify_role
from app.types import RoleType


def test_classifies_frontend_internship():
    assert classify_role("Frontend Engineering Intern") == RoleType.frontend
    assert classify_role("Software Engineer Intern, Frontend") == RoleType.frontend
    assert classify_role("Web Engineer Intern") == RoleType.frontend


def test_classifies_backend_internship():
    assert classify_role("Backend Engineering Intern") == RoleType.backend
    assert classify_role("Software Developer Intern, Backend") == RoleType.backend
    assert classify_role("Software Engineer Intern - Infrastructure") == RoleType.backend


def test_classifies_fullstack_internship():
    assert classify_role("Fullstack Engineer Intern") == RoleType.full_stack
    assert classify_role("Full-Stack Developer Intern") == RoleType.full_stack
    assert classify_role("Software Engineer Intern, Fullstack (Summer 2027)") == RoleType.full_stack


def test_classifies_sde_internship():
    assert classify_role("Software Development Engineer Intern") == RoleType.sde
    assert classify_role("Software Engineer Intern") == RoleType.sde
    assert classify_role("Forward Deployed Software Engineer, Internship") == RoleType.sde
    assert classify_role("Software Engineer Intern, AI") == RoleType.sde


def test_rejects_senior_role():
    assert classify_role("Senior Backend Engineer") is None


def test_rejects_senior_internship():
    assert classify_role("Senior Backend Engineer Intern") is None


def test_rejects_non_developer_internships():
    assert classify_role("Machine Learning Intern") is None
    assert classify_role("Data Scientist Intern") is None
    assert classify_role("AI Intern") is None
    assert classify_role("Machine Learning Engineer Intern") is None


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
    "Lead Software Engineer Intern",
    "Principal Software Engineer Intern",
    "Staff Software Engineer Intern",
    "Software Architect Intern",
    "Director of Software Engineering Intern",
    "VP Software Engineering Intern",
    "Software Engineer II Intern",
    "Software Engineer III Intern",
])
def test_rejects_non_software_and_senior_internships(title):
    assert classify_role(title) is None


def test_rejects_internship_with_senior_metadata():
    assert classify_role("Software Engineer Intern", "Senior level") is None
    assert classify_role("Software Engineer Intern", "Director of engineering") is None


def test_rejects_generic_engineering_internship_without_software_signal():
    assert classify_role("Engineer Intern") is None
