"""Settings parsing that the API edge depends on."""

from app.config import Settings


def test_cors_origins_splits_comma_separated_env() -> None:
    settings = Settings(cors_allow_origins="https://a.app, https://b.app ,https://c.app")
    assert settings.cors_origins == ["https://a.app", "https://b.app", "https://c.app"]


def test_cors_origins_defaults_to_local_dev() -> None:
    origins = Settings().cors_origins
    assert "http://localhost:3000" in origins
