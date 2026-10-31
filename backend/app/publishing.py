import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session, selectinload

from . import db, models, schemas, security
from .dependencies import get_current_user
from .photos import can_access_class, require_class_access

router = APIRouter()


def require_publisher(user):
    if user.role not in {models.RoleEnum.COORDENADOR, models.RoleEnum.PROFESSOR}:
        raise HTTPException(status_code=403, detail="Perfil sem acesso às publicações.")


def can_manage(post, user):
    return user.role == models.RoleEnum.COORDENADOR or (
        user.role == models.RoleEnum.PROFESSOR and post.created_by_user_id == user.id
    )


def post_response(post: models.Post, current_user: models.User) -> schemas.ManagedPostResponse:
    photos = post.ordered_photos
    paths = [photo.file_path for photo in photos]
    if not post.photos:
        paths = [post.image_path]
    return schemas.ManagedPostResponse(
        id=post.id, class_id=post.class_id, created_by_user_id=post.created_by_user_id,
        classroom_name=post.classroom_name, teacher_name=post.teacher_name,
        teacher_avatar_url=post.teacher_avatar_url or "",
        image_url=security.generatePresignedUrl(paths[0]) if paths else "",
        image_urls=[security.generatePresignedUrl(path) for path in paths],
        caption=post.caption, created_at=post.created_at,
        photo_id=photos[0].id if photos else None, photo_ids=[photo.id for photo in photos],
        child_names=[child.name for child in post.children if child.school_id == post.school_id],
        student_ids=[child.student_profile.id for child in post.children
                     if child.school_id == post.school_id and child.student_profile
                     and child.student_profile.school_id == post.school_id],
        can_manage=can_manage(post, current_user),
    )


def posts_query(session, user):
    require_publisher(user)
    query = session.query(models.Post).options(
        selectinload(models.Post.photos),
        selectinload(models.Post.children).selectinload(models.Child.student_profile),
    ).filter(models.Post.school_id == user.school_id)
    if user.role == models.RoleEnum.PROFESSOR:
        allowed = [item.id for item in user.classes if item.school_id == user.school_id and item.is_active]
        query = query.filter(models.Post.class_id.in_(allowed))
    return query


def owned_post(post_id, user, session, *, write=False):
    post = posts_query(session, user).filter(models.Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Publicação não encontrada.")
    if write and not can_manage(post, user):
        raise HTTPException(status_code=403, detail="Você só pode alterar as publicações que criou.")
    return post


def validate_content(payload, user, session, fixed_class_id=None):
    require_publisher(user)
    caption = payload.caption.strip()
    if not caption:
        raise HTTPException(status_code=422, detail="Escreva uma legenda para a publicação.")
    if not payload.student_ids or not payload.photo_ids:
        raise HTTPException(status_code=422, detail="Selecione ao menos uma foto e um aluno.")
    photo_ids = list(dict.fromkeys(payload.photo_ids))
    photos = session.query(models.Photo).filter(
        models.Photo.school_id == user.school_id, models.Photo.id.in_(photo_ids)
    ).all()
    if len(photos) != len(photo_ids) or any(photo.class_id is None for photo in photos):
        raise HTTPException(status_code=404, detail="Uma ou mais fotos não foram encontradas.")
    class_id = photos[0].class_id
    if any(photo.class_id != class_id for photo in photos):
        raise HTTPException(status_code=422, detail="Todas as fotos devem pertencer à mesma turma.")
    if fixed_class_id is not None and class_id != fixed_class_id:
        raise HTTPException(status_code=422, detail="Não é possível alterar a turma de uma publicação.")
    if fixed_class_id is not None and user.role == models.RoleEnum.COORDENADOR:
        school_class = session.query(models.Class).filter(models.Class.id == class_id,
            models.Class.school_id == user.school_id).first()
        if not school_class:
            raise HTTPException(status_code=404, detail="Turma não encontrada.")
    else:
        school_class = require_class_access(user, class_id, session)
    student_ids = set(payload.student_ids)
    students = session.query(models.Student).filter(
        models.Student.school_id == user.school_id, models.Student.id.in_(student_ids)
    ).all()
    if len(students) != len(student_ids):
        raise HTTPException(status_code=404, detail="Um ou mais alunos não foram encontrados.")
    if any(student.class_id != class_id or student.status != models.StudentStatusEnum.ATIVO for student in students):
        raise HTTPException(status_code=422, detail="Selecione alunos ativos da turma da foto.")
    if any(not student.child_profile or student.child_profile.school_id != user.school_id for student in students):
        raise HTTPException(status_code=422, detail="Há alunos sem perfil familiar vinculado. Procure a coordenação.")
    ordered = sorted(photos, key=lambda photo: photo_ids.index(photo.id))
    return caption, school_class, ordered, students


def apply_content(post, caption, school_class, photos, students):
    post.caption = caption
    post.class_id = school_class.id
    post.classroom_name = school_class.name
    post.image_path = photos[0].file_path
    post.photo_order = [photo.id for photo in photos]
    post.photos = photos
    post.children = [student.child_profile for student in students]
    # Preserve identification links made outside publications, too.
    for photo in photos:
        linked = {student.id for student in photo.students}
        photo.students.extend(student for student in students if student.id not in linked)


@router.get("/", response_model=List[schemas.ManagedPostResponse])
def list_school_posts(
    class_id: int | None = None,
    current_user: models.User = Depends(get_current_user),
    session: Session = Depends(db.get_db),
):
    query = posts_query(session, current_user)
    if class_id is not None:
        school_class = session.query(models.Class).filter(models.Class.id == class_id,
            models.Class.school_id == current_user.school_id).first()
        if not school_class or not can_access_class(current_user, class_id):
            raise HTTPException(status_code=404, detail="Turma não encontrada.")
        query = query.filter(models.Post.class_id == class_id)
    return [post_response(post, current_user) for post in query.order_by(models.Post.created_at.desc()).all()]


@router.get("/{post_id}", response_model=schemas.ManagedPostResponse)
def get_school_post(post_id: str, current_user: models.User = Depends(get_current_user), session: Session = Depends(db.get_db)):
    return post_response(owned_post(post_id, current_user, session), current_user)


@router.post("/", response_model=schemas.ManagedPostResponse, status_code=status.HTTP_201_CREATED)
def create_school_post(payload: schemas.PostCreate, current_user: models.User = Depends(get_current_user), session: Session = Depends(db.get_db)):
    content = validate_content(payload, current_user, session)
    post = models.Post(id=str(uuid.uuid4()), school_id=current_user.school_id,
        created_by_user_id=current_user.id, teacher_name=current_user.name, teacher_avatar_url="")
    apply_content(post, *content)
    session.add(post)
    session.commit()
    session.refresh(post)
    return post_response(post, current_user)


@router.put("/{post_id}", response_model=schemas.ManagedPostResponse)
def update_school_post(post_id: str, payload: schemas.PostCreate, current_user: models.User = Depends(get_current_user), session: Session = Depends(db.get_db)):
    post = owned_post(post_id, current_user, session, write=True)
    content = validate_content(payload, current_user, session, post.class_id)
    apply_content(post, *content)
    session.commit()
    session.refresh(post)
    return post_response(post, current_user)


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_school_post(post_id: str, current_user: models.User = Depends(get_current_user), session: Session = Depends(db.get_db)):
    post = owned_post(post_id, current_user, session, write=True)
    session.delete(post)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
