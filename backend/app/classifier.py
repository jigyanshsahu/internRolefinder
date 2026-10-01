import re
from app.models import RoleType

INTERN_OR_FRESHER_PATTERN = re.compile(
    r"\b(intern(ship)?|co[ -]?op|freshers?|new grad(uate)?|graduate( trainee| engineer| program)?|entry[ -]?level|early[ -]career)\b",
    re.I,
)
EXCLUDED_PATTERN = re.compile(r"\b(sr\.?|senior|staff|lead|principal|manager|director|experienced)\b", re.I)
NON_SOFTWARE_PATTERN = re.compile(
    r"\b(hardware|mechanical|electrical|electronics?|process planner|manufacturing|human resources|hr intern|recruiter|recruiting|sales|marketing|accounting|finance|legal|supply chain|procurement)\b",
    re.I,
)
SOFTWARE_TITLE_PATTERN = re.compile(
    r"\b(sde|swe|software|developer|development|backend|back[ -]?end|frontend|front[ -]?end|full[ -]?stack|web engineer|web developer|devops|platform engineer|site reliability|data engineer|mobile engineer|forward deployed)\b",
    re.I,
)
AI_PATTERN = re.compile(
    r"\b(ai|artificial intelligence|machine[ -]?learning|ml|deep learning|llm|large language models?|nlp|natural language processing|computer vision|generative ai|genai|data scientist|robotics|forward deployed)\b",
    re.I,
)
def classify_role(title: str, text: str = "") -> RoleType | None:
    title_value = title.lower()
    value = f"{title} {text}".lower()
    if not INTERN_OR_FRESHER_PATTERN.search(value):
        return None
    if EXCLUDED_PATTERN.search(title_value) or NON_SOFTWARE_PATTERN.search(title_value):
        return None
    if not SOFTWARE_TITLE_PATTERN.search(title_value) and not AI_PATTERN.search(title_value):
        return None
    if AI_PATTERN.search(value):
        return RoleType.ai
    return RoleType.sde
