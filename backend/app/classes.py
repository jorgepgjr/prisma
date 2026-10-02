from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from . import schemas
from .db import get_db
from .dependencies import get_current_user, require_roles
from .models import Class, RoleEnum, User

router = APIRouter()


def class_response(item: Class) -> schemas.ClassResponse:
    return schemas.ClassResponse(
        id=item.id, school_id=item.school_id, name=item.name, year=item.year,
        is_active=item.is_active, created_at=item.created_at,
        teacher_ids=[teacher.id for teacher in item.teachers],
    )


def school_teachers(session: Session, school_id: int, teacher_ids: List[int]) -> List[User]:
    ids = list(dict.fromkeys(teacher_ids))
    teachers = session.query(User).filter(
        User.school_id == school_id, User.id.in_(ids), User.role == RoleEnum.PROFESSOR
    ).all() if ids else []
    if len(teachers) != len(ids):
        raise HTTPException(status_code=404, detail="Um ou mais professores não foram encontrados.")
    return teachers


@router.get("/", response_model=List[schemas.ClassResponse])
def get_classes(
    include_inactive: bool = Query(False),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    if current_user.role == RoleEnum.MARKETING:
        raise HTTPException(status_code=403, detail="Acesso não autorizado para esta função.")
    query = session.query(Class).filter(Class.school_id == current_user.school_id)
    if not include_inactive:
        query = query.filter(Class.is_active.is_(True))
    if current_user.role == RoleEnum.PROFESSOR:
        query = query.filter(Class.teachers.any(User.id == current_user.id))
    return [class_response(item) for item in query.order_by(Class.year.desc(), Class.name).all()]


@router.post("/", response_model=schemas.ClassResponse, status_code=status.HTTP_201_CREATED)
def create_class(
    payload: schemas.ClassCreate,
    current_user: User = Depends(require_roles([RoleEnum.COORDENADOR])),
    session: Session = Depends(get_db),
):
    duplicate = session.query(Class).filter(
        Class.school_id == current_user.school_id,
        Class.name == payload.name.strip(), Class.year == payload.year,
    ).first()
    if duplicate:
        raise HTTPException(status_code=409, detail="Já existe uma turma com esse nome e ano.")
    item = Class(school_id=current_user.school_id, name=payload.name.strip(), year=payload.year)
    item.teachers = school_teachers(session, current_user.school_id, payload.teacher_ids)
    session.add(item)
    session.commit()
    session.refresh(item)
    return class_response(item)


@router.put("/{class_id}", response_model=schemas.ClassResponse)
def update_class(
    class_id: int, payload: schemas.ClassUpdate,
    current_user: User = Depends(require_roles([RoleEnum.COORDENADOR])),
    session: Session = Depends(get_db),
):
    item = session.query(Class).filter(Class.id == class_id, Class.school_id == current_user.school_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Turma não encontrada.")
    values = payload.model_dump(exclude_unset=True)
    teacher_ids = values.pop("teacher_ids", None)
    if "name" in values:
        values["name"] = values["name"].strip()
    for key, value in values.items():
        setattr(item, key, value)
    if teacher_ids is not None:
        item.teachers = school_teachers(session, current_user.school_id, teacher_ids)
    duplicate = session.query(Class).filter(
        Class.school_id == current_user.school_id, Class.name == item.name,
        Class.year == item.year, Class.id != item.id,
    ).first()
    if duplicate:
        raise HTTPException(status_code=409, detail="Já existe uma turma com esse nome e ano.")
    session.commit()
    session.refresh(item)
    return class_response(item)


@router.delete("/{class_id}", response_model=schemas.ClassResponse)
def deactivate_class(
    class_id: int,
    current_user: User = Depends(require_roles([RoleEnum.COORDENADOR])),
    session: Session = Depends(get_db),
):
    item = session.query(Class).filter(Class.id == class_id, Class.school_id == current_user.school_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Turma não encontrada.")
    item.is_active = False
    session.commit()
    session.refresh(item)
    return class_response(item)
