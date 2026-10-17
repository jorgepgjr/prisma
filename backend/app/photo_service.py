import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from .models import Photo, PhotoStatusEnum

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".avif", ".heic", ".heif"}


def save_photo(file: UploadFile, session: Session, user_id: int, school_id: int, class_id: int | None = None) -> Photo:
    suffix = Path(file.filename or "foto.jpg").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Tipo de arquivo não permitido.")
    relative_path = Path(str(school_id)) / f"{uuid.uuid4().hex}{suffix}"
    destination = UPLOAD_DIR / relative_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with destination.open("wb") as buffer:
            while content := file.file.read(1024 * 1024):
                buffer.write(content)
        photo = Photo(
            school_id=school_id, file_path=relative_path.as_posix(), title=file.filename,
            uploaded_by_user_id=user_id, class_id=class_id, status=PhotoStatusEnum.PENDING_REVIEW,
        )
        session.add(photo)
        session.commit()
        session.refresh(photo)
        return photo
    except Exception as error:
        session.rollback()
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erro ao salvar a foto.") from error


def get_photo_path(file_id: str) -> str:
    root = UPLOAD_DIR.resolve()
    path = (root / file_id).resolve()
    if root not in path.parents or not path.is_file():
        raise HTTPException(status_code=404, detail="Arquivo de foto não encontrado.")
    return str(path)
