import enum


class RoleType(str, enum.Enum):
    sde = "sde"
    frontend = "frontend"
    backend = "backend"
    full_stack = "full_stack"
