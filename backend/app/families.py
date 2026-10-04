import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import db, models, schemas, security
from .dependencies import require_roles
from .photos import can_access_class

router = APIRouter()


def parent_school_filter(school_id):
    return or_(models.Parent.school_id == school_id, and_(
        models.Parent.school_id.is_(None),
        models.Parent.children.any(models.Child.school_id == school_id),
    ))


def parent_response(parent, school_id):
    return schemas.FamilyParentResponse(
        id=parent.id, name=parent.name, email=parent.email, phone=parent.phone,
        is_active=parent.is_active,
        student_ids=[child.student_profile.id for child in parent.children
                     if child.school_id == school_id and child.student_profile],
    )


def own_parent(parent_id, current_user, session):
    parent = session.query(models.Parent).filter(
        models.Parent.id == parent_id, parent_school_filter(current_user.school_id),
    ).first()
    if not parent:
        raise HTTPException(status_code=404, detail="Familiar não encontrado.")
    # Não altera uma conta legada compartilhada com outra escola.
    if any(child.school_id != current_user.school_id for child in parent.children):
        raise HTTPException(status_code=409, detail="Esta conta familiar é compartilhada com outra escola e não pode ser alterada neste painel.")
    return parent


def selected_students(ids, school_id, session):
    students = session.query(models.Student).filter(
        models.Student.id.in_(set(ids)), models.Student.school_id == school_id,
    ).all() if ids else []
    if len(students) != len(set(ids)):
        raise HTTPException(status_code=404, detail="Um ou mais alunos não foram encontrados.")
    return students


def assign_students(parent, students, school_id):
    wanted = {student.id for student in students}
    for child in list(parent.children):
        if child.school_id == school_id and child.student_profile and child.student_profile.id not in wanted:
            parent.children.remove(child)
    for student in students:
        if not student.child_profile:
            student.child_profile = models.Child(
                id=str(uuid.uuid4()), school_id=school_id, name=student.name,
                classroom=student.school_class.name, avatar_path="",
            )
        if student.child_profile not in parent.children:
            parent.children.append(student.child_profile)


def commit_parent(parent, school_id, session):
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="E-mail ou telefone já cadastrado.")
    session.refresh(parent)
    return parent_response(parent, school_id)


@router.get("/parents", response_model=List[schemas.FamilyParentResponse])
def list_school_parents(
    current_user: models.User = Depends(require_roles([models.RoleEnum.COORDENADOR])),
    session: Session = Depends(db.get_db),
    include_inactive: bool = False,
):
    query = session.query(models.Parent).filter(parent_school_filter(current_user.school_id))
    if not include_inactive:
        query = query.filter(models.Parent.is_active.is_(True))
    return [parent_response(parent, current_user.school_id) for parent in query.order_by(models.Parent.name).all()]


@router.post("/parents", response_model=schemas.FamilyParentResponse, status_code=201)
def create_parent(
    payload: schemas.FamilyParentCreate,
    current_user: models.User = Depends(require_roles([models.RoleEnum.COORDENADOR])),
    session: Session = Depends(db.get_db),
):
    students = selected_students(payload.student_ids, current_user.school_id, session)
    name = payload.name.strip()
    if len(name) < 2:
        raise HTTPException(status_code=422, detail="Informe o nome do familiar.")
    email = str(payload.email).strip().lower()
    if session.query(models.Parent).filter(models.Parent.email == email).first():
        raise HTTPException(status_code=409, detail="E-mail já cadastrado.")
    parent = models.Parent(id=str(uuid.uuid4()), school_id=current_user.school_id,
                           name=name, email=email, phone=(payload.phone or "").strip() or None,
                           hashed_password=security.get_password_hash(payload.password), is_active=True)
    session.add(parent)
    with session.no_autoflush:
        assign_students(parent, students, current_user.school_id)
    return commit_parent(parent, current_user.school_id, session)


@router.put("/parents/{parent_id}", response_model=schemas.FamilyParentResponse)
def update_parent(
    parent_id: str, payload: schemas.FamilyParentUpdate,
    current_user: models.User = Depends(require_roles([models.RoleEnum.COORDENADOR])),
    session: Session = Depends(db.get_db),
):
    parent = own_parent(parent_id, current_user, session)
    students = selected_students(payload.student_ids, current_user.school_id, session) if payload.student_ids is not None else None
    if payload.email is not None and session.query(models.Parent).filter(
        models.Parent.email == str(payload.email).strip().lower(), models.Parent.id != parent.id,
    ).first():
        raise HTTPException(status_code=409, detail="E-mail já cadastrado.")
    if payload.phone and session.query(models.Parent).filter(
        models.Parent.phone == payload.phone.strip(), models.Parent.id != parent.id,
    ).first():
        raise HTTPException(status_code=409, detail="Telefone já cadastrado.")
    if payload.name is not None:
        if len(payload.name.strip()) < 2:
            raise HTTPException(status_code=422, detail="Informe o nome do familiar.")
        parent.name = payload.name.strip()
    if payload.email is not None:
        parent.email = str(payload.email).strip().lower()
    if "phone" in payload.model_fields_set:
        parent.phone = (payload.phone or "").strip() or None
    if payload.password is not None:
        parent.hashed_password = security.get_password_hash(payload.password)
    if payload.is_active is not None:
        parent.is_active = payload.is_active
    parent.school_id = current_user.school_id
    if students is not None:
        with session.no_autoflush:
            assign_students(parent, students, current_user.school_id)
    return commit_parent(parent, current_user.school_id, session)


