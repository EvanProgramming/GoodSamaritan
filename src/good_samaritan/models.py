from __future__ import annotations
from datetime import datetime, timezone
from enum import StrEnum
from pydantic import BaseModel, Field

class Status(StrEnum):
    DISCOVERED="DISCOVERED"; SKIPPED="SKIPPED"; SELECTED="SELECTED"; CLONING="CLONING"; ANALYZING="ANALYZING"; EDITING="EDITING"; TESTING="TESTING"; REVIEWING="REVIEWING"; READY="READY"; PR_CREATED="PR_CREATED"; FAILED="FAILED"

class Issue(BaseModel):
    repository: str; number: int; title: str; body: str = ""; labels: list[str] = Field(default_factory=list)
    comments: list[str] = Field(default_factory=list); assignee: str | None = None; has_open_pr: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Assessment(BaseModel):
    clear: bool; small_scope: bool; expected_behavior: bool; safe: bool; confidence: float = Field(ge=0, le=1)
    reasoning: str = ""

class Candidate(BaseModel):
    issue: Issue; score: float; reasons: list[str]; assessment: Assessment | None = None

class CommandResult(BaseModel):
    command: str; exit_code: int; output: str

class ModelReply(BaseModel):
    provider: str; model: str; content: str; estimated_tokens: int = 0
