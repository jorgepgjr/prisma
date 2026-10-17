from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from . import schemas
from .db import get_db
from .dependencies import get_current_user, require_roles
from .families import parent_school_filter
from .models import Child, Parent, Class, RoleEnum, Student, StudentStatusEnum, User

router = APIRouter()


def student_response(item: Student) -> schemas.StudentResponse:
    return schemas.StudentResponse(
        id=item.id, school_id=item.school_id, name=item.name, class_id=item.class_id,
        marketing_allowed=item.marketing_allowed, status=item.status.value,
        child_id=item.child_profile.id if item.child_profile else None,
        parent_ids=[parent.id for parent in item.child_profile.parents] if item.child_profile else [],
    )


def own_class(session: Session, class_id: int, school_id: int) -> Class:
    item = session.query(Class).filter(Class.id == class_id, Class.school_id == school_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Turma não encontrada.")
    return item


def set_student_parents(item: Student, parent_ids: List[str], session: Session):
    ids = set(parent_ids)
    parents = session.query(Parent).filter(
        Parent.id.in_(ids), parent_school_filter(item.school_id),
    ).all() if ids else []
    if len(parents) != len(ids):
        raise HTTPException(status_code=404, detail="Um ou mais responsáveis não foram encontrados nesta escola.")
    if parents and not item.child_profile:
        school_class = own_class(session, item.class_id, item.school_id)
        item.child_profile = Child(
            id=str(uuid.uuid4()), school_id=item.school_id, name=item.name,
            classroom=school_class.name, avatar_path="",
        )
    if item.child_profile:
        item.child_profile.parents = parents


@router.get("/", response_model=List[schemas.StudentResponse])
def list_students(
    class_id: Optional[int] = None, include_inactive: bool = Query(False),
    current_user: User = Depends(require_roles([RoleEnum.COORDENADOR])),
    session: Session = Depends(get_db),
):
    query = session.query(Student).filter(Student.school_id == current_user.school_id)
    if class_id is not None:
        own_class(session, class_id, current_user.school_id)
        query = query.filter(Student.class_id == class_id)
    if not include_inactive:
        query = query.filter(Student.status == StudentStatusEnum.ATIVO)
    return [student_response(item) for item in query.order_by(Student.name).all()]


@router.get("/class/{class_id}", response_model=List[schemas.StudentResponse])
def get_students_by_class(
    class_id: int, current_user: User = Depends(get_current_user), session: Session = Depends(get_db),
):
    school_class = own_class(session, class_id, current_user.school_id)
    if current_user.role == RoleEnum.MARKETING:
        raise HTTPException(status_code=404, detail="Turma não encontrada.")
    if current_user.role == RoleEnum.PROFESSOR and current_user not in school_class.teachers:
        raise HTTPException(status_code=404, detail="Turma não encontrada.")
    items = session.query(Student).filter(
        Student.school_id == current_user.school_id, Student.class_id == class_id,
        Student.status == StudentStatusEnum.ATIVO,
    ).order_by(Student.name).all()
    return [student_response(item) for item in items]


@router.post("/", response_model=schemas.StudentResponse, status_code=status.HTTP_201_CREATED)
def create_student(
    payload: schemas.StudentCreate,
    current_user: User = Depends(require_roles([RoleEnum.COORDENADOR])),
    session: Session = Depends(get_db),
):
    own_class(session, payload.class_id, current_user.school_id)
    item = Student(
        school_id=current_user.school_id, name=payload.name.strip(), class_id=payload.class_id,
        marketing_allowed=payload.marketing_allowed, status=StudentStatusEnum.ATIVO,
    )
    set_student_parents(item, payload.parent_ids, session)
    session.add(item)
    session.commit()
    session.refresh(item)
    return student_response(item)


@router.put("/{student_id}", response_model=schemas.StudentResponse)
def update_student(
    student_id: int, payload: schemas.StudentUpdate,
    current_user: User = Depends(require_roles([RoleEnum.COORDENADOR])),
    session: Session = Depends(get_db),
):
    item = session.query(Student).filter(Student.id == student_id, Student.school_id == current_user.school_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Criança não encontrada.")
    values = payload.model_dump(exclude_unset=True)
    parent_ids = values.pop("parent_ids", None)
    is_active = values.pop("is_active", None)
    if "class_id" in values:
        own_class(session, values["class_id"], current_user.school_id)
    if "name" in values:
        values["name"] = values["name"].strip()
    for key, value in values.items():
        setattr(item, key, value)
    if is_active is not None:
        item.status = StudentStatusEnum.ATIVO if is_active else StudentStatusEnum.INATIVO
    if item.child_profile:
        item.child_profile.name = item.name
        item.child_profile.classroom = own_class(session, item.class_id, item.school_id).name
    if parent_ids is not None:
        set_student_parents(item, parent_ids, session)
    session.commit()
    session.refresh(item)
    return student_response(item)


@router.delete("/{student_id}", response_model=schemas.StudentResponse)
def deactivate_student(
    student_id: int,
    current_user: User = Depends(require_roles([RoleEnum.COORDENADOR])),
    session: Session = Depends(get_db),
):
    item = session.query(Student).filter(Student.id == student_id, Student.school_id == current_user.school_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Criança não encontrada.")
    item.status = StudentStatusEnum.INATIVO
    session.commit()
    session.refresh(item)
    return student_response(item)


@router.get("/{student_id}/photos", response_model=List[schemas.PhotoResponse])
def get_student_photos(
    student_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """
    Retorna todas as fotos em que o aluno foi identificado (via vínculo direto ou cluster de faces).
    """
    from .photos import serialize_photo
    from .models import DetectedFace, FaceCluster, Photo

    student = session.query(Student).filter(
        Student.id == student_id, Student.school_id == current_user.school_id,
    ).first()
    if not student or current_user.role == RoleEnum.MARKETING:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aluno não encontrado.")
    if current_user.role == RoleEnum.PROFESSOR and current_user not in student.school_class.teachers:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aluno não encontrado.")

    # 1. Fotos vinculadas diretamente
    direct_photo_ids = set(p.id for p in student.photos)

    # 2. Fotos identificadas através dos clusters de faces associados ao aluno
    cluster_photo_ids = {
        photo_id for (photo_id,) in session.query(DetectedFace.photo_id)
        .join(FaceCluster, FaceCluster.id == DetectedFace.cluster_id)
        .join(Photo, Photo.id == DetectedFace.photo_id)
        .filter(
            FaceCluster.student_id == student.id,
            Photo.school_id == current_user.school_id,
        ).distinct().all()
    }

    all_photo_ids = direct_photo_ids.union(cluster_photo_ids)
    if not all_photo_ids:
        return []

    photos = session.query(Photo).filter(
        Photo.id.in_(all_photo_ids), Photo.school_id == current_user.school_id,
    ).order_by(Photo.created_at.desc()).all()
    return [serialize_photo(p) for p in photos]
