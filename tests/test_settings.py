"""Settings/env parsing and production-safe defaults. No live calls."""

import logging
import sys

sys.path.insert(0, "src")

import pytest

from api import settings


@pytest.fixture(autouse=True)
def clean_settings_env(monkeypatch):
    for key in (
        "ENVIRONMENT",
        "ALLOWED_ORIGINS",
        "E2E_TEST_MODE",
        "PUBLIC_DATA_FIXTURE_ONLY",
        "GITHUB_TOKEN",
        "AI_REVIEW_PROVIDER",
        "AI_REVIEW_BASE_URL",
        "AI_REVIEW_MODEL",
        "AI_REVIEW_API_KEY",
    ):
        monkeypatch.delenv(key, raising=False)
    yield


def test_environment_defaults_to_development(monkeypatch):
    assert settings.environment() == "development"
    assert not settings.is_production()
    monkeypatch.setenv("ENVIRONMENT", "production")
    assert settings.environment() == "production"
    assert settings.is_production()
    monkeypatch.setenv("ENVIRONMENT", "staging")
    assert settings.environment() == "development"


def test_test_mode_defaults_are_false():
    assert settings.e2e_test_mode() is False
    assert settings.fixture_only_mode() is False
    assert settings.github_token_configured() is False
    assert settings.ai_review_configured() is False


def test_parse_allowed_origins_valid():
    assert settings.parse_allowed_origins("") == []
    assert settings.parse_allowed_origins("https://a.example, https://b.example/") == [
        "https://a.example",
        "https://b.example",
    ]


def test_parse_allowed_origins_rejects_wildcard():
    with pytest.raises(ValueError):
        settings.parse_allowed_origins("https://a.example, *")


def test_parse_allowed_origins_requires_https():
    with pytest.raises(ValueError):
        settings.parse_allowed_origins("http://example.com")


def test_allowed_origins_merges_dev_and_configured(monkeypatch):
    assert settings.allowed_origins() == [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://app.example")
    assert settings.allowed_origins() == [
        "https://app.example",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]


def test_public_data_status():
    assert settings.public_data_status() == "available"


def test_public_data_status_limited_in_fixture_mode(monkeypatch):
    monkeypatch.setenv("PUBLIC_DATA_FIXTURE_ONLY", "1")
    assert settings.public_data_status() == "limited"


def test_startup_log_never_leaks_values(monkeypatch, caplog):
    monkeypatch.setenv("GITHUB_TOKEN", "fake-secret-token-123")
    monkeypatch.setenv("AI_REVIEW_API_KEY", "fake-ai-key-456")
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://secret-app.example")
    with caplog.at_level(logging.INFO):
        settings.log_safe_config()
    text = caplog.text
    assert "fake-secret-token-123" not in text
    assert "fake-ai-key-456" not in text
    assert "secret-app" not in text
    assert "environment=" in text
