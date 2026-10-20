from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import List
from . import db, models, schemas
from .dependencies import get_current_user, require_roles

router = APIRouter()

@router.get("/", response_model=List[schemas.TagResponse])
def get_tags(current_user: models.User = Depends(get_current_user), session: Session = Depends(db.get_db)):
    return session.query(models.Tag).filter(models.Tag.school_id == current_user.school_id).order_by(models.Tag.name).all()

@router.post("/", response_model=schemas.TagResponse)
def create_tag(
    tag: schemas.TagCreate,
    current_user: models.User = Depends(require_roles([models.RoleEnum.PROFESSOR, models.RoleEnum.COORDENADOR])),
    session: Session = Depends(db.get_db),
):
    name = " ".join(tag.name.split())
    if not name or len(name) > 60:
        raise HTTPException(status_code=422, detail="Informe uma tag de até 60 caracteres.")
    db_tag = session.query(models.Tag).filter(models.Tag.school_id == current_user.school_id, func.lower(models.Tag.name) == name.casefold()).first()
    if db_tag:
        return db_tag
    
    new_tag = models.Tag(name=name, school_id=current_user.school_id)
    session.add(new_tag)
    session.commit()
    session.refresh(new_tag)
    return new_tag
