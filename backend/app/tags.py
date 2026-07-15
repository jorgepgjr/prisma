from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from . import db, models, schemas

router = APIRouter()

@router.get("/", response_model=List[schemas.TagResponse])
def get_tags(session: Session = Depends(db.get_db)):
    return session.query(models.Tag).all()

@router.post("/", response_model=schemas.TagResponse)
def create_tag(tag: schemas.TagCreate, session: Session = Depends(db.get_db)):
    db_tag = session.query(models.Tag).filter(models.Tag.name == tag.name).first()
    if db_tag:
        raise HTTPException(status_code=400, detail="Tag already exists")
    
    new_tag = models.Tag(name=tag.name)
    session.add(new_tag)
    session.commit()
    session.refresh(new_tag)
    return new_tag
