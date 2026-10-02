import re
from app.types import RoleType

INTERN_PATTERN = re.compile(r"\bintern(ship)?\b", re.I)
EXCLUDED_PATTERN = re.compile(r"\b(sr\.?|senior|staff|lead|principal|manager|director|experienced)\b", re.I)
NON_SOFTWARE_PATTERN = re.compile(
    r"\b(hardware|mechanical|electrical|electronics?|process planner|manufacturing|human resources|hr intern|recruiter|recruiting|sales|marketing|accounting|finance|legal|supply chain|procurement)\b",
    re.I,
)
SOFTWARE_TITLE_PATTERN = re.compile(
    r"\b(sde|swe|software (engineer|developer|development)|frontend (engineering|engineer|developer)|front[ -]?end (engineering|engineer|developer)|backend (engineering|engineer|developer)|back[ -]?end (engineering|engineer|developer)|full[ -]?stack (engineering|engineer|developer)|web engineer|web developer|web development|application developer|mobile (engineer|developer)|game developer|embedded software|systems? (engineer|developer))\b",
    re.I,
)

FULLSTACK_PATTERN = re.compile(r"\b(full[ -]?stack)\b", re.I)
FRONTEND_PATTERN = re.compile(
    r"\b(front[ -]?end|frontend|ui|web developer|web engineer|web development|web intern|client[ -]?side)\b",
    re.I,
)
BACKEND_PATTERN = re.compile(
    r"\b(back[ -]?end|backend|infrastructure|distributed systems?|server|api|platform engineering)\b",
    re.I,
)


def classify_role(title: str, text: str = "") -> RoleType | None:
    title_value = title.lower()
    if not INTERN_PATTERN.search(title_value):
        return None
    if EXCLUDED_PATTERN.search(title_value) or NON_SOFTWARE_PATTERN.search(title_value):
        return None
    if not SOFTWARE_TITLE_PATTERN.search(title_value):
        return None

    if FULLSTACK_PATTERN.search(title_value):
        return RoleType.full_stack
    if FRONTEND_PATTERN.search(title_value):
        return RoleType.frontend
    if BACKEND_PATTERN.search(title_value):
        return RoleType.backend
    return RoleType.sde