@router.delete("/parents/{parent_id}", response_model=schemas.FamilyParentResponse)
def deactivate_parent(
    parent_id: str,
    current_user: models.User = Depends(require_roles([models.RoleEnum.COORDENADOR])),
    session: Session = Depends(db.get_db),
):
    parent = own_parent(parent_id, current_user, session)
    parent.is_active = False
    parent.school_id = current_user.school_id
    return commit_parent(parent, current_user.school_id, session)


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
    current_user: models.User = Depends(require_roles([models.RoleEnum.COORDENADOR])),
    session: Session = Depends(db.get_db),
):
    children = session.query(models.Child).filter(
        models.Child.school_id == current_user.school_id
    ).order_by(models.Child.name).all()
    return [family_response(child) for child in children]


@router.post("/students/{student_id}", response_model=schemas.FamilyChildResponse, status_code=201)
def create_family_profile(
    student_id: int,
    payload: schemas.FamilyAccountCreate,
    current_user: models.User = Depends(require_roles([models.RoleEnum.COORDENADOR])),
    session: Session = Depends(db.get_db),
):
    student = session.query(models.Student).filter(
        models.Student.id == student_id, models.Student.school_id == current_user.school_id
    ).first()
    if not student:
        raise HTTPException(status_code=404, detail="Aluno não encontrado.")
    if not can_access_class(current_user, student.class_id):
        raise HTTPException(status_code=403, detail="Você não tem acesso a esta turma.")
    if student.child_profile:
        raise HTTPException(status_code=409, detail="Este aluno já possui um perfil familiar.")

    email = str(payload.parent_email).strip().lower()
    parent = session.query(models.Parent).filter(models.Parent.email == email).first()
    if parent and not session.query(models.Parent).filter(models.Parent.id == parent.id, parent_school_filter(current_user.school_id)).first():
        raise HTTPException(status_code=409, detail="E-mail já cadastrado.")
    if not parent:
        if len(payload.parent_name.strip()) < 2:
            raise HTTPException(status_code=422, detail="Informe o nome do responsável.")
        if not payload.initial_password or len(payload.initial_password) < 6:
            raise HTTPException(status_code=422, detail="A senha inicial deve ter ao menos 6 caracteres.")
        if payload.parent_phone and session.query(models.Parent).filter(models.Parent.phone == payload.parent_phone).first():
            raise HTTPException(status_code=409, detail="Este telefone já pertence a outro responsável.")
        parent = models.Parent(
            id=str(uuid.uuid4()),
            school_id=current_user.school_id,
            name=payload.parent_name.strip(),
            email=email,
            phone=payload.parent_phone.strip() if payload.parent_phone else None,
            hashed_password=security.get_password_hash(payload.initial_password),
            is_active=True,
        )
        session.add(parent)

    child = models.Child(
        id=str(uuid.uuid4()),
        school_id=current_user.school_id,
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
    current_user: models.User = Depends(require_roles([models.RoleEnum.COORDENADOR])),
    session: Session = Depends(db.get_db),
):
    student = session.query(models.Student).filter(
        models.Student.id == student_id, models.Student.school_id == current_user.school_id
    ).first()
    if not student:
        raise HTTPException(status_code=404, detail="Aluno não encontrado.")
    if not can_access_class(current_user, student.class_id):
        raise HTTPException(status_code=403, detail="Você não tem acesso a esta turma.")

    if payload.child_id is None:
        student.child_profile = None
    else:
        child = session.query(models.Child).filter(
            models.Child.id == payload.child_id, models.Child.school_id == current_user.school_id
        ).first()
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
        school_id=student.school_id,
        name=student.name,
        class_id=student.class_id,
        marketing_allowed=student.marketing_allowed,
        status=student.status.value,
        child_id=student.child_profile.id if student.child_profile else None,
        parent_ids=[parent.id for parent in student.child_profile.parents] if student.child_profile else [],
    )
