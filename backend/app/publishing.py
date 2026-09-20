import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from . import db, models, schemas, security
from .dependencies import get_current_user
from .photos import can_access_class

router = APIRouter()


def post_response(post: models.Post, photo_id: int | None = None) -> schemas.ManagedPostResponse:
    paths = [photo.file_path for photo in post.photos] or [post.image_path]
    return schemas.ManagedPostResponse(
        id=post.id,
        classroom_name=post.classroom_name,
        teacher_name=post.teacher_name,
        teacher_avatar_url=post.teacher_avatar_url,
        image_url=security.generatePresignedUrl(post.image_path),
        image_urls=[security.generatePresignedUrl(path) for path in paths],
        caption=post.caption,
        created_at=post.created_at,
        photo_id=photo_id or (post.photos[0].id if post.photos else None),
        child_names=[child.name for child in post.children],
    )


@router.get("/", response_model=List[schemas.ManagedPostResponse])
def list_school_posts(
    class_id: int,
    current_user: models.User = Depends(get_current_user),
    session: Session = Depends(db.get_db),
):
    if not can_access_class(current_user, class_id):
        raise HTTPException(status_code=403, detail="Você não tem acesso a esta turma.")
    school_class = session.query(models.Class).filter(models.Class.id == class_id).first()
    if not school_class:
        raise HTTPException(status_code=404, detail="Turma não encontrada.")
    posts = (
        session.query(models.Post)
        .filter(models.Post.classroom_name == school_class.name)
        .order_by(models.Post.created_at.desc())
        .all()
    )
    return [post_response(post) for post in posts]


@router.post("/", response_model=schemas.ManagedPostResponse, status_code=status.HTTP_201_CREATED)
def create_school_post(
    payload: schemas.PostCreate,
    current_user: models.User = Depends(get_current_user),
    session: Session = Depends(db.get_db),
):
    caption = payload.caption.strip()
    if not caption:
        raise HTTPException(status_code=422, detail="Escreva uma legenda para a publicação.")
    if not payload.student_ids:
        raise HTTPException(status_code=422, detail="Selecione ao menos um aluno.")
    if not payload.photo_ids:
        raise HTTPException(status_code=422, detail="Selecione ao menos uma foto.")

    selected_photo_ids = list(dict.fromkeys(payload.photo_ids))
    photos = session.query(models.Photo).filter(models.Photo.id.in_(selected_photo_ids)).all()
    if len(photos) != len(selected_photo_ids) or any(photo.class_id is None for photo in photos):
        raise HTTPException(status_code=404, detail="Uma ou mais fotos não foram encontradas.")
    class_id = photos[0].class_id
    if any(photo.class_id != class_id for photo in photos):
        raise HTTPException(status_code=422, detail="Todas as fotos devem pertencer à mesma turma.")
    if class_id is None or not can_access_class(current_user, class_id):
        raise HTTPException(status_code=403, detail="Você não tem acesso a estas fotos.")

    selected_ids = set(payload.student_ids)
    students = session.query(models.Student).filter(models.Student.id.in_(selected_ids)).all()
    if len(students) != len(selected_ids) or any(student.class_id != class_id for student in students):
        raise HTTPException(status_code=422, detail="Todos os alunos devem pertencer à turma da foto.")

    children = [student.child_profile for student in students if student.child_profile]
    if len(children) != len(students):
        missing = [student.name for student in students if not student.child_profile]
        raise HTTPException(status_code=422, detail=f"Sem perfil familiar vinculado: {', '.join(missing)}.")

    post = models.Post(
        id=str(uuid.uuid4()),
        classroom_name=photos[0].school_class.name,
        teacher_name=current_user.name,
        teacher_avatar_url="",
        image_path=photos[0].file_path,
        caption=caption,
    )
    post.children.extend(children)
    post.photos.extend(sorted(photos, key=lambda item: selected_photo_ids.index(item.id)))
    for photo in photos:
        linked_ids = {student.id for student in photo.students}
        photo.students.extend(student for student in students if student.id not in linked_ids)
    session.add(post)
    session.commit()
    session.refresh(post)
    return post_response(post, photos[0].id)
