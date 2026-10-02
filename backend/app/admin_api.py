from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from . import models, schemas, security
from .db import get_db
from .dependencies import require_roles

router = APIRouter()
UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"
MANAGED_ROLES = {models.RoleEnum.PROFESSOR, models.RoleEnum.MARKETING}


def user_response(user: models.User) -> schemas.UserResponse:
    return schemas.UserResponse(
        id=user.id, school_id=user.school_id, name=user.name, email=user.email,
        role=user.role, is_active=user.is_active, created_at=user.created_at,
        class_ids=[item.id for item in user.classes],
    )


def validate_role(role: models.RoleEnum) -> None:
    if role not in MANAGED_ROLES:
        raise HTTPException(status_code=422, detail="Neste MVP, apenas Professor e Marketing podem ser cadastrados pelo painel.")


def find_classes(session: Session, school_id: int, class_ids: List[int]) -> List[models.Class]:
    ids = list(dict.fromkeys(class_ids))
    items = session.query(models.Class).filter(
        models.Class.school_id == school_id, models.Class.id.in_(ids)
    ).all() if ids else []
    if len(items) != len(ids):
        raise HTTPException(status_code=404, detail="Uma ou mais turmas não foram encontradas.")
    return items


@router.get("/summary", response_model=schemas.AdminSummaryResponse)
def summary(
    current_user: models.User = Depends(require_roles([models.RoleEnum.COORDENADOR])),
    session: Session = Depends(get_db),
):
    photos = session.query(models.Photo).filter(models.Photo.school_id == current_user.school_id).all()
    storage_bytes = 0
    missing_files = 0
    root = UPLOAD_DIR.resolve()
    for photo in photos:
        path = (root / photo.file_path).resolve()
        if root not in path.parents or not path.is_file():
            missing_files += 1
            continue
        storage_bytes += path.stat().st_size
    return schemas.AdminSummaryResponse(
        school=current_user.school,
        active_professionals=session.query(models.User).filter(
            models.User.school_id == current_user.school_id, models.User.is_active.is_(True)
        ).count(),
        active_classes=session.query(models.Class).filter(
            models.Class.school_id == current_user.school_id, models.Class.is_active.is_(True)
        ).count(),
        active_students=session.query(models.Student).filter(
            models.Student.school_id == current_user.school_id,
            models.Student.status == models.StudentStatusEnum.ATIVO,
        ).count(),
        photo_count=len(photos), storage_bytes=storage_bytes, missing_files=missing_files,
    )


@router.get("/users", response_model=List[schemas.UserResponse])
def list_users(
    include_inactive: bool = Query(False),
    current_user: models.User = Depends(require_roles([models.RoleEnum.COORDENADOR])),
    session: Session = Depends(get_db),
):
    query = session.query(models.User).filter(
        models.User.school_id == current_user.school_id, models.User.role.in_(MANAGED_ROLES)
    )
    if not include_inactive:
        query = query.filter(models.User.is_active.is_(True))
    return [user_response(item) for item in query.order_by(models.User.name).all()]


@router.post("/users", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: schemas.UserCreate,
    current_user: models.User = Depends(require_roles([models.RoleEnum.COORDENADOR])),
    session: Session = Depends(get_db),
):
    validate_role(payload.role)
    email = str(payload.email).strip().lower()
    if session.query(models.User).filter(models.User.email == email).first():
        raise HTTPException(status_code=409, detail="Este e-mail já está cadastrado.")
    item = models.User(
        school_id=current_user.school_id, name=payload.name.strip(), email=email,
        hashed_password=security.get_password_hash(payload.password), role=payload.role,
    )
    item.classes = find_classes(session, current_user.school_id, payload.class_ids) if payload.role == models.RoleEnum.PROFESSOR else []
    session.add(item)
    session.commit()
    session.refresh(item)
    return user_response(item)


@router.put("/users/{user_id}", response_model=schemas.UserResponse)
def update_user(
    user_id: int, payload: schemas.UserUpdate,
    current_user: models.User = Depends(require_roles([models.RoleEnum.COORDENADOR])),
    session: Session = Depends(get_db),
):
    item = session.query(models.User).filter(
        models.User.id == user_id, models.User.school_id == current_user.school_id,
        models.User.role.in_(MANAGED_ROLES),
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Profissional não encontrado.")
    values = payload.model_dump(exclude_unset=True)
    class_ids = values.pop("class_ids", None)
    password = values.pop("password", None)
    if "role" in values:
        validate_role(values["role"])
    if "email" in values:
        values["email"] = str(values["email"]).strip().lower()
        duplicate = session.query(models.User).filter(models.User.email == values["email"], models.User.id != item.id).first()
        if duplicate:
            raise HTTPException(status_code=409, detail="Este e-mail já está cadastrado.")
    if "name" in values:
        values["name"] = values["name"].strip()
    for key, value in values.items():
        setattr(item, key, value)
    if password:
        item.hashed_password = security.get_password_hash(password)
    if item.role == models.RoleEnum.PROFESSOR and class_ids is not None:
        item.classes = find_classes(session, current_user.school_id, class_ids)
    elif item.role != models.RoleEnum.PROFESSOR:
        item.classes = []
    session.commit()
    session.refresh(item)
    return user_response(item)


@router.delete("/users/{user_id}", response_model=schemas.UserResponse)
def deactivate_user(
    user_id: int,
    current_user: models.User = Depends(require_roles([models.RoleEnum.COORDENADOR])),
    session: Session = Depends(get_db),
):
    item = session.query(models.User).filter(
        models.User.id == user_id, models.User.school_id == current_user.school_id,
        models.User.role.in_(MANAGED_ROLES),
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Profissional não encontrado.")
    item.is_active = False
    session.commit()
    session.refresh(item)
    return user_response(item)
