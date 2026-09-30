"""Buffer snapshots + exact time-buffer formula (original window scored)."""

from hollow_green import detectors
from hollow_green.schemas import BufferSnapshot, DeploymentEvent, ReleaseLog
from hollow_green.taxonomy import EventType


def _clamp(value: float, lo: float = -100.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def compute_buffers(log: ReleaseLog, events: list[DeploymentEvent]) -> BufferSnapshot:
    ordered = events
    retries = detectors.retries(ordered)
    n = len(retries)
    retries_left = max(0, log.retry_budget_max - n)
    if log.retry_budget_max > 0:
        retry_reserve_pct = retries_left / log.retry_budget_max * 100.0
    else:
        retry_reserve_pct = 100.0 if n == 0 else 0.0

    started = next(e for e in ordered if e.type == EventType.DEPLOY_STARTED.value)
    terminal = next(
        e
        for e in ordered
        if e.type
        in (
            EventType.DEPLOY_SUCCEEDED.value,
            EventType.DEPLOY_FAILED.value,
            EventType.DEPLOY_ROLLED_BACK.value,
        )
    )
    elapsed_min = (terminal.ts - started.ts).total_seconds() / 60.0
    original = float(log.window_minutes)
    extension_total = detectors.extension_total_min(ordered)
    effective = original + extension_total

    original_pct = _clamp(round((original - elapsed_min) / original * 100.0, 1))
    effective_pct = _clamp(round((effective - elapsed_min) / effective * 100.0, 1))

    cutoff = terminal.ts
    snaps = [e for e in detectors.snapshot_events(ordered) if e.ts <= cutoff]
    available = True
    fresh = True
    if snaps:
        last = max(snaps, key=lambda e: (e.ts, e.event_id))
        if last.type == EventType.ROLLBACK_UNAVAILABLE.value:
            available = False
            fresh = False
        elif last.type == EventType.ROLLBACK_SNAPSHOT_STALE.value:
            available = True
            fresh = False
        else:
            available = True
            fresh = True

    healths = [
        e
        for e in detectors.health_reports(ordered)
        if e.ts <= cutoff and e.details.get("status") in ("pass", "degraded", "fail")
    ]
    if healths:
        last_h = max(healths, key=lambda e: (e.ts, e.event_id))
        raw = last_h.details.get("status")
        health_end: str = raw if isinstance(raw, str) else "unknown"
    else:
        health_end = "unknown"

    manual_count = len(detectors.manual_overrides(ordered))

    return BufferSnapshot(
        retries_used=n,
        retries_left=retries_left,
        retry_reserve_pct=round(retry_reserve_pct, 1),
        time_remaining_original_pct=original_pct,
        time_remaining_effective_pct=effective_pct,
        extension_total_min=extension_total,
        rollback_available=available,
        rollback_fresh=fresh,
        health_end=health_end,  # type: ignore[arg-type]
        manual_count=manual_count,
    )
