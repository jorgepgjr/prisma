from fastapi import APIRouter, Depends
from typing import List
from .. import models, schemas, security

router = APIRouter()

@router.get("/", response_model=List[schemas.ChildResponse])
def get_children(current_parent: models.Parent = Depends(security.get_current_parent)):
    """
    Retorna todas as crianças vinculadas ao pai autenticado.
    """
    response_children = []
    for child in current_parent.children:
        child_dict = {
            "id": child.id,
            "name": child.name,
            "avatar_url": security.generatePresignedUrl(child.avatar_path),
            "classroom": child.classroom,
            "created_at": child.created_at
        }
        response_children.append(child_dict)
        
    return response_children
