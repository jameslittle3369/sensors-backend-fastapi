from datetime import UTC, datetime

from sqlmodel import Session, select

from app.core.security import generate_token_key, hash_password
from app.models.token import Token
from app.models.user import User


def get_user_by_email(session: Session, email: str) -> User | None:
    # users_user.email is a citext column -- comparison is already
    # case-insensitive at the DB level, no need for a manual lower().
    return session.exec(select(User).where(User.email == email)).first()


def create_user(
    session: Session, *, email: str, password: str, first_name: str = "", last_name: str = ""
) -> User:
    user = User(
        email=email,
        password=hash_password(password),
        first_name=first_name,
        last_name=last_name,
        date_joined=datetime.now(UTC),
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def get_or_create_token(session: Session, user: User) -> Token:
    token = session.exec(select(Token).where(Token.user_id == user.id)).first()
    if token is not None:
        return token
    token = Token(key=generate_token_key(), created=datetime.now(UTC), user_id=user.id)
    session.add(token)
    session.commit()
    session.refresh(token)
    return token
