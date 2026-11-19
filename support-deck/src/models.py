from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class QueueStatus(str, Enum):
    pending = "pending"
    drafted = "drafted"
    approved = "approved"
    rejected = "rejected"
    not_covered = "not_covered"


class ApprovalActionType(str, Enum):
    docs_append = "docs_append"
    gmail_draft = "gmail_draft"
    reply_finalize = "reply_finalize"


class ApprovalStatus(str, Enum):
    pending_approval = "pending_approval"
    approved = "approved"
    rejected = "rejected"


class QueueItem(BaseModel):
    question_id: str
    question_text: str = ""
    status: QueueStatus = QueueStatus.pending
    draft: str | None = None
    citation_url: str | None = None
    routing_note: str | None = None
    searched: list[str] = Field(default_factory=list)
    reviewer_flags: list[str] = Field(default_factory=list)
    explainer_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ApprovalAction(BaseModel):
    action_id: str
    type: ApprovalActionType
    payload_preview: dict[str, Any] = Field(default_factory=dict)
    content_hash: str = ""
    status: ApprovalStatus = ApprovalStatus.pending_approval
    edited_content: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    decided_at: datetime | None = None


class FeeExplainer(BaseModel):
    explainer_id: str | None = None
    bullets: list[str]
    links: list[str]
    last_checked: date
    active: bool = True

    @field_validator("bullets")
    @classmethod
    def _cap_bullets(cls, value: list[str]) -> list[str]:
        if len(value) > 6:
            raise ValueError("FeeExplainer bullets must be ≤6")
        return value

    @field_validator("links")
    @classmethod
    def _exactly_two_links(cls, value: list[str]) -> list[str]:
        if len(value) != 2:
            raise ValueError("FeeExplainer links must have exactly 2 URLs")
        return value


class FrequencySignal(BaseModel):
    normalized_text: str
    count: int
    window_days: int = 7
    threshold: int = 5
    first_seen: datetime | None = None
    last_seen: datetime | None = None

    @model_validator(mode="after")
    def _count_non_negative(self) -> FrequencySignal:
        if self.count < 0:
            raise ValueError("count must be ≥0")
        return self
