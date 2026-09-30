"""Ingest validation: uniqueness, terminal count, release binding, time sanity."""

from collections import Counter

from hollow_green.schemas import DeploymentEvent, ReleaseLog
from hollow_green.taxonomy import TERMINAL_TO_LABEL, TERMINAL_TYPES, EventType


class IngestError(ValueError):
    def __init__(self, message: str, duplicate_event_ids: list[str] | None = None):
        super().__init__(message)
        self.duplicate_event_ids = duplicate_event_ids or []


def _event_type(value: str) -> EventType | None:
    try:
        return EventType(value)
    except ValueError:
        return None


def validate_and_sort(log: ReleaseLog) -> list[DeploymentEvent]:
    ids = [e.event_id for e in log.events]
    dupes = sorted([k for k, v in Counter(ids).items() if v > 1])
    if dupes:
        raise IngestError(
            f"duplicate event_id values: {dupes}",
            duplicate_event_ids=dupes,
        )

    mismatched = [e.event_id for e in log.events if e.release_id != log.release_id]
    if mismatched:
        raise IngestError(f"release_id mismatch on events: {mismatched}")

    unknown = [e.event_id for e in log.events if _event_type(e.type) is None]
    if unknown:
        raise IngestError(f"unknown event types on events: {unknown}")

    starts = [e for e in log.events if e.type == EventType.DEPLOY_STARTED.value]
    if len(starts) != 1:
        raise IngestError(
            f"expected exactly 1 deploy_started, found {len(starts)}",
        )

    terminals = [e for e in log.events if _event_type(e.type) in TERMINAL_TYPES]
    if len(terminals) == 0:
        raise IngestError("zero terminal events: expected exactly 1")
    if len(terminals) > 1:
        raise IngestError(
            f"multiple terminal events: {[e.event_id for e in terminals]}",
        )

    for e in log.events:
        if e.type == EventType.WINDOW_EXTENDED.value:
            raw = e.details.get("extension_minutes")
            if isinstance(raw, bool) or not isinstance(raw, (int, float)):
                raise IngestError(
                    f"window_extended {e.event_id} missing numeric extension_minutes",
                )
            if float(raw) <= 0:
                raise IngestError(
                    f"window_extended {e.event_id} extension_minutes must be > 0",
                )

    t0 = starts[0].ts
    t_term = terminals[0].ts
    elapsed_min = (t_term - t0).total_seconds() / 60
    if elapsed_min < 0:
        raise IngestError("negative elapsed time: terminal precedes deploy_started")

    ordered = sorted(log.events, key=lambda e: (e.ts, e.event_id))
    return ordered


def terminal_label(events: list[DeploymentEvent]) -> str:
    for e in events:
        t = _event_type(e.type)
        if t in TERMINAL_TYPES and t is not None:
            return TERMINAL_TO_LABEL[t]
    raise IngestError("zero terminal events: expected exactly 1")
