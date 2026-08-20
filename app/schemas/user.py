from pydantic import BaseModel, EmailStr


class UserPublic(BaseModel):
    id: int
    first_name: str
    last_name: str
    # Avatar is deliberately simplified for this migration: django-avatar
    # + easy-thumbnails is not rebuilt. Always null for now -- clients
    # reading this key won't KeyError, they'll just see no avatar.
    avatar: None = None


class UserSelf(BaseModel):
    id: int
    email: str
    is_email_verified: bool
    first_name: str
    last_name: str
    avatar: None = None


class UserUpdateRequest(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    # Accepted but ignored -- avatar upload isn't implemented (see
    # UserPublic/UserSelf.avatar).
    avatar: str | None = None


class RegisterRequest(BaseModel):
    first_name: str = ""
    last_name: str = ""
    email: EmailStr
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class ConfirmEmailRequest(BaseModel):
    token: str
