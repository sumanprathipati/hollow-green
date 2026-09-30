"""Pydantic v2 schemas. Terminology: RecoveryFollowUp, Reserve Level, Recovery Load."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

SchemaVersion = Literal["1.0"]
Actor = Literal["system", "pipeline", "human", "monitor"]
Severity = Literal["info", "warn", "error"]
HealthEnd = Literal["pass", "degraded", "fail", "unknown"]
RecoveryLoad = Literal["low", "medium", "high", "critical"]
FollowUpKind = Literal[
    "retry", "restart", "manual_override", "bypass", "rollback", "window_extension"
]
FollowUpStatus = Literal["open", "completed", "verified"]
FollowUpSeverity = Literal["low", "medium", "high", "critical"]
Classification = Literal[
    "clean_success", "recovered_success", "fragile_success", "rollback", "failed"
]
Terminal = Literal["succeeded", "rolled_back", "failed"]
ToleranceLevel = Literal["high", "medium", "low", "critical"]


class DeploymentEvent(BaseModel):
    event_id: str = Field(min_length=1)
    release_id: str = Field(min_length=1)
    ts: datetime
    type: str
    actor: Actor
    severity: Severity = "info"
    details: dict[str, str | int | float | bool] = Field(default_factory=dict)


class ReleaseLog(BaseModel):
    schema_version: SchemaVersion
    release_id: str = Field(min_length=1)
    service: str = Field(min_length=1)
    window_minutes: int = Field(gt=0)
    retry_budget_max: int = Field(ge=0)
    events: list[DeploymentEvent] = Field(min_length=1)


class BufferSnapshot(BaseModel):
    retries_used: int = Field(ge=0)
    retries_left: int = Field(ge=0)
    retry_reserve_pct: float = Field(ge=0, le=100)
    time_remaining_original_pct: float
    time_remaining_effective_pct: float
    extension_total_min: float = Field(ge=0)
    rollback_available: bool
    rollback_fresh: bool
    health_end: HealthEnd
    manual_count: int = Field(ge=0)


class Deduction(BaseModel):
    rule_id: str = Field(min_length=1)
    event_ids: list[str] = Field(min_length=1)
    points: int = Field(gt=0)
    reason: str


class ScoreReport(BaseModel):
    reserve_level: int = Field(ge=0, le=100)
    recovery_load: RecoveryLoad
    deductions: list[Deduction] = Field(default_factory=list)
    buffers: BufferSnapshot


class RecoveryFollowUp(BaseModel):
    follow_up_id: str = Field(min_length=1)
    kind: FollowUpKind
    event_ids: list[str] = Field(min_length=1)
    severity: FollowUpSeverity
    required_action: str = Field(min_length=1)
    status: FollowUpStatus = "open"


class RollbackSummary(BaseModel):
    executed: bool
    event_ids: list[str] = Field(default_factory=list)
    verified: bool = False
    manual: bool = False


class ToleranceReport(BaseModel):
    level: ToleranceLevel
    retries_left: int = Field(ge=0)
    can_survive_second_failure: bool
    rationale: list[str] = Field(default_factory=list)


class ReleaseReport(BaseModel):
    release_id: str
    classification: Classification
    terminal: Terminal
    score: ScoreReport
    follow_ups: list[RecoveryFollowUp] = Field(default_factory=list)
    rollback_summary: RollbackSummary
    tolerance: ToleranceReport
