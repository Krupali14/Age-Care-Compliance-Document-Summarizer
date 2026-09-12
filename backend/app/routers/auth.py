from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.auth import create_access_token, hash_password, verify_password
from app.database import get_db
from app.models import User
from app.rate_limit import (
    LOGIN_MAX_ATTEMPTS,
    LOGIN_WINDOW_SECONDS,
    REGISTER_MAX_ATTEMPTS,
    REGISTER_WINDOW_SECONDS,
    client_ip,
    enforce,
)
from app.schemas import RegisterRequest, TokenResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(request: Request, payload: RegisterRequest, db: Session = Depends(get_db)):
    enforce(f"register:{client_ip(request)}", REGISTER_MAX_ATTEMPTS, REGISTER_WINDOW_SECONDS)
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(email=payload.email, hashed_password=hash_password(payload.password))
    db.add(user)
    db.commit()
    return {"id": user.id, "email": user.email}


@router.post("/login", response_model=TokenResponse)
def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Registration stores addresses lowercased, so sign-in has to match that way or
    # a capitalised address would silently fail to find its own account.
    email = form_data.username.strip().lower()
    # Limited on both axes: the address stops one account being ground through a
    # password list from many hosts, the address-plus-IP stops one host working
    # through many accounts. Counted before the password check, so a wrong guess is
    # never free, and bcrypt's cost is not a lever an attacker can pull.
    enforce(f"login:{email}", LOGIN_MAX_ATTEMPTS, LOGIN_WINDOW_SECONDS)
    enforce(f"login-ip:{client_ip(request)}", LOGIN_MAX_ATTEMPTS * 3, LOGIN_WINDOW_SECONDS)

    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    token = create_access_token(user.id, user.email)
    return TokenResponse(access_token=token)
