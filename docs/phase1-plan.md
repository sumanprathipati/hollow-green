# Hollow Green — Phase 1 Final Plan

Product: Hollow Green finds releases that passed but quietly spent their recovery capacity. Green on the dashboard, hollow underneath.

Status: Plan finalized (terminology rev: no financial language). Implementation not started.

Rules (from `AGENTS.md`):
- Synthetic data only. No real company, customer, or employer data.
- Python 3.12, FastAPI, Pydantic v2, Pytest.
- Deterministic, explainable scoring. Every score links to specific events.
- Every scoring rule needs one test where it matches and one where it does not.
- No LLM, UI, database, authentication, or cloud deployment in Phase 1.
- Run format, lint, type check, and tests before done.

Terminology (binding for code):
- `RecoveryFollowUp` (not DebtItem), `follow_up_id` (not debt_id).
- `required_action` (not repayment).
- `status: open | completed | verified` (not restored bool). Phase 1 creates `open` only; `completed` / `verified` are schema-allowed for future phases.
- `recovery load` (not recovery debt).
- No `debt_score` field anywhere.
- `Reserve Level` is the only numeric primary score (0–100).
- `Recovery Load` is a derived label from Reserve Level: `low | medium | high | critical`.

This file is the source of truth for Phase 1. Implementation must match it.

---

## 1. Architecture and folder structure

Stateless pipeline:

```text
Ingest -> Detect -> Buffers -> Score -> FollowUps -> Classify -> Tolerance
```

```text
hollow-green/
  pyproject.toml
  README.md
  AGENTS.md
  docs/phase1-plan.md        # this file
  src/hollow_green/
    __init__.py
    schemas.py               # Pydantic v2 models, versioned envelope
    taxonomy.py              # event-type constants + version registry
    ingest.py                # validate version, event_id uniqueness, sort, normalize
    detectors.py             # map events -> recovery actions
    buffers.py               # buffer snapshots + time formula
    scoring.py               # Reserve Level + Recovery Load label + deductions
    followups.py             # RecoveryFollowUp factory + required_action strings
    classify.py              # 5 release classes
    tolerance.py             # second-failure tolerance
  src/api/
    __init__.py
    main.py
    routes.py                # GET /v1/health, GET /v1/version, POST /v1/releases:analyze
  tests/
    test_ingest.py
    test_detectors.py
    test_buffers.py
    test_scoring.py
    test_followups.py
    test_classify.py
    test_tolerance.py
    test_api.py
    fixtures/synthetic_*.json
```

`api/routes.py` is a thin wrapper. All logic is pure functions in `src/hollow_green/`.

---

## 2. Pydantic schemas (v1)

`schema_version: Literal["1.0"]`. Unknown version -> 422.

```python
DeploymentEvent:
  event_id: str
  release_id: str
  ts: datetime
  type: EventType
  actor: Literal["system","pipeline","human","monitor"]
  severity: Literal["info","warn","error"] = "info"
  details: dict[str, str|int|float|bool] = {}

ReleaseLog:
  schema_version: SchemaVersion
  release_id: str
  service: str               # synthetic only, e.g. "checkout-api-synth"
  window_minutes: int > 0    # interpreted as original_window_minutes (see §5)
  retry_budget_max: int >= 0
  events: list[DeploymentEvent]  # len >= 1

BufferSnapshot:
  retries_used: int
  retries_left: int
  retry_reserve_pct: float        # 0-100
  time_remaining_original_pct: float   # scored
  time_remaining_effective_pct: float  # display only
  extension_total_min: float
  rollback_available: bool
  rollback_fresh: bool
  health_end: Literal["pass","degraded","fail","unknown"]
  manual_count: int

Deduction:
  rule_id: str
  event_ids: list[str]       # never empty; every point traces to events
  points: int                # positive int subtracted
  reason: str

RecoveryLoad = Literal["low","medium","high","critical"]

ScoreReport:
  reserve_level: int 0-100        # only numeric primary score
  recovery_load: RecoveryLoad     # derived label, see §8
  deductions: list[Deduction]
  buffers: BufferSnapshot

FollowUpKind = Literal["retry","restart","manual_override","bypass","rollback","window_extension"]
FollowUpStatus = Literal["open","completed","verified"]  # Phase 1 emits open only

RecoveryFollowUp:
  follow_up_id: str
  kind: FollowUpKind
  event_ids: list[str]
  severity: Literal["low","medium","high","critical"]
  required_action: str
  status: FollowUpStatus = "open"

RollbackSummary:
  executed: bool
  event_ids: list[str]       # all rollback_* event IDs, possibly empty
  verified: bool             # True iff health pass exists after rollback_completed
  manual: bool               # True iff any rollback_* has actor==human

ReleaseReport:
  release_id: str
  classification: Literal["clean_success","recovered_success","fragile_success","rollback","failed"]
  terminal: Literal["succeeded","rolled_back","failed"]
  score: ScoreReport
  follow_ups: list[RecoveryFollowUp]
  rollback_summary: RollbackSummary
  tolerance: ToleranceReport

ToleranceReport:
  level: Literal["high","medium","low","critical"]
  retries_left: int
  can_survive_second_failure: bool
  rationale: list[str]       # includes rollback visibility line when applicable
```

