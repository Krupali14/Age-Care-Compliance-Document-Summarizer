import re

from pydantic import BaseModel, field_validator

# Deliberately permissive: enough to catch a value that is plainly not an address,
# without pretending to arbitrate what the RFC allows.
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

MIN_PASSWORD_LENGTH = 8
# bcrypt hashes only the first 72 bytes and silently ignores the rest, so a longer
# password would appear to be accepted while its tail did nothing. Rejecting it is
# honest; truncating it quietly is not.
MAX_PASSWORD_BYTES = 72


class RegisterRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def _check_email(cls, value: str) -> str:
        value = value.strip()
        if not _EMAIL.match(value):
            raise ValueError("Enter a valid email address")
        return value.lower()

    @field_validator("password")
    @classmethod
    def _check_password(cls, value: str) -> str:
        if len(value) < MIN_PASSWORD_LENGTH:
            raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters")
        if len(value.encode("utf-8")) > MAX_PASSWORD_BYTES:
            raise ValueError(f"Password must be at most {MAX_PASSWORD_BYTES} bytes")
        return value


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UploadResponse(BaseModel):
    id: int
    filename: str
    status: str
