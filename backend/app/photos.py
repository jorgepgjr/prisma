import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from . import db, models, schemas, security
from .dependencies import get_current_user, require_roles

router = APIRouter()
UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif", "image/avif", "application/octet-stream"}
ALLOWED_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".avif"}


def can_access_class(user: models.User, class_id: int) -> bool:
    if user.role == models.RoleEnum.COORDENADOR:
        return True
    return user.role == models.RoleEnum.PROFESSOR and any(item.id == class_id for item in user.classes)


def require_class_access(user: models.User, class_id: int, session: Session) -> models.Class:
    school_class = session.query(models.Class).filter(
        models.Class.id == class_id, models.Class.school_id == user.school_id,
        models.Class.is_active.is_(True),
    ).first()
    if not school_class or not can_access_class(user, class_id):
        raise HTTPException(status_code=404, detail="Turma não encontrada.")
    return school_class


def serialize_photo(photo: models.Photo) -> schemas.PhotoResponse:
    detected_count = len(photo.detected_faces) if hasattr(photo, "detected_faces") and photo.detected_faces else 0
    return schemas.PhotoResponse(
        id=photo.id, file_path=photo.file_path,
        media_url=security.generatePresignedUrl(photo.file_path), title=photo.title,
        description=photo.description, uploaded_by_user_id=photo.uploaded_by_user_id,
        uploader_name=photo.uploader.name if photo.uploader else None,
        class_id=photo.class_id,
        class_name=photo.school_class.name if photo.school_class else None,
        status=photo.status.value,
        process_status=photo.process_status.value if hasattr(photo, "process_status") and photo.process_status else "PENDING",
        process_attempts=photo.process_attempts if hasattr(photo, "process_attempts") else 0,
        process_error=photo.process_error if hasattr(photo, "process_error") else None,
        detected_faces_count=detected_count,
        created_at=photo.created_at,
        student_ids=[student.id for student in photo.students],
        tags=photo.tags,
    )



@router.post("/upload", response_model=schemas.PhotoResponse, status_code=status.HTTP_201_CREATED)
def upload_photo(
    file: UploadFile = File(...), title: Optional[str] = Form(None),
    description: Optional[str] = Form(None), class_id: int = Form(...),
    current_user: models.User = Depends(get_current_user), session: Session = Depends(db.get_db),
):
    if current_user.role not in {models.RoleEnum.PROFESSOR, models.RoleEnum.COORDENADOR}:
        raise HTTPException(status_code=403, detail="Seu perfil não pode enviar fotos.")
    require_class_access(current_user, class_id, session)
    suffix = Path(file.filename or "foto.jpg").suffix.lower() or ".jpg"
    if file.content_type not in ALLOWED_IMAGE_TYPES or suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(status_code=415, detail="Envie uma imagem JPEG, PNG, WebP, AVIF ou HEIC.")
    relative_path = Path(str(current_user.school_id)) / f"{uuid.uuid4().hex}{suffix}"
    destination = UPLOAD_DIR / relative_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with destination.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as error:
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="Não foi possível armazenar a foto.") from error
    new_photo = models.Photo(
        school_id=current_user.school_id, file_path=relative_path.as_posix(),
        title=title or "Foto da rotina escolar", description=description,
        uploaded_by_user_id=current_user.id, class_id=class_id,
    )
    try:
        session.add(new_photo)
        session.commit()
        session.refresh(new_photo)
    except Exception:
        session.rollback()
        destination.unlink(missing_ok=True)
        raise
    return serialize_photo(new_photo)


@router.get("/", response_model=List[schemas.PhotoResponse])
def list_school_photos(
    class_id: Optional[int] = None,
    current_user: models.User = Depends(require_roles([models.RoleEnum.COORDENADOR])),
    session: Session = Depends(db.get_db),
):
    query = session.query(models.Photo).filter(models.Photo.school_id == current_user.school_id)
    if class_id is not None:
        school_class = session.query(models.Class).filter(
            models.Class.id == class_id, models.Class.school_id == current_user.school_id
        ).first()
        if not school_class:
            raise HTTPException(status_code=404, detail="Turma não encontrada.")
        query = query.filter(models.Photo.class_id == class_id)
    photos = query.order_by(models.Photo.created_at.desc()).all()
    return [serialize_photo(photo) for photo in photos]


