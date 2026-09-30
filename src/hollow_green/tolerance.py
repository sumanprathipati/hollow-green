"""Second-failure tolerance with rollback visibility."""

from hollow_green.schemas import BufferSnapshot, RollbackSummary, ToleranceReport


def compute_tolerance(
    reserve: int,
    buffers: BufferSnapshot,
    rollback_summary: RollbackSummary,
) -> ToleranceReport:
    health = buffers.health_end
    available = buffers.rollback_available
    left = buffers.retries_left
    rationale: list[str] = []

    if reserve < 25:
        level = "critical"
        rationale.append(f"reserve {reserve} < 25")
    elif health == "fail":
        level = "critical"
        rationale.append("health fail at end")
    elif not available and left == 0:
        level = "critical"
        rationale.append("rollback unavailable and no retries left")
    elif not available:
        level = "low"
        rationale.append("rollback unavailable at end")
    elif reserve < 50:
        level = "low"
        rationale.append(f"reserve {reserve} < 50")
    elif health == "degraded":
        level = "low"
        rationale.append("health degraded at end")
    elif left == 0:
        level = "low"
        rationale.append("no retries left")
    elif 50 <= reserve <= 69:
        level = "medium"
        rationale.append(f"reserve {reserve} in 50-69")
    elif left == 1:
        level = "medium"
        rationale.append("one retry left")
    elif reserve >= 70 and left >= 2 and available and health == "pass":
        level = "high"
        rationale.append(f"reserve {reserve} >= 70, retries_left {left}")
    elif health == "unknown":
        level = "low"
        rationale.append("health unknown at end")
    else:
        level = "medium"
        rationale.append(f"reserve {reserve}, retries_left {left}")

    if rollback_summary.executed:
        ids = ", ".join(rollback_summary.event_ids) or "rollback"
        if rollback_summary.verified:
            rationale.append(f"rollback executed {ids}, verified by health pass")
        else:
            rationale.append(f"rollback executed {ids}, unverified")

    can_survive = level in ("high", "medium")
    return ToleranceReport(
        level=level,  # type: ignore[arg-type]
        retries_left=left,
        can_survive_second_failure=can_survive,
        rationale=rationale,
    )
