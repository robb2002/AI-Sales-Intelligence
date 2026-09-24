import json
import logging
import uuid
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

import jwt
from jwt.exceptions import ExpiredSignatureError, PyJWKClientConnectionError, PyJWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import (
    AuthExpiredError,
    AuthInvalidError,
    InsufficientPermissionError,
    UserNotProvisionedError,
    UserWithoutRoleError,
)
from app.repositories.app_users import AppUserRepository

logger = logging.getLogger(__name__)

CLERK_JWKS_URL = "https://api.clerk.com/v1/jwks"
CLERK_USERS_URL = "https://api.clerk.com/v1/users"
ROLES: frozenset[str] = frozenset({"SALES_REP", "SALES_MANAGER"})


@dataclass(frozen=True)
class CurrentUser:
    user_id: uuid.UUID
    clerk_user_id: str
    email: str
    role: str


@dataclass(frozen=True)
class ClerkUserProfile:
    clerk_user_id: str
    email: str
    role: str | None


class ClerkClient:
    """Verifies session tokens and loads the Clerk user profile used for app_users sync."""

    def __init__(self, secret_key: str, authorized_parties: list[str]) -> None:
        self._secret_key = secret_key
        self._jwks = jwt.PyJWKClient(
            CLERK_JWKS_URL,
            headers={
                "Authorization": f"Bearer {secret_key}",
                "User-Agent": "ai-sales-intelligence-backend",
            },
            lifespan=3600,
            timeout=10,
        )
        self._authorized_parties = frozenset(authorized_parties)

    def verify_session_token(self, token: str) -> str:
        """Return the Clerk user id. Blocking: call from a thread."""
        try:
            signing_key = self._jwks.get_signing_key_from_jwt(token)
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                options={"require": ["exp", "sub"]},
                leeway=5,
            )
        except ExpiredSignatureError as exc:
            raise AuthExpiredError() from exc
        except PyJWKClientConnectionError as exc:
            logger.error(
                "Could not fetch Clerk signing keys",
                extra={"fields": {"error": type(exc).__name__}},
            )
            raise AuthInvalidError() from exc
        except PyJWTError as exc:
            raise AuthInvalidError() from exc

        authorized_party = claims.get("azp")
        if authorized_party and authorized_party not in self._authorized_parties:
            raise AuthInvalidError()
        return claims["sub"]

    def fetch_user_profile(self, clerk_user_id: str) -> ClerkUserProfile:
        """Load email and publicMetadata.role from Clerk. Blocking: call from a thread."""
        request = urllib.request.Request(
            f"{CLERK_USERS_URL}/{urllib.parse.quote(clerk_user_id, safe='')}",
            headers={
                "Authorization": f"Bearer {self._secret_key}",
                "User-Agent": "ai-sales-intelligence-backend",
            },
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            logger.error(
                "Clerk user fetch failed",
                extra={"fields": {"status": exc.code, "clerk_user_id": clerk_user_id}},
            )
            raise AuthInvalidError() from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            logger.error(
                "Clerk user fetch unavailable",
                extra={"fields": {"error": type(exc).__name__}},
            )
            raise AuthInvalidError() from exc

        email = _primary_email(payload)
        role_value = (payload.get("public_metadata") or {}).get("role")
        role = role_value if isinstance(role_value, str) else None
        return ClerkUserProfile(clerk_user_id=clerk_user_id, email=email, role=role)


def _primary_email(payload: dict) -> str:
    addresses = payload.get("email_addresses") or []
    primary_id = payload.get("primary_email_address_id")
    for address in addresses:
        if address.get("id") == primary_id and address.get("email_address"):
            return str(address["email_address"])
    for address in addresses:
        if address.get("email_address"):
            return str(address["email_address"])
    return ""


async def resolve_current_user(
    clerk_user_id: str,
    profile: ClerkUserProfile,
    users: AppUserRepository,
    session: AsyncSession,
) -> CurrentUser:
    if not profile.role:
        raise UserNotProvisionedError()
    if profile.role not in ROLES:
        raise UserWithoutRoleError()
    if not profile.email:
        raise UserWithoutRoleError()

    user = await users.upsert_from_clerk(clerk_user_id, profile.email, profile.role)
    await session.commit()
    return CurrentUser(
        user_id=user.user_id,
        clerk_user_id=user.clerk_user_id,
        email=user.email,
        role=user.role,
    )


def ensure_role(user: CurrentUser, allowed_roles: frozenset[str]) -> None:
    if user.role not in allowed_roles:
        raise InsufficientPermissionError()


# Backwards-compatible name used by older imports during the auth phase.
ClerkTokenVerifier = ClerkClient
