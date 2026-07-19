from typing import Any

from pydantic import BaseModel


class RoleConfig(BaseModel):
    backend: str
    handle: str # model name
    max_tokens: int | None = None
    timeout_seconds: int | None = None


class StageConfig(BaseModel):
    cognition: dict[str, Any]  # tighten these two later, same pattern
    search: dict[str, Any]
    roles: dict[str, RoleConfig]
