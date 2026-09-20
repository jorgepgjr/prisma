import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from . import db, models, schemas, security
from .dependencies import get_current_user
from .photos import can_access_class

router = APIRouter()


def family_response(child: models.Child) -> schemas.FamilyChildResponse:
    return schemas.FamilyChildResponse(
        id=child.id,
        name=child.name,
        classroom=child.classroom,
        avatar_url=security.generatePresignedUrl(child.avatar_path),
        parent_names=[parent.name for parent in child.parents],
        parent_emails=[parent.email for parent in child.parents],
        linked_student_id=child.student_profile.id if child.student_profile else None,
    )


@router.get("/children", response_model=List[schemas.FamilyChildResponse])
def list_family_children(
    current_user: models.User = Depends(get_current_user),
    session: Session = Depends(db.get_db),
):
    children = session.query(models.Child).order_by(models.Child.name).all()
    return [family_response(child) for child in children]


@router.post("/students/{student_id}", response_model=schemas.FamilyChildResponse, status_code=201)
def create_family_profile(
    student_id: int,
    payload: schemas.FamilyAccountCreate,
    current_user: models.User = Depends(get_current_user),
    session: Session = Depends(db.get_db),
):
    student = session.query(models.Student).filter(models.Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Aluno não encontrado.")
    if not can_access_class(current_user, student.class_id):
        raise HTTPException(status_code=403, detail="Você não tem acesso a esta turma.")
    if student.child_profile:
        raise HTTPException(status_code=409, detail="Este aluno já possui um perfil familiar.")

    email = str(payload.parent_email).strip().lower()
    parent = session.query(models.Parent).filter(models.Parent.email == email).first()
    if not parent:
        if len(payload.parent_name.strip()) < 2:
            raise HTTPException(status_code=422, detail="Informe o nome do responsável.")
        if not payload.initial_password or len(payload.initial_password) < 6:
            raise HTTPException(status_code=422, detail="A senha inicial deve ter ao menos 6 caracteres.")
        if payload.parent_phone and session.query(models.Parent).filter(models.Parent.phone == payload.parent_phone).first():
            raise HTTPException(status_code=409, detail="Este telefone já pertence a outro responsável.")
        parent = models.Parent(
            id=str(uuid.uuid4()),
            name=payload.parent_name.strip(),
            email=email,
            phone=payload.parent_phone.strip() if payload.parent_phone else None,
            hashed_password=security.get_password_hash(payload.initial_password),
            is_active=True,
        )
        session.add(parent)

    child = models.Child(
        id=str(uuid.uuid4()),
        name=student.name,
        avatar_path="",
        classroom=student.school_class.name,
    )
    parent.children.append(child)
    student.child_profile = child
    session.add(child)
    session.commit()
    session.refresh(child)
    return family_response(child)


@router.put("/students/{student_id}", response_model=schemas.StudentResponse)
def link_student_to_family_profile(
    student_id: int,
    payload: schemas.StudentFamilyLink,
    current_user: models.User = Depends(get_current_user),
    session: Session = Depends(db.get_db),
):
    student = session.query(models.Student).filter(models.Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Aluno não encontrado.")
    if not can_access_class(current_user, student.class_id):
        raise HTTPException(status_code=403, detail="Você não tem acesso a esta turma.")

    if payload.child_id is None:
        student.child_profile = None
    else:
        child = session.query(models.Child).filter(models.Child.id == payload.child_id).first()
        if not child:
            raise HTTPException(status_code=404, detail="Perfil familiar não encontrado.")
        if child.student_profile and child.student_profile.id != student.id:
            raise HTTPException(
                status_code=409,
                detail=f"O perfil {child.name} já está vinculado a outro aluno.",
            )
        student.child_profile = child

    session.commit()
    session.refresh(student)
    return schemas.StudentResponse(
        id=student.id,
        name=student.name,
        class_id=student.class_id,
        marketing_allowed=student.marketing_allowed,
        status=student.status.value,
        child_id=student.child_profile.id if student.child_profile else None,
    )
