import json
import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from . import db, models, schemas, security
from .dependencies import get_current_user
from .photos import can_access_class

router = APIRouter()


def project_response(project: models.Project) -> schemas.ProjectResponse:
    try:
        objectives = json.loads(project.pedagogical_objectives)
    except (TypeError, json.JSONDecodeError):
        objectives = [project.pedagogical_objectives] if project.pedagogical_objectives else []
    paths = [photo.file_path for photo in project.photos] or [project.image_path]
    return schemas.ProjectResponse(
        id=project.id,
        child_id=project.child_id,
        title=project.title,
        image_url=security.generatePresignedUrl(paths[0]),
        image_urls=[security.generatePresignedUrl(path) for path in paths],
        completion_date=project.completion_date,
        description=project.description,
        pedagogical_objectives=objectives,
        created_at=project.created_at,
    )


@router.post("/", response_model=List[schemas.ProjectResponse], status_code=status.HTTP_201_CREATED)
def create_school_portfolio(
    payload: schemas.PortfolioCreate,
    current_user: models.User = Depends(get_current_user),
    session: Session = Depends(db.get_db),
):
    title = payload.title.strip()
    description = payload.description.strip()
    if not title or not description:
        raise HTTPException(status_code=422, detail="Informe título e descrição do portfólio.")
    if not payload.photo_ids or not payload.student_ids:
        raise HTTPException(status_code=422, detail="Selecione fotos e ao menos um aluno.")

    photo_ids = list(dict.fromkeys(payload.photo_ids))
    photos = session.query(models.Photo).filter(models.Photo.id.in_(photo_ids)).all()
    if len(photos) != len(photo_ids) or any(photo.class_id is None for photo in photos):
        raise HTTPException(status_code=404, detail="Uma ou mais fotos não foram encontradas.")
    class_id = photos[0].class_id
    if any(photo.class_id != class_id for photo in photos):
        raise HTTPException(status_code=422, detail="Todas as fotos devem pertencer à mesma turma.")
    if class_id is None or not can_access_class(current_user, class_id):
        raise HTTPException(status_code=403, detail="Você não tem acesso a estas fotos.")

    student_ids = list(dict.fromkeys(payload.student_ids))
    students = session.query(models.Student).filter(models.Student.id.in_(student_ids)).all()
    if len(students) != len(student_ids) or any(student.class_id != class_id for student in students):
        raise HTTPException(status_code=422, detail="Todos os alunos devem pertencer à turma das fotos.")
    missing = [student.name for student in students if not student.child_profile]
    if missing:
        raise HTTPException(status_code=422, detail=f"Sem perfil familiar vinculado: {', '.join(missing)}.")

    ordered_photos = sorted(photos, key=lambda item: photo_ids.index(item.id))
    objectives = [value.strip() for value in payload.pedagogical_objectives if value.strip()]
    projects = []
    for student in students:
        project = models.Project(
            id=str(uuid.uuid4()),
            child_id=student.child_profile.id,
            title=title,
            image_path=ordered_photos[0].file_path,
            completion_date=datetime.now(),
            description=description,
            pedagogical_objectives=json.dumps(objectives, ensure_ascii=False),
        )
        project.photos.extend(ordered_photos)
        projects.append(project)
        for photo in ordered_photos:
            if all(linked.id != student.id for linked in photo.students):
                photo.students.append(student)

    session.add_all(projects)
    session.commit()
    for project in projects:
        session.refresh(project)
    return [project_response(project) for project in projects]
