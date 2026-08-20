from datetime import UTC, datetime

from sqlmodel import Session

from app.core.security import generate_token_key, hash_password
from app.models.token import Token
from app.models.user import User


def make_user(
    session: Session,
    *,
    email: str = "user@example.com",
    password: str = "password123",
    first_name: str = "Jane",
    last_name: str = "Doe",
    is_email_verified: bool = False,
) -> User:
    user = User(
        email=email,
        password=hash_password(password),
        first_name=first_name,
        last_name=last_name,
        is_email_verified=is_email_verified,
        date_joined=datetime.now(UTC),
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def make_token(session: Session, user: User) -> Token:
    token = Token(key=generate_token_key(), created=datetime.now(UTC), user_id=user.id)
    session.add(token)
    session.commit()
    session.refresh(token)
    return token


def auth_headers(session: Session, user: User) -> dict:
    token = make_token(session, user)
    return {"Authorization": f"Token {token.key}"}
