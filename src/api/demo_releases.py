"""Development/demo fixture endpoints (read-only, synthetic only)."""

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

ALLOWED_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"]

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "tests" / "fixtures"

DEMO_MAP: dict[str, str] = {
    "rel-clean-001": "synthetic_clean_001.json",
    "rel-recovered-002": "synthetic_recovered_002.json",
    "rel-fragile-003": "synthetic_fragile_003.json",
    "rel-rollback-005": "synthetic_rollback_005.json",
    "rel-failed-006": "synthetic_failed_006.json",
}

DEMO_META: list[dict[str, str]] = [
    {
        "release_id": "rel-clean-001",
        "display_name": "Clean success demo (rel-clean-001)",
        "classification_hint": "clean_success",
    },
    {
        "release_id": "rel-recovered-002",
        "display_name": "Recovered success demo, 2 retries (rel-recovered-002)",
        "classification_hint": "recovered_success",
    },
    {
        "release_id": "rel-fragile-003",
        "display_name": "Fragile success demo, retries + manual + low time (rel-fragile-003)",
        "classification_hint": "fragile_success",
    },
    {
        "release_id": "rel-rollback-005",
        "display_name": "Rollback demo, verified auto rollback (rel-rollback-005)",
        "classification_hint": "rollback",
    },
    {
        "release_id": "rel-failed-006",
        "display_name": "Failed demo (rel-failed-006)",
        "classification_hint": "failed",
    },
]

demo_router = APIRouter()


@demo_router.get(
    "/v1/demo-releases",
    description="Development/demo only: list synthetic demo fixtures.",
)
def list_demo_releases() -> list[dict[str, str]]:
    return DEMO_META


@demo_router.get(
    "/v1/demo-releases/{release_id}",
    description="Development/demo only: return one synthetic ReleaseLog fixture.",
)
def get_demo_release(release_id: str) -> dict[str, object]:
    filename = DEMO_MAP.get(release_id)
    if filename is None:
        raise HTTPException(status_code=404, detail="unknown demo release")
    base = FIXTURES_DIR.resolve()
    target = (base / filename).resolve()
    if target.parent != base or not target.is_file():
        raise HTTPException(status_code=404, detail="unknown demo release")
    payload: dict[str, object] = json.loads(target.read_text())
    return payload