API example (response shape):

```json
{
  "release_id": "rel-recovered-002",
  "classification": "recovered_success",
  "terminal": "succeeded",
  "score": {
    "reserve_level": 82,
    "recovery_load": "low",
    "deductions": [
      {"rule_id": "retry.consume", "event_ids": ["evt-02", "evt-04"], "points": 18, "reason": "2 retries: first 6 + 1x12"}
    ],
    "buffers": {"retries_used": 2, "retries_left": 3, "health_end": "pass", "rollback_available": true}
  },
  "follow_ups": [
    {"follow_up_id": "fu-01", "kind": "retry", "event_ids": ["evt-02"], "severity": "low", "required_action": "Reduce flakiness for evt-02; restore retry budget", "status": "open"}
  ],
  "rollback_summary": {"executed": false, "event_ids": [], "verified": false, "manual": false},
  "tolerance": {"level": "high", "retries_left": 3, "can_survive_second_failure": true, "rationale": ["reserve 82 >= 70, retries_left 3"]}
}
```

---

## 3. Event taxonomy (`taxonomy.py`)

Closed enum. Unknown `type` -> 422.

Lifecycle:
- `deploy_started` (required, exactly 1)
- `deploy_progress`
- `health_report` with `details.status: pass|degraded|fail`
- `deploy_succeeded | deploy_failed | deploy_rolled_back` (terminal events). Each ReleaseLog must contain exactly one terminal event. Zero or more than one terminal event must return 422.

Recovery actions (each maps to detection; follow-up creation per §7–§9):
- `retry_attempt` — `details.attempt_no: int`, `actor` should be `system|pipeline` for automated; `human` is allowed but never discounted.
- `service_restart`
- `manual_override` — expected `actor=human`.
- `bypass` — `details.bypass_kind: health_check_skip|approval_skip|test_skip`.
- `rollback_started`, `rollback_completed`
- `window_extended` — `details.extension_minutes: float > 0`, required. Counts as recovery action.

Buffer / capacity signals:
- `rollback_snapshot_ready | rollback_snapshot_stale | rollback_unavailable`
- `budget_exhausted` (optional explicit marker; derived check also applies)
- `window_extended` (also a capacity signal; see §5)

---

## 4. Retry scoring

Do not deduct the same amount for every retry.

Definitions:
- `retries = [e for e in events if e.type == retry_attempt]`, ordered by `ts`.
- `n = len(retries)`.
- `automated = [e for e in retries if e.actor in {system, pipeline}]`.
- `first_successful_automated`: the earliest event in `automated` iff `terminal == succeeded` and `automated` is non-empty. Otherwise none. Rationale: "successful" is defined by release outcome (deterministic, no outcome-guessing per retry). A `retry_attempt` with `actor==human` never qualifies for discount.
- `retries_used = n`. `retries_left = max(0, retry_budget_max - n)`.

