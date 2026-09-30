"""Closed event taxonomy for Phase 1. Unknown types are rejected."""

from enum import StrEnum


class EventType(StrEnum):
    DEPLOY_STARTED = "deploy_started"
    DEPLOY_PROGRESS = "deploy_progress"
    HEALTH_REPORT = "health_report"
    DEPLOY_SUCCEEDED = "deploy_succeeded"
    DEPLOY_FAILED = "deploy_failed"
    DEPLOY_ROLLED_BACK = "deploy_rolled_back"
    RETRY_ATTEMPT = "retry_attempt"
    SERVICE_RESTART = "service_restart"
    MANUAL_OVERRIDE = "manual_override"
    BYPASS = "bypass"
    ROLLBACK_STARTED = "rollback_started"
    ROLLBACK_COMPLETED = "rollback_completed"
    ROLLBACK_SNAPSHOT_READY = "rollback_snapshot_ready"
    ROLLBACK_SNAPSHOT_STALE = "rollback_snapshot_stale"
    ROLLBACK_UNAVAILABLE = "rollback_unavailable"
    BUDGET_EXHAUSTED = "budget_exhausted"
    WINDOW_EXTENDED = "window_extended"


TERMINAL_TYPES = frozenset(
    {
        EventType.DEPLOY_SUCCEEDED,
        EventType.DEPLOY_FAILED,
        EventType.DEPLOY_ROLLED_BACK,
    }
)

RECOVERY_ACTION_TYPES = frozenset(
    {
        EventType.RETRY_ATTEMPT,
        EventType.SERVICE_RESTART,
        EventType.MANUAL_OVERRIDE,
        EventType.BYPASS,
        EventType.ROLLBACK_STARTED,
        EventType.ROLLBACK_COMPLETED,
        EventType.WINDOW_EXTENDED,
    }
)

ROLLBACK_EVENT_TYPES = frozenset(
    {
        EventType.ROLLBACK_STARTED,
        EventType.ROLLBACK_COMPLETED,
    }
)

AUTOMATED_ACTORS = frozenset({"system", "pipeline"})

TERMINAL_TO_LABEL = {
    EventType.DEPLOY_SUCCEEDED: "succeeded",
    EventType.DEPLOY_FAILED: "failed",
    EventType.DEPLOY_ROLLED_BACK: "rolled_back",
}
