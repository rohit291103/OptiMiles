"""Authentication seam — verify a Supabase access token, extract the user id.

The frontend's Supabase session mints an HS256 access token signed with the
project JWT secret; this module verifies that signature and returns the caller's
real `auth.users` id (the token's `sub` claim). That id is exactly what
`repositories.results.persist_recommendation` requires as a precondition — a
`users → auth.users`-backed identity that only Supabase auth can create.

Boundary note (D-4): FastAPI still talks to Postgres with the service role; this
seam does not authorize row access, it only identifies the caller so writes are
attributed to a real user. RLS stays on as defense-in-depth.

With no `supabase_jwt_secret` configured, auth is *disabled*: `require_user`
rejects every request (401), so a misconfigured deploy fails closed, never open.
"""

from uuid import UUID

import jwt
from fastapi import Depends, Header, HTTPException, status

from app.config import Settings, get_settings


class AuthError(HTTPException):
    def __init__(self, detail: str) -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


def user_id_from_token(token: str, settings: Settings) -> UUID:
    """Verify a Supabase access token and return the `sub` (auth.users id).

    Raises AuthError on a missing secret, bad signature, wrong audience,
    expiry, or a `sub` that isn't a UUID. Pure and synchronous — unit-testable
    without a request or a live Supabase.
    """
    if not settings.supabase_jwt_secret:
        raise AuthError("Authentication is not configured.")
    try:
        claims = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience=settings.supabase_jwt_audience,
            # Require the claims we rely on: without this, PyJWT only checks
            # `exp` when present, so an exp-less token would never expire.
            options={"require": ["exp", "aud", "sub"]},
        )
    except jwt.PyJWTError as exc:
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
