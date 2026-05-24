"""Unified data models for the runtime engine."""
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class TaskStatus(str, Enum):
    PENDING = "pending"
    AUTHENTICATING = "authenticating"
    FETCHING = "fetching"
    SENDING = "sending"
    DONE = "done"
    FAILED = "failed"


class HealthStatus(str, Enum):
    OK = "ok"
    WARNING = "warning"
    BANNED = "banned"


@dataclass
class AuthResult:
    success: bool
    session: dict = field(default_factory=dict)
    expire_at: Optional[str] = None
    error: str = ""


@dataclass
class Room:
    id: str
    name: str
    type: str  # "voice" or "video"
    audience_count: int = 0
    raw: dict = field(default_factory=dict)


@dataclass
class User:
    app_uid: str
    name: str
    room_id: str
    room_type: str  # "voice" or "video"
    rank: int
    gender: Optional[str] = None  # "male" / "female" / None
    score: Optional[int] = None
    extra: dict = field(default_factory=dict)
    raw: dict = field(default_factory=dict)


@dataclass
class Message:
    body: str
    template_vars: dict = field(default_factory=dict)

    def render(self) -> str:
        return self.body.format(**self.template_vars)


@dataclass
class SendResult:
    success: bool
    error_code: str = ""
    error_msg: str = ""
    cost_ms: int = 0
    raw: dict = field(default_factory=dict)


@dataclass
class TaskConfig:
    app: str
    account_id: int
    filters: dict = field(default_factory=dict)
    message_template_ids: list[int] = field(default_factory=list)
