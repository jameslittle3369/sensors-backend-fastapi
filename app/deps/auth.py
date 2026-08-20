from fastapi import Depends, Header, HTTPException, status
from sqlmodel import Session

from app.deps.db import get_session
from app.models.token import Token
from app.models.user import User

# Matches DRF's TokenAuthentication header format exactly, and looks up
# the same authtoken_token table Django wrote to -- any client already
# holding a valid token keeps working with zero client-side changes.
AUTH_HEADER_PREFIX = "Token "


def _get_user_from_authorization(
    authorization: str | None, session: Session
) -> User | None:
    if not authorization or not authorization.startswith(AUTH_HEADER_PREFIX):
        return None
    key = authorization[len(AUTH_HEADER_PREFIX) :].strip()
    if not key:
        return None
    token = session.get(Token, key)
    if token is None:
        return None
    user = session.get(User, token.user_id)
    if user is None or not user.is_active:
        return None
    return user


async def get_current_user(
    authorization: str | None = Header(default=None),
    session: Session = Depends(get_session),
) -> User:
    user = _get_user_from_authorization(authorization, session)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided or are invalid.",
        )
    return user


async def get_current_user_optional(
    authorization: str | None = Header(default=None),
    session: Session = Depends(get_session),
) -> User | None:
    return _get_user_from_authorization(authorization, session)
