from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlmodel import Session, col, func, or_, select

from app.core.errors import ApiFieldError
from app.core.pagination import build_page
from app.core.security import hash_password, verify_password
from app.deps.auth import get_current_user, get_current_user_optional
from app.deps.db import get_session
from app.models.user import User
from app.schemas.pagination import PAGE_SIZE, Page
from app.schemas.user import (
    ChangePasswordRequest,
    ConfirmEmailRequest,
    UserPublic,
    UserSelf,
    UserUpdateRequest,
)
from app.services.confirm_email import check_confirm_email_token

router = APIRouter(tags=["users"])


def _shape(user: User, requester: User | None) -> UserSelf | UserPublic:
    if requester is not None and requester.id == user.id:
        return UserSelf(
            id=user.id,
            email=user.email,
            is_email_verified=user.is_email_verified,
            first_name=user.first_name,
            last_name=user.last_name,
        )
    return UserPublic(id=user.id, first_name=user.first_name, last_name=user.last_name)


@router.get("/users", response_model=Page[UserSelf | UserPublic])
def list_users(
    request: Request,
    q: str | None = None,
    page: int = 1,
    session: Session = Depends(get_session),
    requester: User | None = Depends(get_current_user_optional),
) -> Page:
    statement = select(User).order_by(col(User.id))
    if q:
        pattern = f"%{q}%"
        statement = statement.where(
            or_(col(User.first_name).ilike(pattern), col(User.last_name).ilike(pattern))
        )
    total = session.exec(select(func.count()).select_from(statement.subquery())).one()
    rows = session.exec(statement.offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE)).all()
    return build_page(request, [_shape(u, requester) for u in rows], total, page)


@router.get("/users/me", response_model=UserSelf)
def get_me(user: User = Depends(get_current_user)) -> UserSelf:
    return _shape(user, user)


@router.post("/users/change-password")
def change_password(
    payload: ChangePasswordRequest,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    if not verify_password(payload.current_password, user.password):
        raise ApiFieldError.field("current_password", "That is not your current password.")
    user.password = hash_password(payload.new_password)
    session.add(user)
    session.commit()
    return {"detail": "success"}


@router.get("/users/{user_id}", response_model=UserSelf | UserPublic)
def get_user(
    user_id: int,
    session: Session = Depends(get_session),
    requester: User | None = Depends(get_current_user_optional),
) -> UserSelf | UserPublic:
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return _shape(user, requester)


@router.patch("/users/{user_id}", response_model=UserSelf)
@router.put("/users/{user_id}", response_model=UserSelf)
def update_user(
    user_id: int,
    payload: UserUpdateRequest,
    session: Session = Depends(get_session),
    requester: User = Depends(get_current_user),
) -> UserSelf:
    if requester.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    if payload.first_name is not None:
        requester.first_name = payload.first_name
    if payload.last_name is not None:
        requester.last_name = payload.last_name
    # avatar is accepted but ignored -- see UserUpdateRequest.avatar
    session.add(requester)
    session.commit()
    session.refresh(requester)
    return _shape(requester, requester)


@router.post("/users/{user_id}/confirm-email")
def confirm_email(
    user_id: int,
    payload: ConfirmEmailRequest,
    session: Session = Depends(get_session),
) -> dict:
    user = session.get(User, user_id)
    if user is None:
        # Django behavior: a nonexistent user id is a 400 non-field
        # error, not a 404.
        raise ApiFieldError.non_field("Invalid token")
    if not check_confirm_email_token(user, payload.token):
        raise ApiFieldError.field("token", "Invalid token")
    user.is_email_verified = True
    session.add(user)
    session.commit()
    return {}
