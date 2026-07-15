from fastapi import APIRouter, Depends
from typing import List
from .. import models, schemas, security

router = APIRouter()

@router.get("/", response_model=List[schemas.ChildResponse])
def get_children(current_parent: models.Parent = Depends(security.get_current_parent)):
    """
    Retorna todas as crianças vinculadas ao pai autenticado.
    """
    return current_parent.children