Points:
- If `n == 0`: no `retry.consume` deduction.
- If `terminal == succeeded` and first-successful-automated exists:
  `retry_points = min(RETRY_CAP, RETRY_FIRST + RETRY_REPEAT * (n - 1))`
- Else (failed / rolled_back, or all retries human):
  `retry_points = min(RETRY_CAP, RETRY_REPEAT * n)`
- Constants: `RETRY_FIRST = 6`, `RETRY_REPEAT = 12`, `RETRY_CAP = 60`.
- Single deduction: `{rule_id: "retry.consume", event_ids: [all n retry event_ids in ts order], points: retry_points}`. All IDs listed even when capped.
- Examples: 1 auto retry + success = 6. 2 auto + success = 18 (6+12). 3 auto + success = 30. 6+ retries = 60 cap. 2 retries + failed = 24 (no discount).

Budget-exhausted penalty (separate rule):
- Trigger iff `n >= retry_budget_max and retry_budget_max > 0` OR `budget_exhausted` event present OR (`retry_budget_max == 0` and `n > 0`).
- Points: `RETRY_EXHAUSTED_PENALTY = 15`.
- Deduction: `{rule_id: "retry.budget_exhausted", event_ids: [budget_exhausted event_id if present else last retry event_id], points: 15}`.
- This stacks with `retry.consume` and is traceable (never empty `event_ids`).

---

## 5. Time-buffer formula

`window_minutes` in `ReleaseLog` is the planned buffer and is interpreted as `original_window_minutes`. Do not silently extend it.

Inputs:
- `t0 = ts(deploy_started)`, `t_term = ts(terminal event)`. Missing either -> 422. `elapsed_min = (t_term - t0).total_seconds() / 60`. Negative `elapsed_min` -> 422 (clock skew, not clamped).
- `original = window_minutes`.
- `extension_total = sum(details.extension_minutes for window_extended)`. Each must be `> 0` else 422.
- `effective = original + extension_total`.

Outputs (in `BufferSnapshot`):
- `time_remaining_original_pct = (original - elapsed_min) / original * 100`
- `time_remaining_effective_pct = (effective - elapsed_min) / effective * 100` (display only)
- Clamp display to `[-100, 100]`, round to 1 decimal.
- `extension_total_min = extension_total`.

Scoring uses original only:
- `time.low` iff `time_remaining_original_pct < 20` -> 15 pts. `event_ids`: `[deploy_started ID, terminal event ID]` for traceability.
- `time.critical` iff `time_remaining_original_pct < 10` -> additional 10 pts (25 total for time). Same `event_ids`.
- Extension gives zero credit: no deduction may be reduced or removed because `effective` looks better. Invariant: `Reserve <= 100 - original_time_points - other_points`.
- `window_extended` counts as a recovery action and blocks `clean_success` (see §10).

`window_extension` follow-up (no points, visibility + required action):
- One `RecoveryFollowUp(kind=window_extension)` per `window_extended` event. Points are 0 for these items; time points come only from `time.low/critical` above (avoids double-count).
- Severity from total: `extension_total <= 20% original` -> `medium`; `> 20%` -> `high`; `> 50%` -> `critical`.
- `required_action`: `"Re-estimate scope; restore schedule buffer of {extension_minutes}m"`.
- `status` is `open` in Phase 1.

Boundary tests required:
- No extension, finishes mid-window -> no time deduction, no extension follow-up.
- One extension where original remaining is `< 10%` but effective remaining is `> 20%` -> must still deduct 25 time points (proves extension did not restore reserve).

---

## 6. event_id uniqueness

Inside one `ReleaseLog`:
- Every `event_id` must be unique. Duplicate -> 422 with body `{duplicate_event_ids: [...]}`.
- No silent deduplication in Phase 1. Rationale: silent drop hides recovery actions and breaks traceability.
- Check runs before sorting. Sort by `(ts, event_id)` for deterministic order after validation.
- `release_id` on each event must equal `ReleaseLog.release_id` else 422.

