"""FastAPI routes: stateless analysis."""

from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from hollow_green.analyze import analyze_log
from hollow_green.ingest import IngestError
from hollow_green.schemas import ReleaseLog

router = APIRouter()


@router.get("/v1/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/v1/version")
def version() -> dict[str, str]:
    return {"schema_version": "1.0", "app": "hollow-green"}


@router.post("/v1/releases:analyze")
def analyze_release(payload: dict[str, object]) -> dict[str, object]:
    try:
        log = ReleaseLog.model_validate(payload)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc
    try:
        report = analyze_log(log)
    except IngestError as exc:
        detail: object = {"message": str(exc)}
        if exc.duplicate_event_ids:
            detail = {
                "message": str(exc),
                "duplicate_event_ids": exc.duplicate_event_ids,
            }
        raise HTTPException(status_code=422, detail=detail) from exc
    return report.model_dump(mode="json")
