from itsdangerous import BadSignature, URLSafeTimedSerializer

from app.core.config import get_settings
from app.models.user import User

# Deliberately a NEW signing scheme, not a replica of Django's
# django.core.signing algorithm. No welcome email is sent by either the
# old flow (forgot/change-email infra isn't ported) or the new one (no
# email side effect on register in this migration), so there's no
# realistic pre-migration confirmation link left to honor. Any such link
# will now 400 as "Invalid token" -- an intentional, documented break.
_SALT = "confirm_email"


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(get_settings().secret_key, salt=_SALT)


def generate_confirm_email_token(user: User) -> str:
    return _serializer().dumps([user.id, user.email])


def check_confirm_email_token(user: User, token: str) -> bool:
    try:
        payload = _serializer().loads(token)
    except BadSignature:
        return False
    return payload == [user.id, user.email]