---

## 7. Rollback scoring

Do not deduct points merely because `rollback_completed` exists. A clean, verified automatic rollback is a safety mechanism, not automatically recovery load.

- No `rollback.executed` deduction. `rollback_completed` alone costs 0 points.
- `rollback.missing` (25 pts, end `rollback_available==False`) and `rollback.stale` (10 pts, available but not fresh) and `health.*` / `time.*` remain unchanged.
- `RollbackSummary` is always present (see §2). `verified=True` iff exists `health_report(status=pass)` with `ts > rollback_completed ts`. `manual=True` iff any `rollback_*` has `actor==human`.
- Conditional `RecoveryFollowUp(kind=rollback)`, at most one per release, created iff any:
  - `incomplete`: `rollback_started` present without `rollback_completed`;
  - `manual`: `rollback_summary.manual == True`;
  - `unverified`: `executed == True` and `verified == False`;
  - `degraded`: `executed == True` and `health_end in {degraded, fail}` (unknown counts as unverified but not degraded).
- Clean path (automated + completed + verified + health pass) -> zero rollback follow-ups, zero rollback points.
- `required_action`: incomplete -> `"Complete or reconcile rollback, then verify with health pass"`; manual -> `"Record manual rollback runbook + refresh snapshot"`; unverified -> `"Run post-rollback health check to pass"`; degraded -> `"Remediate degraded health post-rollback"`. If multiple conditions hold, join with `"; "`. `status` is `open`.
- Visibility: `rollback_summary.event_ids` always lists rollback events; `tolerance.rationale` always includes one rollback line when executed, e.g. `"rollback executed evt-12, verified by evt-14 (health pass)"` or `"rollback executed evt-12, unverified"`.

---

## 8. Scoring explanation

`Reserve Level` is the only numeric primary score.

- All `points` are positive ints subtracted from 100. `Reserve = max(0, 100 - sum(deductions))`.
- `Recovery Load` is a derived label from Reserve, not a second score:
  - `reserve 80-100` -> `low`
  - `reserve 50-79` -> `medium`
  - `reserve 25-49` -> `high`
  - `reserve 0-24` -> `critical`
- There is no `debt_score` field. Fixture expectations and tests assert `reserve_level` + `recovery_load` only.

| rule_id | trigger | points |
|---|---|---|
| `restart.consume` | per `service_restart` | 15 each |
| `manual.consume` | per `manual_override` | 20 each |
| `bypass.consume` | per `bypass` | 25 each |
| `rollback.missing` | end `rollback_available==False` | 25 |
| `rollback.stale` | available but `rollback_fresh==False` | 10 |
| `health.degraded_end` | `health_end==degraded` | 20 |
| `health.failed_end` | `health_end==fail` | 40 |

Buffer derivation (`buffers.py`):
- `retry_reserve_pct = retries_left / retry_budget_max * 100` (100 if budget 0 and n 0, else 0 if budget 0 and n > 0).
- `rollback_available/fresh` from latest snapshot event before terminal; default available=True, fresh=True if no signal (documented assumption for synthetic logs).
- `health_end` from last `health_report` before terminal, else `unknown` (no points for unknown except via rollback-unverified).
- `manual_count` = count of `manual_override`.

---

## 9. Recovery follow-ups

Retries share one aggregated `retry.consume` deduction but follow-ups stay per-event for actionability.

- `retry`: one `RecoveryFollowUp(kind=retry)` per `retry_attempt` event, severity `low` for first-successful-automated, `medium` for repeats, `high` if budget exhausted. `required_action`: `"Reduce flakiness for <event_id>; restore retry budget"`. `status: open`.
- `restart`: one per `service_restart`, severity `medium`, `required_action`: `"Investigate crash loop; add readiness probe"`.
- `manual_override`: one per event, severity `high`, `required_action`: `"Automate the manual step; record runbook"`.
- `bypass`: one per event, severity `high` (`critical` if `health_check_skip`), `required_action`: `"Reinstate skipped check in pipeline"`.
- `rollback`: conditional single item per §7.
- `window_extension`: one per `window_extended` per §5.

