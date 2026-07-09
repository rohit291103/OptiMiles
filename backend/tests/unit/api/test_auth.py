"""JWT verification seam — the security-critical paths, with a known secret.

We mint tokens with the same HS256 secret the code verifies against, so these
exercise real signature verification (no live Supabase). The rejection cases are
the point: a bad signature, wrong audience, expiry, missing/garbled header, a
non-UUID subject, and — the fail-closed guarantee — a request when no secret is
configured must all 401, never pass through.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest

from app.api.auth import AuthError, _bearer, require_user, user_id_from_token
from app.config import Settings

SECRET = "test-jwt-secret-do-not-use-in-prod-and-at-least-32-bytes"


def _settings(secret: str = SECRET, audience: str = "authenticated") -> Settings:
    return Settings(supabase_jwt_secret=secret, supabase_jwt_audience=audience)


def _token(
    *,
    sub: str,
    secret: str = SECRET,
    audience: str = "authenticated",
    exp_delta: timedelta = timedelta(hours=1),
) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {"sub": sub, "aud": audience, "iat": now, "exp": now + exp_delta},
        secret,
        algorithm="HS256",
    )


def test_valid_token_returns_user_id() -> None:
    uid = uuid4()
    assert user_id_from_token(_token(sub=str(uid)), _settings()) == uid


def test_bad_signature_rejected() -> None:
    token = _token(sub=str(uuid4()), secret="a-different-secret")
    with pytest.raises(AuthError):
        user_id_from_token(token, _settings())


def test_wrong_audience_rejected() -> None:
    token = _token(sub=str(uuid4()), audience="anon")
    with pytest.raises(AuthError):
        user_id_from_token(token, _settings())


def test_expired_token_rejected() -> None:
    token = _token(sub=str(uuid4()), exp_delta=timedelta(hours=-1))
    with pytest.raises(AuthError):
        user_id_from_token(token, _settings())


def test_non_uuid_subject_rejected() -> None:
    with pytest.raises(AuthError):
        user_id_from_token(_token(sub="not-a-uuid"), _settings())


def test_missing_subject_rejected() -> None:
    now = datetime.now(UTC)
    token = jwt.encode(
        {"aud": "authenticated", "iat": now, "exp": now + timedelta(hours=1)},
        SECRET,
        algorithm="HS256",
    )
    with pytest.raises(AuthError):
        user_id_from_token(token, _settings())


def test_token_without_exp_rejected() -> None:
    """A validly-signed token that omits `exp` must NOT be treated as
    never-expiring — we require the claim explicitly."""
    now = datetime.now(UTC)
    token = jwt.encode(
        {"sub": str(uuid4()), "aud": "authenticated", "iat": now},  # no exp
        SECRET,
        algorithm="HS256",
    )
    with pytest.raises(AuthError):
        user_id_from_token(token, _settings())


def test_alg_none_token_rejected() -> None:
    """An unsigned `alg: none` token must be rejected — no algorithm-confusion
    bypass of the HS256 allowlist."""
    token = jwt.encode(
        {"sub": str(uuid4()), "aud": "authenticated"}, None, algorithm="none"
    )
    with pytest.raises(AuthError):
        user_id_from_token(token, _settings())


def test_wrong_algorithm_rejected() -> None:
    """A token signed with a different (real) algorithm than the allowlist is
    rejected even when signed with the same secret."""
    now = datetime.now(UTC)
    token = jwt.encode(
        {"sub": str(uuid4()), "aud": "authenticated", "iat": now,
         "exp": now + timedelta(hours=1)},
        SECRET,
        algorithm="HS512",  # not in algorithms=["HS256"]
    )
    with pytest.raises(AuthError):
        user_id_from_token(token, _settings())


def test_fails_closed_when_no_secret_configured() -> None:
    """A deploy with no JWT secret must reject every token, never pass through."""
    token = _token(sub=str(uuid4()))
    with pytest.raises(AuthError):
        user_id_from_token(token, _settings(secret=""))


# ── header parsing ──────────────────────────────────────────────────────────


def test_bearer_extracts_token() -> None:
    assert _bearer("Bearer abc.def.ghi") == "abc.def.ghi"


@pytest.mark.parametrize(
    "header",
    [None, "", "abc.def.ghi", "Basic abc", "Bearer", "Bearer "],
)
def test_bearer_rejects_malformed_header(header: str | None) -> None:
    with pytest.raises(AuthError):
        _bearer(header)


def test_require_user_end_to_end() -> None:
    uid = uuid4()
    result = require_user(f"Bearer {_token(sub=str(uid))}", _settings())
    assert result == uid
