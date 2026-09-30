"""RecoveryFollowUp factory. Phase 1 emits status=open only."""

from hollow_green import detectors
from hollow_green.schemas import (
    BufferSnapshot,
    DeploymentEvent,
    RecoveryFollowUp,
    RollbackSummary,
)
from hollow_green.taxonomy import EventType


def severity_for_extension(extension_total: float, original: float) -> str:
    if original <= 0:
        return "high"
    ratio = extension_total / original
    if ratio > 0.5:
        return "critical"
    if ratio > 0.2:
        return "high"
    return "medium"


def build_rollback_summary(events: list[DeploymentEvent]) -> RollbackSummary:
    rb = detectors.rollback_events(events)
    ids = [e.event_id for e in rb]
    executed = any(e.type == EventType.ROLLBACK_COMPLETED.value for e in rb)
    manual = any(e.actor == "human" for e in rb)
    verified = False
    completed = [e for e in rb if e.type == EventType.ROLLBACK_COMPLETED.value]
    if completed:
        t_done = max(e.ts for e in completed)
        for h in detectors.health_reports(events):
            if h.ts > t_done and h.details.get("status") == "pass":
                verified = True
                break
    return RollbackSummary(executed=executed, event_ids=ids, verified=verified, manual=manual)


def _budget_exhausted(retry_count: int, budget_max: int, events: list[DeploymentEvent]) -> bool:
    if detectors.budget_exhausted_events(events):
        return True
    if budget_max > 0 and retry_count >= budget_max:
        return True
    return budget_max == 0 and retry_count > 0


def build_follow_ups(
    events: list[DeploymentEvent],
    buffers: BufferSnapshot,
    rollback_summary: RollbackSummary,
    retry_budget_max: int,
    terminal_kind: str,
    original_window_minutes: float,
) -> list[RecoveryFollowUp]:
    follow_ups: list[RecoveryFollowUp] = []
    retry_list = detectors.retries(events)
    auto_ids: set[str] = set()
    if terminal_kind == "succeeded":
        auto = [e for e in retry_list if e.actor in ("system", "pipeline")]
        if auto:
            first = min(auto, key=lambda e: (e.ts, e.event_id))
            auto_ids.add(first.event_id)
    exhausted = _budget_exhausted(len(retry_list), retry_budget_max, events)
    for e in retry_list:
        if exhausted:
            severity = "high"
        elif e.event_id in auto_ids:
            severity = "low"
        else:
            severity = "medium"
        follow_ups.append(
            RecoveryFollowUp(
                follow_up_id=f"fu-{e.event_id}",
                kind="retry",
                event_ids=[e.event_id],
                severity=severity,  # type: ignore[arg-type]
                required_action=(f"Reduce flakiness for {e.event_id}; restore retry budget"),
                status="open",
            )
        )

    for e in detectors.restarts(events):
        follow_ups.append(
            RecoveryFollowUp(
                follow_up_id=f"fu-{e.event_id}",
                kind="restart",
                event_ids=[e.event_id],
                severity="medium",
                required_action="Investigate crash loop; add readiness probe",
                status="open",
            )
        )

    for e in detectors.manual_overrides(events):
        follow_ups.append(
            RecoveryFollowUp(
                follow_up_id=f"fu-{e.event_id}",
                kind="manual_override",
                event_ids=[e.event_id],
                severity="high",
                required_action="Automate the manual step; record runbook",
                status="open",
            )
        )

    for e in detectors.bypasses(events):
        kind = e.details.get("bypass_kind")
        severity = "critical" if kind == "health_check_skip" else "high"
        follow_ups.append(
            RecoveryFollowUp(
                follow_up_id=f"fu-{e.event_id}",
                kind="bypass",
                event_ids=[e.event_id],
                severity=severity,  # type: ignore[arg-type]
                required_action="Reinstate skipped check in pipeline",
                status="open",
            )
        )

    incomplete = bool(detectors.rollback_started(events)) and not bool(
        detectors.rollback_completed(events)
    )
    unverified = rollback_summary.executed and not rollback_summary.verified
    degraded = rollback_summary.executed and buffers.health_end in ("degraded", "fail")
    manual = rollback_summary.manual
    if incomplete or manual or unverified or degraded:
        reasons: list[str] = []
        if incomplete:
            reasons.append("Complete or reconcile rollback, then verify with health pass")
        if manual:
            reasons.append("Record manual rollback runbook + refresh snapshot")
        if unverified:
            reasons.append("Run post-rollback health check to pass")
        if degraded:
            reasons.append("Remediate degraded health post-rollback")
        anchor = rollback_summary.event_ids[0] if rollback_summary.event_ids else "rollback"
        follow_ups.append(
            RecoveryFollowUp(
                follow_up_id=f"fu-rollback-{anchor}",
                kind="rollback",
                event_ids=list(rollback_summary.event_ids),
                severity="high",
                required_action="; ".join(reasons),
                status="open",
            )
        )

    ext_severity = severity_for_extension(buffers.extension_total_min, original_window_minutes)
    for e in detectors.extensions(events):
        raw = e.details.get("extension_minutes", 0)
        minutes = float(raw) if isinstance(raw, (int, float)) else 0.0
        follow_ups.append(
            RecoveryFollowUp(
                follow_up_id=f"fu-{e.event_id}",
                kind="window_extension",
                event_ids=[e.event_id],
                severity=ext_severity,  # type: ignore[arg-type]
                required_action=(f"Re-estimate scope; restore schedule buffer of {minutes:g}m"),
                status="open",
            )
        )

    return follow_ups
