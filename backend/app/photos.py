import os
import shutil
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from . import db, models, schemas

router = APIRouter()
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")

@router.post("/upload", response_model=schemas.PhotoResponse)
def upload_photo(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    class_id: Optional[int] = Form(None),
    # Na prática isso viria do token JWT do usuário logado:
    uploaded_by_user_id: int = Form(1),
    session: Session = Depends(db.get_db)
):
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    new_photo = models.Photo(
        file_path=file.filename, # Salvamos apenas o nome do arquivo
        title=title,
        description=description,
        uploaded_by_user_id=uploaded_by_user_id,
        class_id=class_id
    )
    session.add(new_photo)
    session.commit()
    session.refresh(new_photo)
    return new_photo

@router.get("/file/{filename}")
def get_photo_file(filename: str):
    file_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)

@router.get("/class/{class_id}", response_model=List[schemas.PhotoResponse])
def get_photos_by_class(class_id: int, session: Session = Depends(db.get_db)):
    """
    Retorna todas as fotos vinculadas a uma turma específica.
    """
    photos = session.query(models.Photo).filter(models.Photo.class_id == class_id).all()
    return photos


@router.post("/{photo_id}/tags/{tag_id}", response_model=schemas.PhotoResponse)
def add_tag_to_photo(photo_id: int, tag_id: int, session: Session = Depends(db.get_db)):
    photo = session.query(models.Photo).filter(models.Photo.id == photo_id).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
        
    tag = session.query(models.Tag).filter(models.Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
        
    if tag not in photo.tags:
        photo.tags.append(tag)
        session.commit()
        session.refresh(photo)
        
    return photo

@router.delete("/{photo_id}/tags/{tag_id}", response_model=schemas.PhotoResponse)
def remove_tag_from_photo(photo_id: int, tag_id: int, session: Session = Depends(db.get_db)):
    photo = session.query(models.Photo).filter(models.Photo.id == photo_id).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
        
    tag = session.query(models.Tag).filter(models.Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
        
    if tag in photo.tags:
        photo.tags.remove(tag)
        session.commit()
        session.refresh(photo)
        
    return photo
