from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from .db import get_db
from .models import Class, RoleEnum, User
from .dependencies import get_current_user, require_roles
from . import schemas

router = APIRouter()

@router.get("/", response_model=List[schemas.ClassResponse])
def get_classes(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db)
):
    if current_user.role in {RoleEnum.ADMIN, RoleEnum.DIRETOR, RoleEnum.COORDENADOR}:
        return session.query(Class).all()
    elif current_user.role == RoleEnum.PROFESSOR:
        return current_user.classes
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso não autorizado para esta função."
        )

@router.post("/", response_model=schemas.ClassResponse, status_code=status.HTTP_201_CREATED)
def create_class(
    class_in: schemas.ClassCreate,
    current_user: User = Depends(require_roles([RoleEnum.ADMIN, RoleEnum.DIRETOR, RoleEnum.COORDENADOR])),
    session: Session = Depends(get_db)
):
    new_class = Class(
        name=class_in.name,
        year=class_in.year
    )
    session.add(new_class)
    session.commit()
    session.refresh(new_class)
    return new_class
