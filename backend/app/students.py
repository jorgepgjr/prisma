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
            status=s.status.value
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
