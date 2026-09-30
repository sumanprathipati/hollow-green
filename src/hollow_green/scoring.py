"""Deterministic scoring: Reserve Level (only numeric score) + Recovery Load label."""

from hollow_green import detectors
from hollow_green.schemas import (
    BufferSnapshot,
    Deduction,
    DeploymentEvent,
    ReleaseLog,
    ScoreReport,
)
from hollow_green.taxonomy import EventType

RETRY_FIRST = 6
RETRY_REPEAT = 12
RETRY_CAP = 60
RETRY_EXHAUSTED_PENALTY = 15
RESTART_POINTS = 15
MANUAL_POINTS = 20
BYPASS_POINTS = 25
ROLLBACK_MISSING_POINTS = 25
ROLLBACK_STALE_POINTS = 10
HEALTH_DEGRADED_POINTS = 20
HEALTH_FAILED_POINTS = 40
TIME_LOW_POINTS = 15
TIME_CRITICAL_EXTRA_POINTS = 10
CLEAN_RESERVE_MIN = 80
FRAGILE_RESERVE_MAX = 49


def recovery_load_for(reserve: int) -> str:
    if reserve >= 80:
        return "low"
    if reserve >= 50:
        return "medium"
    if reserve >= 25:
        return "high"
    return "critical"


def _terminal_event(events: list[DeploymentEvent]) -> DeploymentEvent:
    kinds = {
        EventType.DEPLOY_SUCCEEDED.value,
        EventType.DEPLOY_FAILED.value,
        EventType.DEPLOY_ROLLED_BACK.value,
    }
    for e in events:
        if e.type in kinds:
            # ordered input: single terminal guaranteed by ingest; take the one
            # present (events are pre-sorted, exactly one exists).
            pass
    matches = [e for e in events if e.type in kinds]
    return matches[0]


def compute_deductions(
    log: ReleaseLog,
    events: list[DeploymentEvent],
    buffers: BufferSnapshot,
    terminal_kind: str,
) -> list[Deduction]:
    deductions: list[Deduction] = []
    ordered = events

    retry_list = detectors.retries(ordered)
    n = len(retry_list)
    if n > 0:
        auto = [e for e in retry_list if e.actor in ("system", "pipeline")]
        if terminal_kind == "succeeded" and auto:
            points = min(RETRY_CAP, RETRY_FIRST + RETRY_REPEAT * (n - 1))
            reason = f"{n} retries: first 6 + {n - 1}x12, capped at 60"
        else:
            points = min(RETRY_CAP, RETRY_REPEAT * n)
            reason = f"{n} retries x12 (no first-retry discount), capped at 60"
        deductions.append(
            Deduction(
                rule_id="retry.consume",
                event_ids=[e.event_id for e in retry_list],
                points=points,
                reason=reason,
            )
        )
        exhausted_by_count = log.retry_budget_max > 0 and n >= log.retry_budget_max
        exhausted_by_zero = log.retry_budget_max == 0 and n > 0
        budget_marks = detectors.budget_exhausted_events(ordered)
        if exhausted_by_count or exhausted_by_zero or budget_marks:
            if budget_marks:
                ids = [budget_marks[0].event_id]
                reason_b = "retry budget exhausted marker"
            else:
                ids = [retry_list[-1].event_id]
                reason_b = "retry budget exhausted by count"
            deductions.append(
                Deduction(
                    rule_id="retry.budget_exhausted",
                    event_ids=ids,
                    points=RETRY_EXHAUSTED_PENALTY,
                    reason=reason_b,
                )
            )

    restart_list = detectors.restarts(ordered)
    if restart_list:
        deductions.append(
            Deduction(
                rule_id="restart.consume",
                event_ids=[e.event_id for e in restart_list],
                points=RESTART_POINTS * len(restart_list),
                reason=f"{len(restart_list)} restarts x15",
            )
        )

    manual_list = detectors.manual_overrides(ordered)
    if manual_list:
        deductions.append(
            Deduction(
                rule_id="manual.consume",
                event_ids=[e.event_id for e in manual_list],
                points=MANUAL_POINTS * len(manual_list),
                reason=f"{len(manual_list)} manual overrides x20",
            )
        )

    bypass_list = detectors.bypasses(ordered)
    if bypass_list:
        deductions.append(
            Deduction(
                rule_id="bypass.consume",
                event_ids=[e.event_id for e in bypass_list],
                points=BYPASS_POINTS * len(bypass_list),
                reason=f"{len(bypass_list)} bypasses x25",
            )
        )

    if not buffers.rollback_available:
        snaps = detectors.snapshot_events(ordered)
        ids = [snaps[-1].event_id] if snaps else [_terminal_event(ordered).event_id]
        deductions.append(
            Deduction(
                rule_id="rollback.missing",
                event_ids=ids,
                points=ROLLBACK_MISSING_POINTS,
                reason="rollback unavailable at end",
            )
        )
    elif not buffers.rollback_fresh:
        snaps = [
            e
            for e in detectors.snapshot_events(ordered)
            if e.type == EventType.ROLLBACK_SNAPSHOT_STALE.value
        ]
        ids = [snaps[-1].event_id] if snaps else [_terminal_event(ordered).event_id]
        deductions.append(
            Deduction(
                rule_id="rollback.stale",
                event_ids=ids,
                points=ROLLBACK_STALE_POINTS,
                reason="rollback snapshot stale at end",
            )
        )

    if buffers.health_end == "degraded":
        healths = detectors.health_reports(ordered)
        ids = [healths[-1].event_id] if healths else [_terminal_event(ordered).event_id]
        deductions.append(
            Deduction(
                rule_id="health.degraded_end",
                event_ids=ids,
                points=HEALTH_DEGRADED_POINTS,
                reason="health degraded at end",
            )
        )
    elif buffers.health_end == "fail":
        healths = detectors.health_reports(ordered)
        ids = [healths[-1].event_id] if healths else [_terminal_event(ordered).event_id]
        deductions.append(
            Deduction(
                rule_id="health.failed_end",
                event_ids=ids,
                points=HEALTH_FAILED_POINTS,
                reason="health failed at end",
            )
        )

    if buffers.time_remaining_original_pct < 20:
        started = next(e for e in ordered if e.type == EventType.DEPLOY_STARTED.value)
        term = _terminal_event(ordered)
        deductions.append(
            Deduction(
                rule_id="time.low",
                event_ids=[started.event_id, term.event_id],
                points=TIME_LOW_POINTS,
                reason=(
                    "time remaining on original window "
                    f"{buffers.time_remaining_original_pct}% < 20%"
                ),
            )
        )
        if buffers.time_remaining_original_pct < 10:
            deductions.append(
                Deduction(
                    rule_id="time.critical",
                    event_ids=[started.event_id, term.event_id],
                    points=TIME_CRITICAL_EXTRA_POINTS,
                    reason=(
                        "time remaining on original window "
                        f"{buffers.time_remaining_original_pct}% < 10%"
                    ),
                )
            )

    return deductions


def compute_score(
    log: ReleaseLog,
    events: list[DeploymentEvent],
    buffers: BufferSnapshot,
    terminal_kind: str,
) -> ScoreReport:
    deductions = compute_deductions(log, events, buffers, terminal_kind)
    total = sum(d.points for d in deductions)
    reserve = max(0, 100 - total)
    load = recovery_load_for(reserve)
    return ScoreReport(
        reserve_level=reserve,
        recovery_load=load,  # type: ignore[arg-type]
        deductions=deductions,
        buffers=buffers,
    )
