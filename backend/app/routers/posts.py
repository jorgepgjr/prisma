from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from .. import db, models, schemas, security

router = APIRouter()

@router.get("/", response_model=List[schemas.PostResponse])
def get_posts(
    child: models.Child = Depends(security.verifyChildAccess),
    session: Session = Depends(db.get_db)
):
    """
    Retorna o feed de fotos onde a criança está marcada.
    Valida o acesso usando `verifyChildAccess`.
    """
    posts = sorted((post for post in child.posts if post.school_id == child.school_id),
                   key=lambda item: item.created_at, reverse=True)
    
    # Prepara a resposta injetando a URL assinada (Pre-signed URL simulada)
    response_posts = []
    for post in posts:
        paths = [photo.file_path for photo in post.photos if photo.school_id == child.school_id]
        if not paths:
            if post.photos:
                continue
            paths = [post.image_path]
        post_dict = {
            "id": post.id,
            "classroom_name": post.classroom_name,
            "teacher_name": post.teacher_name,
            "teacher_avatar_url": post.teacher_avatar_url,
            "image_url": security.generatePresignedUrl(paths[0]),
            "image_urls": [security.generatePresignedUrl(path) for path in paths],
            "caption": post.caption,
            "created_at": post.created_at
        }
        response_posts.append(post_dict)
        
    return response_posts
