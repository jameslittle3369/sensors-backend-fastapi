from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.errors import ApiFieldError
from app.core.security import verify_password
from app.deps.db import get_session
from app.schemas.auth import LoginRequest, LoginResponse
from app.services.auth_service import get_or_create_token, get_user_by_email

router = APIRouter(tags=["login"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, session: Session = Depends(get_session)) -> LoginResponse:
    user = get_user_by_email(session, payload.email)
    if user is None:
        raise ApiFieldError.field("email", "Email does not exist.")
    if not verify_password(payload.password, user.password):
        raise ApiFieldError.field("password", "Incorrect password.")
    token = get_or_create_token(session, user)
    return LoginResponse(token=token.key)