@router.get("/class/{class_id}", response_model=List[schemas.PhotoResponse])
def get_photos_by_class(
    class_id: int, student_id: Optional[int] = None,
    date_from: Optional[datetime] = None, date_to: Optional[datetime] = None,
    tag_ids: Optional[List[int]] = Query(None),
    current_user: models.User = Depends(get_current_user), session: Session = Depends(db.get_db),
):
    require_class_access(current_user, class_id, session)
    query = session.query(models.Photo).filter(
        models.Photo.school_id == current_user.school_id, models.Photo.class_id == class_id
    )
    if student_id is not None:
        query = query.filter(models.Photo.students.any(models.Student.id == student_id))
    if date_from is not None:
        query = query.filter(models.Photo.created_at >= date_from)
    if date_to is not None:
        query = query.filter(models.Photo.created_at <= date_to)
    if tag_ids:
        for tag_id in set(tag_ids):
            query = query.filter(models.Photo.tags.any(models.Tag.id == tag_id))
    return [serialize_photo(photo) for photo in query.order_by(models.Photo.created_at.desc()).all()]


@router.get("/marketing", response_model=List[schemas.PhotoResponse])
def marketing_photos(
    current_user: models.User = Depends(require_roles([models.RoleEnum.MARKETING])),
    session: Session = Depends(db.get_db),
):
    photos = session.query(models.Photo).filter(
        models.Photo.school_id == current_user.school_id,
        models.Photo.status == models.PhotoStatusEnum.APPROVED_FOR_MARKETING,
    ).order_by(models.Photo.created_at.desc()).all()
    return [serialize_photo(photo) for photo in photos]


@router.put("/{photo_id}/status", response_model=schemas.PhotoResponse)
def update_photo_status(
    photo_id: int, payload: schemas.PhotoStatusUpdate,
    current_user: models.User = Depends(require_roles([models.RoleEnum.COORDENADOR])),
    session: Session = Depends(db.get_db),
):
    photo = session.query(models.Photo).filter(
        models.Photo.id == photo_id, models.Photo.school_id == current_user.school_id
    ).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Foto não encontrada.")
    photo.status = payload.status
    session.commit()
    session.refresh(photo)
    return serialize_photo(photo)


def get_owned_photo(photo_id: int, user: models.User, session: Session) -> models.Photo:
    photo = session.query(models.Photo).filter(
        models.Photo.id == photo_id, models.Photo.school_id == user.school_id
    ).first()
    if not photo or photo.class_id is None or not can_access_class(user, photo.class_id):
        raise HTTPException(status_code=404, detail="Foto não encontrada.")
    return photo


@router.post("/{photo_id}/tags/{tag_id}", response_model=schemas.PhotoResponse)
def add_tag_to_photo(
    photo_id: int, tag_id: int, current_user: models.User = Depends(get_current_user),
    session: Session = Depends(db.get_db),
):
    photo = get_owned_photo(photo_id, current_user, session)
    tag = session.query(models.Tag).filter(models.Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag não encontrada.")
    if tag not in photo.tags:
        photo.tags.append(tag)
        session.commit()
        session.refresh(photo)
    return serialize_photo(photo)


@router.delete("/{photo_id}/tags/{tag_id}", response_model=schemas.PhotoResponse)
def remove_tag_from_photo(
    photo_id: int, tag_id: int, current_user: models.User = Depends(get_current_user),
    session: Session = Depends(db.get_db),
):
    photo = get_owned_photo(photo_id, current_user, session)
    tag = session.query(models.Tag).filter(models.Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag não encontrada.")
    if tag in photo.tags:
        photo.tags.remove(tag)
        session.commit()
        session.refresh(photo)
    return serialize_photo(photo)
