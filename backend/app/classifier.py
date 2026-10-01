import re
from app.models import RoleType

INTERN_OR_FRESHER_PATTERN = re.compile(
    r"\b(intern(ship)?|co[ -]?op|freshers?|new grad(uate)?|graduate( trainee| engineer| program)?|entry[ -]?level|early[ -]career)\b",
    re.I,
)
EXCLUDED_PATTERN = re.compile(r"\b(senior|staff|lead|principal|manager|director|experienced)\b", re.I)
AI_PATTERN = re.compile(
    r"\b(ai|artificial intelligence|machine[ -]?learning|ml|deep learning|llm|large language models?|nlp|natural language processing|computer vision|generative ai|genai|data scientist|robotics)\b",
    re.I,
)
SDE_PATTERN = re.compile(
    r"\b(sde|swe|software|developer|development|engineer|backend|back[ -]?end|frontend|front[ -]?end|full[ -]?stack|web engineer|web developer|devops|platform engineer|site reliability|data engineer|mobile engineer)\b",
    re.I,
)


def classify_role(title: str, text: str = "") -> RoleType | None:
    value = f"{title} {text}".lower()
    if not INTERN_OR_FRESHER_PATTERN.search(value) or EXCLUDED_PATTERN.search(value):
        return None
    if AI_PATTERN.search(value):
        return RoleType.ai
    if SDE_PATTERN.search(value):
        return RoleType.sde
    return RoleType.other