`follow_up_id` is deterministic in tests (e.g. `fu-<event_id>` or indexed `fu-01` in fixture order) and unique within the report.

---

## 10. Classification

Order matters:

1. `failed` iff `terminal == failed`.
2. `rollback` iff `terminal == rolled_back`.
3. Else `succeeded`:
   - `clean_success` iff zero recovery actions (`retry_attempt`, `service_restart`, `manual_override`, `bypass`, `rollback_*`, `window_extended` all absent) AND `reserve >= 80` AND `health_end == pass` AND `rollback_available == True` AND `manual_count == 0`.
   - `fragile_success` iff any: `reserve < 50` OR `health_end != pass` OR `rollback_available == False` OR `manual_count >= 2` OR `bypass >= 1`.
   - Else `recovered_success`.

Constants: `CLEAN_RESERVE_MIN=80`, `FRAGILE_RESERVE_MAX=49`, `FRAGILE_MANUAL_MIN=2`.

---

## 11. Second-failure tolerance

- `critical`: `reserve < 25` OR `health_end == fail` OR (`rollback_available == False` AND `retries_left == 0`).
- `low`: `rollback_available == False` OR `reserve < 50` OR `health_end == degraded` OR `retries_left == 0`.
- `medium`: `reserve 50-69` OR `retries_left == 1`.
- `high`: `reserve >= 70` AND `retries_left >= 2` AND rollback available AND health pass.
- `can_survive_second_failure = level in {high, medium}`.
- `rationale` lists triggering rule + event IDs, plus mandatory rollback line when `rollback_summary.executed`.

---

## 12. API contract

```text
GET /v1/health -> {status: "ok"}
GET /v1/version -> {schema_version: "1.0", app: "hollow-green"}
POST /v1/releases:analyze
  request: ReleaseLog
  response 200: ReleaseReport  # score.{reserve_level, recovery_load}, follow_ups[], rollback_summary, tolerance
  errors: 422 validation (bad version, zero terminal events, multiple terminal events,
    duplicate event_id, mismatched release_id, bad extension_minutes,
    negative elapsed, unknown event type)
```

Stateless. No `GET /releases/{id}` (would imply storage).

---

## 13. Ten synthetic test cases

Fixtures in `tests/fixtures/synthetic_*.json`, synthetic services only. Expectations use `reserve_level`, `recovery_load`, `follow_ups`, never `debt_score`:

1. `rel-clean-001` — no retries, no extension, health pass, snapshot ready -> `clean_success`, reserve 100, load `low`, 0 follow-ups, tolerance high. Non-match for all deduction rules.
2. `rel-recovered-002` — 2 auto retries then success -> `recovered_success`, retry 18 pts (6+12), reserve 82, load `low`, 2 retry follow-ups (`low` + `medium`). Match for `retry.consume` tiering.
3. `rel-fragile-003` — 4 auto retries + 1 manual, `time_remaining_original < 20%` but `>= 10%` -> `fragile_success`, retry 42 (6+12*3) + manual 20 + time.low 15 = 77 total, reserve exactly 23, load exactly `critical`. Match for `manual.consume`, `time.low`.
4. `rel-bypass-004` — 1 `health_check_skip` -> `fragile_success` via bypass rule, 1 bypass follow-up (`critical`, `required_action` reinstates check).
5. `rel-rollback-005` — clean auto `rollback_completed` + post health pass -> `rollback`, 0 rollback points, 0 rollback follow-ups, summary verified=True, load by reserve. Non-match for rollback follow-up. Tolerance rationale contains rollback line.
6. `rel-rollback-unverified-005b` — auto rollback, no post health pass -> `rollback`, 1 rollback follow-up (`open`, unverified). Match for conditional rollback follow-up.
7. `rel-failed-006` — 2 retries then `deploy_failed`, health fail, budget exhausted (budget 2) -> `failed`, retry 24 (no discount) + exhausted 15 + health 40, load `critical`. Match for `retry.budget_exhausted`, `health.failed_end`.
8. `rel-norollback-007` — success but `rollback_unavailable` -> `fragile_success`, `rollback.missing` 25.
9. `rel-restart-008` — 2 restarts + degraded end -> `fragile_success`. Match for `restart.consume`, `health.degraded_end`.
10. `rel-window-one-009` — one extension: `original=60, elapsed=55, extension=15` -> original remaining 8.3% (25 time pts), 1 extension follow-up (`open`), effective display 25.0% but score uses 8.3%. Match for `time.critical` + non-restoration invariant.
11. `rel-stale-010` — 1 auto retry + success + `rollback_snapshot_stale` -> `recovered_success`, retry 6 + stale 10. (005b variant makes 11 files; merge 005b into 005 as sub-cases if strict 10 required.)

