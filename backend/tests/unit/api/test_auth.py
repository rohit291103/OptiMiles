"""JWT verification seam — the security-critical paths, both signing schemes.

We mint tokens with keys the code verifies against (an HS256 secret, and a
generated EC keypair for ES256), so these exercise real signature verification
(no live Supabase). The rejection cases are the point: a bad signature, wrong
audience, expiry, missing/garbled header, a non-UUID subject, `alg:none`,
family-confusion — and the fail-closed guarantee (no scheme configured ⇒ every
token 401s, never passes through).

ES256 verification normally resolves the public key from the project's JWKS
endpoint over the network; here we generate a keypair and stub `_jwks_client` so
the crypto is real but the fetch is not.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from app.api import auth as auth_module
from app.api.auth import AuthError, _bearer, require_user, user_id_from_token
from app.config import Settings

SECRET = "test-jwt-secret-do-not-use-in-prod-and-at-least-32-bytes"
JWKS_URL = "https://project.example.supabase.co/auth/v1/.well-known/jwks.json"


class _FakeSigningKey:
    def __init__(self, key: object) -> None:
        self.key = key


class _FakeJWKClient:
    """Stands in for PyJWKClient: returns a fixed public key, no network."""

    def __init__(self, public_key: object) -> None:
        self._public_key = public_key

    def get_signing_key_from_jwt(self, _token: str) -> _FakeSigningKey:
        return _FakeSigningKey(self._public_key)


@pytest.fixture
def es256(monkeypatch: pytest.MonkeyPatch) -> ec.EllipticCurvePrivateKey:
    """An EC keypair whose public half `_jwks_client` will hand back, so an
    ES256 token signed with the private half verifies for real."""
    private_key = ec.generate_private_key(ec.SECP256R1())
    fake = _FakeJWKClient(private_key.public_key())
    monkeypatch.setattr(auth_module, "_jwks_client", lambda _url: fake)
    return private_key


def _es256_settings(audience: str = "authenticated") -> Settings:
    return Settings(
        supabase_url="https://project.example.supabase.co",
        supabase_jwt_audience=audience,
    )


def _es256_token(
    private_key: ec.EllipticCurvePrivateKey,
    *,
    sub: str,
    audience: str = "authenticated",
    exp_delta: timedelta = timedelta(hours=1),
) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {"sub": sub, "aud": audience, "iat": now, "exp": now + exp_delta},
        private_key,
        algorithm="ES256",
    )


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


def test_fails_closed_when_nothing_configured() -> None:
    """A deploy with neither JWKS nor a secret must reject every token."""
    token = _token(sub=str(uuid4()))
    with pytest.raises(AuthError):
        user_id_from_token(token, Settings(supabase_url="", supabase_jwt_secret=""))


# ── ES256 via JWKS (the default scheme for newer Supabase projects) ──────────


def test_es256_valid_token_returns_user_id(
    es256: ec.EllipticCurvePrivateKey,
) -> None:
    """A real ES256 token verifies against the (stubbed) JWKS public key."""
    uid = uuid4()
    token = _es256_token(es256, sub=str(uid))
    assert user_id_from_token(token, _es256_settings()) == uid


def test_es256_bad_signature_rejected(es256: ec.EllipticCurvePrivateKey) -> None:
    """A token signed by a *different* EC key fails against the JWKS key."""
    other = ec.generate_private_key(ec.SECP256R1())
    token = _es256_token(other, sub=str(uuid4()))
    with pytest.raises(AuthError):
        user_id_from_token(token, _es256_settings())


def test_es256_expired_token_rejected(es256: ec.EllipticCurvePrivateKey) -> None:
    token = _es256_token(es256, sub=str(uuid4()), exp_delta=timedelta(hours=-1))
    with pytest.raises(AuthError):
        user_id_from_token(token, _es256_settings())


def test_es256_wrong_audience_rejected(es256: ec.EllipticCurvePrivateKey) -> None:
    token = _es256_token(es256, sub=str(uuid4()), audience="anon")
    with pytest.raises(AuthError):
        user_id_from_token(token, _es256_settings())


def test_es256_token_rejected_when_jwks_not_configured(
    es256: ec.EllipticCurvePrivateKey,
) -> None:
    """An ES256 token with no `supabase_url` set has no JWKS to verify against —
    reject (fail closed), never fall through to the HS256 secret."""
    token = _es256_token(es256, sub=str(uuid4()))
    with pytest.raises(AuthError):
        user_id_from_token(token, Settings(supabase_url="", supabase_jwt_secret=SECRET))


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
