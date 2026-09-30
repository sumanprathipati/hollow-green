"""Detectors: typed accessors over ordered events."""

from hollow_green.schemas import DeploymentEvent
from hollow_green.taxonomy import (
    AUTOMATED_ACTORS,
    ROLLBACK_EVENT_TYPES,
    EventType,
)


def by_type(events: list[DeploymentEvent], kind: EventType) -> list[DeploymentEvent]:
    return [e for e in events if e.type == kind.value]


def retries(events: list[DeploymentEvent]) -> list[DeploymentEvent]:
    return by_type(events, EventType.RETRY_ATTEMPT)


def automated_retries(events: list[DeploymentEvent]) -> list[DeploymentEvent]:
    return [e for e in retries(events) if e.actor in AUTOMATED_ACTORS]


def restarts(events: list[DeploymentEvent]) -> list[DeploymentEvent]:
    return by_type(events, EventType.SERVICE_RESTART)


def manual_overrides(events: list[DeploymentEvent]) -> list[DeploymentEvent]:
    return by_type(events, EventType.MANUAL_OVERRIDE)


def bypasses(events: list[DeploymentEvent]) -> list[DeploymentEvent]:
    return by_type(events, EventType.BYPASS)


def extensions(events: list[DeploymentEvent]) -> list[DeploymentEvent]:
    return by_type(events, EventType.WINDOW_EXTENDED)


def rollback_events(events: list[DeploymentEvent]) -> list[DeploymentEvent]:
    return [e for e in events if e.type in {t.value for t in ROLLBACK_EVENT_TYPES}]


def rollback_started(events: list[DeploymentEvent]) -> list[DeploymentEvent]:
    return by_type(events, EventType.ROLLBACK_STARTED)


def rollback_completed(events: list[DeploymentEvent]) -> list[DeploymentEvent]:
    return by_type(events, EventType.ROLLBACK_COMPLETED)


def health_reports(events: list[DeploymentEvent]) -> list[DeploymentEvent]:
    return by_type(events, EventType.HEALTH_REPORT)


def budget_exhausted_events(events: list[DeploymentEvent]) -> list[DeploymentEvent]:
    return by_type(events, EventType.BUDGET_EXHAUSTED)


def snapshot_events(events: list[DeploymentEvent]) -> list[DeploymentEvent]:
    kinds = {
        EventType.ROLLBACK_SNAPSHOT_READY.value,
        EventType.ROLLBACK_SNAPSHOT_STALE.value,
        EventType.ROLLBACK_UNAVAILABLE.value,
    }
    return [e for e in events if e.type in kinds]


def has_recovery_action(events: list[DeploymentEvent]) -> bool:
    kinds = {
        EventType.RETRY_ATTEMPT.value,
        EventType.SERVICE_RESTART.value,
        EventType.MANUAL_OVERRIDE.value,
        EventType.BYPASS.value,
        EventType.ROLLBACK_STARTED.value,
        EventType.ROLLBACK_COMPLETED.value,
        EventType.WINDOW_EXTENDED.value,
    }
    return any(e.type in kinds for e in events)


def extension_total_min(events: list[DeploymentEvent]) -> float:
    total = 0.0
    for e in extensions(events):
        raw = e.details.get("extension_minutes", 0)
        if isinstance(raw, (int, float)) and not isinstance(raw, bool):
            total += float(raw)
    return total