Additional unit tests (no fixture):
- Duplicate `event_id` -> 422, IDs listed.
- Zero terminal events -> 422.
- Exactly one terminal event -> 200 (covered by every fixture).
- Multiple terminal events (e.g. `deploy_succeeded` + `deploy_failed`, distinct event_ids) -> 422.
- 8 retries -> retry points capped 60, all 8 IDs listed.
- Human-only retry + success -> no 6-pt discount.
- Extension cannot raise reserve: same elapsed with/without extension -> reserve with extension <= reserve without.
- `RecoveryFollowUp` shape: every item has `follow_up_id, kind, event_ids, severity, required_action, status`; `status` is `open` in Phase 1.
- No `debt_score` / `debt_id` / `repayment` / `restored` keys appear in API responses (regression test for terminology).

---

## 14. Acceptance criteria

- `POST /v1/releases:analyze` accepts `1.0`; returns 422 for unknown version, zero terminal events, multiple terminal events, duplicate `event_id`, bad extension, negative elapsed.
- `rel-fragile-003` asserts reserve exactly 23 and load exactly `critical` (42 retry + 20 manual + 15 time.low).
- All 5 classifications reachable.
- Every deduction has non-empty `event_ids`; retry cap case lists all IDs.
- Retry: 1 auto + success = 6; repeats 12; cap 60; exhausted +15.
- Rollback: clean verified auto rollback = 0 points, 0 follow-ups, visible in `rollback_summary` + tolerance rationale; incomplete/manual/unverified/degraded = 1 follow-up with `status open`.
- Time: scoring uses original window; extension never raises reserve; one-extension + no-extension boundary tests pass.
- `score` contains `reserve_level` + `recovery_load` only; no `debt_score` key.
- Every follow-up has `follow_up_id, kind, event_ids, severity, required_action, status=open`; no `debt_id` / `repayment` / `restored` keys.
- `recovery_load` mapping pinned: 80-100 low, 50-79 medium, 25-49 high, 0-24 critical.
- `pytest`, `ruff check`, `mypy`, `ruff format --check` pass on Python 3.12.
- No real data, secrets, LLM/UI/db/auth/cloud. No financial "debt" language in code, tests, README, or API.
- README documents Reserve Level, Recovery Load, API example with `follow_ups`, and test run.

---

## 15. Risks and assumptions

- "Successful retry" defined by terminal outcome (simple, deterministic). Per-retry success linking deferred.
- Clean rollbacks can score reserve 100 but classify `rollback` — dashboards must not rank by reserve alone.
- `window_minutes` alias `original_window_minutes`: strict rename deferred to `1.1`.
- Single-release scope; no cross-release carryover.
- Closed enum rejects forward-compatible logs; cost accepted for explicit versioning.
- Per-event retry follow-ups + aggregated retry deduction is intentional (actionability vs scoring).
- `completed` / `verified` follow-up states are schema-reserved; no transitions in Phase 1 (no restoration events).

---

End of Phase 1 plan. Next step (separate approval): implement exactly this, starting with schemas + ingest + uniqueness validation.
