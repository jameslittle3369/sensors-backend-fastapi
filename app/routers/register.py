from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.core.errors import ApiFieldError
from app.deps.db import get_session
from app.schemas.user import RegisterRequest, UserSelf
from app.services.auth_service import create_user, get_user_by_email

router = APIRouter(tags=["register"])


@router.post("/register", response_model=UserSelf, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, session: Session = Depends(get_session)) -> UserSelf:
    if get_user_by_email(session, payload.email) is not None:
        raise ApiFieldError.field("email", "That email is already in use.  Choose another.")
    user = create_user(
        session,
        email=payload.email,
        password=payload.password,
        first_name=payload.first_name,
        last_name=payload.last_name,
    )
    # No welcome email is sent here (Celery/djmail are out of scope for
    # this migration) -- see app/services/confirm_email.py for the
    # related note on why no in-flight confirmation tokens need honoring.
    return UserSelf(
        id=user.id,
        email=user.email,
        is_email_verified=user.is_email_verified,
        first_name=user.first_name,
        last_name=user.last_name,
    )
