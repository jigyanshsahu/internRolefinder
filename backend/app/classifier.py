import re
from app.types import RoleType

INTERN_PATTERN = re.compile(r"\bintern(ship)?\b", re.I)
EXCLUDED_PATTERN = re.compile(r"\b(sr\.?|senior|staff|lead|principal|manager|director|experienced)\b", re.I)
NON_SOFTWARE_PATTERN = re.compile(
    r"\b(hardware|mechanical|electrical|electronics?|process planner|manufacturing|human resources|hr intern|recruiter|recruiting|sales|marketing|accounting|finance|legal|supply chain|procurement)\b",
    re.I,
)
SOFTWARE_TITLE_PATTERN = re.compile(
    r"\b(sde|swe|software (engineer|developer|development)|frontend (engineering|engineer|developer)|front[ -]?end (engineering|engineer|developer)|backend (engineering|engineer|developer)|back[ -]?end (engineering|engineer|developer)|full[ -]?stack (engineering|engineer|developer)|web engineer|web developer|application developer|mobile (engineer|developer)|game developer)\b",
    re.I,
)
AI_DOMAIN_PATTERN = re.compile(
    r"\b(ai|artificial intelligence|machine[ -]?learning|ml|deep learning|llm|large language models?|nlp|natural language processing|computer vision|generative ai|genai|robotics)\b",
    re.I,
)
def classify_role(title: str, text: str = "") -> RoleType | None:
    title_value = title.lower()
    if not INTERN_PATTERN.search(title_value):
        return None
    if EXCLUDED_PATTERN.search(title_value) or NON_SOFTWARE_PATTERN.search(title_value):
        return None
    has_software_title = SOFTWARE_TITLE_PATTERN.search(title_value) is not None
    if not has_software_title:
        return None
    if AI_DOMAIN_PATTERN.search(title_value):
        return RoleType.ai
    return RoleType.sde
