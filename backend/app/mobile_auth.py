from datetime import timedelta
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy.orm import Session

from . import models, security
from .account_email import email_accounts, normalize_email
from .db import get_db

router = APIRouter()
bearer = OAuth2PasswordBearer(tokenUrl="/api/mobile/auth/login")


class MobileLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email", mode="before")
    @classmethod
    def clean_email(cls, value):
        return normalize_email(value)


class MobileProfile(BaseModel):
    id: str
    profile: Literal["PROFESSOR", "FAMILIAR"]
    name: str
    email: str
    school_id: Optional[int] = None
    school_name: Optional[str] = None


class MobileToken(BaseModel):
    access_token: str
    token_type: str = "bearer"
    account: MobileProfile


def validate_account(account, profile, session):
    active = account.is_active
    school = session.get(models.School, account.school_id) if account.school_id is not None else None
    if account.school_id is not None and (not school or not school.is_active):
        active = False
    if profile == "PROFESSOR":
        active = active and school is not None and account.role == models.RoleEnum.PROFESSOR
    else:
        active = active and security.parent_school_is_active(account, session)
    if not active:
        raise HTTPException(status_code=403, detail="Esta conta não tem acesso ao aplicativo. Consulte a escola.")
    return MobileProfile(id=str(account.id), profile=profile, name=account.name,
                         email=normalize_email(account.email), school_id=account.school_id,
                         school_name=school.name if school else None)


def unique_account(session, email):
    users, parents = email_accounts(session, email)
    if len(users) + len(parents) > 1:
        raise HTTPException(status_code=409, detail="Há mais de um cadastro para este e-mail. Solicite a correção à escola.")
    return (users[0], "PROFESSOR") if users else ((parents[0], "FAMILIAR") if parents else (None, None))


@router.post("/login", response_model=MobileToken)
def login(payload: MobileLogin, session: Session = Depends(get_db)):
    account, profile = unique_account(session, payload.email)
    try:
        valid_password = bool(account and account.hashed_password and security.verify_password(payload.password, account.hashed_password))
    except (ValueError, TypeError):
        valid_password = False
    if not valid_password:
        raise HTTPException(status_code=401, detail="E-mail ou senha inválidos.")
    context = validate_account(account, profile, session)
    # Mantém o subject esperado pelos endpoints já existentes de cada área.
    subject = account.email if profile == "PROFESSOR" else account.id
    token = security.create_access_token(
        {"sub": subject, "mobile_profile": profile, "school_id": account.school_id},
        expires_delta=timedelta(minutes=30) if profile == "PROFESSOR" else timedelta(days=30),
    )
    return MobileToken(access_token=token, account=context)


@router.get("/me", response_model=MobileProfile)
def me(token: str = Depends(bearer), session: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, security.SECRET_KEY, algorithms=[security.ALGORITHM])
        profile = payload.get("mobile_profile")
        subject = payload.get("sub")
        if profile == "PROFESSOR":
            account = session.query(models.User).filter(models.User.email == subject).first()
        elif profile == "FAMILIAR":
            account = session.get(models.Parent, subject) if subject else None
        else:
            account = None
        if not account:
            raise HTTPException(status_code=401, detail="Sessão inválida. Entre novamente.")
    except JWTError:
        raise HTTPException(status_code=401, detail="Sessão expirada. Entre novamente.")
    unique, current_profile = unique_account(session, account.email)
    if unique is not account or current_profile != profile:
        raise HTTPException(status_code=401, detail="Sessão inválida.")
    return validate_account(account, profile, session)
