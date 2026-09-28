from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from .db import get_db
from .models import Student, Class, RoleEnum, User, StudentStatusEnum
from .dependencies import get_current_user, require_roles
from . import schemas

router = APIRouter()

@router.get("/class/{class_id}", response_model=List[schemas.StudentResponse])
def get_students_by_class(
    class_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db)
):
    # 1. Verifica se a turma existe
    db_class = session.query(Class).filter(Class.id == class_id).first()
    if not db_class:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Turma não encontrada.")

    # 2. Verifica a permissão (Admin/Diretor/Coordenador ou Professor atribuído)
    if current_user.role in {RoleEnum.ADMIN, RoleEnum.DIRETOR, RoleEnum.COORDENADOR}:
        pass
    elif current_user.role == RoleEnum.PROFESSOR:
        if not any(c.id == class_id for c in current_user.classes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem permissão para acessar os alunos desta turma."
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso não autorizado para esta função."
        )

    # 3. Retorna os alunos
    students = session.query(Student).filter(Student.class_id == class_id).all()
    # Pydantic v2 lidará com converter StudentStatusEnum para string
    return [
        schemas.StudentResponse(
            id=s.id,
            name=s.name,
            class_id=s.class_id,
            marketing_allowed=s.marketing_allowed,
            status=s.status.value,
            child_id=s.child_profile.id if s.child_profile else None,
        ) for s in students
    ]

@router.post("/", response_model=schemas.StudentResponse, status_code=status.HTTP_201_CREATED)
def create_student(
    student_in: schemas.StudentCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db)
):
    # 1. Verifica se a turma de destino existe
    db_class = session.query(Class).filter(Class.id == student_in.class_id).first()
    if not db_class:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Turma não encontrada.")

    # 2. Verifica a permissão para criar (Admin/Diretor/Coordenador ou Professor atribuído)
    if current_user.role in {RoleEnum.ADMIN, RoleEnum.DIRETOR, RoleEnum.COORDENADOR}:
        pass
    elif current_user.role == RoleEnum.PROFESSOR:
        if not any(c.id == student_in.class_id for c in current_user.classes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você só pode cadastrar alunos em turmas atribuídas a você."
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso não autorizado para esta função."
        )

    # 3. Salva no banco de dados
    new_student = Student(
        name=student_in.name,
        class_id=student_in.class_id,
        marketing_allowed=student_in.marketing_allowed,
        status=StudentStatusEnum.ATIVO
    )
    session.add(new_student)
    session.commit()
    session.refresh(new_student)
    
    return schemas.StudentResponse(
        id=new_student.id,
        name=new_student.name,
        class_id=new_student.class_id,
        marketing_allowed=new_student.marketing_allowed,
        status=new_student.status.value
    )


@router.get("/{student_id}/photos", response_model=List[schemas.PhotoResponse])
def get_student_photos(
    student_id: int,
    session: Session = Depends(get_db),
):
    """
    Retorna todas as fotos em que o aluno foi identificado (via vínculo direto ou cluster de faces).
    """
    from .photos import serialize_photo
    from .models import Photo, FaceCluster, DetectedFace

    student = session.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aluno não encontrado.")

    # 1. Fotos vinculadas diretamente
    direct_photo_ids = set(p.id for p in student.photos)

    # 2. Fotos identificadas através dos clusters de faces associados ao aluno
    cluster_photo_ids = set()
    clusters = session.query(FaceCluster).filter(FaceCluster.student_id == student_id).all()
    for c in clusters:
        for f in c.faces:
            if f.photo_id:
                cluster_photo_ids.add(f.photo_id)

    all_photo_ids = direct_photo_ids.union(cluster_photo_ids)
    if not all_photo_ids:
        return []

    photos = session.query(Photo).filter(Photo.id.in_(all_photo_ids)).order_by(Photo.created_at.desc()).all()
    return [serialize_photo(p) for p in photos]

