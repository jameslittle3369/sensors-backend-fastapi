import binascii
import os

from passlib.context import CryptContext

# Matches Django's default PASSWORD_HASHERS[0]
# (django.contrib.auth.hashers.PBKDF2PasswordHasher), format
# "pbkdf2_sha256$<iterations>$<salt>$<hash>". Verifies existing hashes
# already in users_user.password as-is and produces new hashes in the
# same format, so no user needs to reset their password.
pwd_context = CryptContext(schemes=["django_pbkdf2_sha256"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)


def generate_token_key() -> str:
    # Matches rest_framework.authtoken.models.Token.generate_key()
    return binascii.hexlify(os.urandom(20)).decode()
