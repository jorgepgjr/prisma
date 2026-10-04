from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from . import db, models, schemas, security
from .dependencies import get_current_user

router = APIRouter()

def get_user_by_email(session: Session, email: str):
    return session.query(models.User).filter(models.User.email == email).first()

@router.post("/login", response_model=schemas.Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(db.get_db)
):
    user = get_user_by_email(session, email=form_data.username)
    if (
        not user
        or not user.is_active
        or not user.school
        or not user.school.is_active
        or not security.verify_password(form_data.password, user.hashed_password)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.email, "role": user.role.value, "school_id": user.school_id}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=schemas.CurrentUserResponse)
def get_me(current_user: models.User = Depends(get_current_user)):
    return schemas.CurrentUserResponse(
        id=current_user.id,
        school_id=current_user.school_id,
        name=current_user.name,
        email=current_user.email,
        role=current_user.role,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        class_ids=[item.id for item in current_user.classes],
        school=current_user.school,
    )
