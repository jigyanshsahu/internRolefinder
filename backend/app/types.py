import enum


class RoleType(str, enum.Enum):
    sde = "sde"
    ai = "ai"
    other = "other"
