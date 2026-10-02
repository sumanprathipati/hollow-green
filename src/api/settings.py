"""Centralized environment interpretation with production-safe defaults.

Frontend: only NEXT_PUBLIC_API_BASE_URL (build-time, never a secret).
Backend non-secrets: ENVIRONMENT, ALLOWED_ORIGINS, PUBLIC_REPOS.
Backend secrets: GITHUB_TOKEN, AI_REVIEW_API_KEY (+ AI provider config).
Test-only: E2E_TEST_MODE, PUBLIC_DATA_FIXTURE_ONLY.
"""

import logging
import os

logger = logging.getLogger(__name__)

DEV_ORIGINS: tuple[str, ...] = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
)


def environment() -> str:
    """Deployment environment. Anything other than 'production' is development."""
    return (
        "production" if os.environ.get("ENVIRONMENT", "").strip() == "production" else "development"
    )


def is_production() -> bool:
    return environment() == "production"


def e2e_test_mode() -> bool:
    """Explicit test-only flag. Defaults to False; must stay off in production."""
    return os.environ.get("E2E_TEST_MODE", "") == "1"


def fixture_only_mode() -> bool:
    """Deterministic fixture mode for E2E/dev. Defaults to False."""
    return os.environ.get("PUBLIC_DATA_FIXTURE_ONLY", "") == "1"


def github_token_configured() -> bool:
    return bool(os.environ.get("GITHUB_TOKEN", "").strip())


def ai_review_configured() -> bool:
    from api.evidence_review import OpenAICompatibleProvider

    return OpenAICompatibleProvider.from_env() is not None


def parse_allowed_origins(raw: str) -> list[str]:
    """Parse comma-separated origins. Wildcards are never allowed."""
    origins = [o.strip().rstrip("/") for o in raw.split(",") if o.strip()]
    if "*" in origins:
        raise ValueError("wildcard origins are not allowed")
    for origin in origins:
        if not origin.startswith("https://"):
            raise ValueError(f"production origins must be https: {origin}")
    return origins


def allowed_origins() -> list[str]:
    """Dev defaults plus configured production origins. No wildcards, ever."""
    configured = parse_allowed_origins(os.environ.get("ALLOWED_ORIGINS", ""))
    seen = set(configured)
    merged = list(configured)
    for default in DEV_ORIGINS:
        if default not in seen:
            merged.append(default)
    return merged


def public_data_status() -> str:
    """Safe availability label. 'limited' when only fixtures can be served."""
    if fixture_only_mode():
        return "limited"
    return "available"


def log_safe_config() -> None:
    """Log configuration state only. Never values, headers, URLs, or content."""
    logger.info(
        "environment=%s, GitHub token configured=%s, AI provider configured=%s, "
        "E2E mode=%s, allowed origins=%d",
        environment(),
        github_token_configured(),
        ai_review_configured(),
        e2e_test_mode(),
        len(allowed_origins()),
    )
