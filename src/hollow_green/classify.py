"""Release classification. Order: failed, rollback, then success tiers."""

from hollow_green import detectors
from hollow_green.schemas import DeploymentEvent
from hollow_green.taxonomy import EventType

CLEAN_RESERVE_MIN = 80
FRAGILE_RESERVE_MAX = 49
FRAGILE_MANUAL_MIN = 2


def classify(
    terminal_kind: str,
    reserve: int,
    health_end: str,
    rollback_available: bool,
    manual_count: int,
    events: list[DeploymentEvent],
) -> str:
    if terminal_kind == "failed":
        return "failed"
    if terminal_kind == "rolled_back":
        return "rollback"
    bypass_count = len([e for e in events if e.type == EventType.BYPASS.value])
    recovery_present = detectors.has_recovery_action(events)
    if (
        not recovery_present
        and reserve >= CLEAN_RESERVE_MIN
        and health_end == "pass"
        and rollback_available
        and manual_count == 0
    ):
        return "clean_success"
    if (
        reserve <= FRAGILE_RESERVE_MAX
        or health_end != "pass"
        or not rollback_available
        or manual_count >= FRAGILE_MANUAL_MIN
        or bypass_count >= 1
    ):
        return "fragile_success"
    return "recovered_success"
