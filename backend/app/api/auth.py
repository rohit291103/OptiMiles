"""Authentication seam — verify a Supabase access token, extract the user id.

The frontend's Supabase session mints an access token; this module verifies its
signature and returns the caller's real `auth.users` id (the token's `sub`
claim). That id is exactly what `repositories.results.persist_recommendation`
requires as a precondition — a `users → auth.users`-backed identity that only
Supabase auth can create.

**Two signing schemes, chosen by the token's header `alg`:**
- **ES256 (default for newer projects):** tokens are signed with an asymmetric
  key whose *public* half is published at the project's JWKS endpoint. We fetch
  and cache those keys (`PyJWKClient`) and verify against them — no shared secret
  is involved, and there's nothing sensitive to configure beyond the project URL.
- **HS256 (legacy):** tokens are signed with the shared project JWT secret; we
  verify with `supabase_jwt_secret`.

The alg is read from the token header and each token is verified with only the
matching key family, so `alg:none` and HS/ES confusion attacks stay blocked.

Boundary note (D-4): FastAPI still talks to Postgres with the service role; this
seam does not authorize row access, it only identifies the caller so writes are
attributed to a real user. RLS stays on as defense-in-depth.

With neither `supabase_url` (JWKS) nor `supabase_jwt_secret` configured, auth is
*disabled*: `require_user` rejects every request (401), so a misconfigured deploy
fails closed, never open.
"""

import logging
import ssl
from functools import lru_cache
from typing import Any
from uuid import UUID

import certifi
import jwt
from fastapi import Depends, Header, HTTPException, status
from jwt import PyJWKClient

from app.config import Settings, get_settings

_log = logging.getLogger(__name__)


@lru_cache(maxsize=4)
def _jwks_client(jwks_url: str) -> PyJWKClient:
    """A cached JWKS client per URL. `PyJWKClient` caches the fetched keys
    internally, so verification doesn't hit the network on every request; the
    lru_cache keeps one client instance alive across requests.

    The SSL context is built from `certifi`'s CA bundle because PyJWKClient
    fetches over `urllib`, which on some Python builds (e.g. the python.org
    macOS build) doesn't use the system trust store — without this the JWKS
    fetch fails with CERTIFICATE_VERIFY_FAILED and every ES256 token 401s."""
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    return PyJWKClient(jwks_url, ssl_context=ssl_context)


class AuthError(HTTPException):
    def __init__(self, detail: str) -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


# The claims we always require: without this, PyJWT only checks `exp` when it
# happens to be present, so an exp-less token would never expire.
_REQUIRED_CLAIMS = ["exp", "aud", "sub"]


def _signing_key_and_alg(token: str, settings: Settings) -> tuple[Any, str]:
    """Pick the verification key + expected alg from the token's header.

    ES256 ⇒ the matching public key from the project JWKS; HS256 ⇒ the shared
    secret. Raises AuthError when the required scheme isn't configured or the
    alg is unsupported (so `alg:none` and family-confusion are rejected here,
    before any signature check)."""
    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError as exc:
        raise AuthError("Malformed token header.") from exc
    alg = header.get("alg")

    if alg == "ES256":
        jwks_url = settings.supabase_jwks_url
        if not jwks_url:
            raise AuthError("Authentication is not configured.")
        try:
            key = _jwks_client(jwks_url).get_signing_key_from_jwt(token).key
        except jwt.PyJWTError as exc:
            raise AuthError("Could not resolve token signing key.") from exc
        return key, "ES256"

    if alg == "HS256":
        if not settings.supabase_jwt_secret:
            raise AuthError("Authentication is not configured.")
        return settings.supabase_jwt_secret, "HS256"

    raise AuthError("Unsupported token algorithm.")


def user_id_from_token(token: str, settings: Settings) -> UUID:
    """Verify a Supabase access token and return the `sub` (auth.users id).

    Handles both signing schemes (ES256 via JWKS, HS256 via the shared secret),
    chosen by the token header. Raises AuthError on an unconfigured/unsupported
    scheme, bad signature, wrong audience, expiry, or a `sub` that isn't a UUID.
    """
    key, alg = _signing_key_and_alg(token, settings)
    try:
        claims = jwt.decode(
            token,
            key,
            algorithms=[alg],  # exactly the alg the header claimed — no confusion
            audience=settings.supabase_jwt_audience,
            options={"require": _REQUIRED_CLAIMS},
        )
    except jwt.PyJWTError as exc:
        # Log the specific reason server-side (the token itself is never logged)
        # so a 401 is diagnosable — the client only ever sees a generic message.
        _log.warning("JWT verification failed: %s: %s", type(exc).__name__, exc)
        raise AuthError("Invalid or expired token.") from exc

    sub = claims.get("sub")
    if not sub:
        raise AuthError("Token is missing a subject.")
    try:
        return UUID(str(sub))
    except ValueError as exc:
        raise AuthError("Token subject is not a valid user id.") from exc


def _bearer(authorization: str | None) -> str:
    """Pull the token out of an `Authorization: Bearer <token>` header."""
    if not authorization:
        raise AuthError("Missing Authorization header.")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise AuthError("Authorization header must be 'Bearer <token>'.")
    return token


def require_user(
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> UUID:
    """FastAPI dependency: the authenticated caller's id, or 401.

    Use on endpoints that persist. Anonymous endpoints (the public simulator)
    do not depend on this.
    """
    return user_id_from_token(_bearer(authorization), settings)
