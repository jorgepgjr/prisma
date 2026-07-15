from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
import json
from .. import db, models, schemas, security

router = APIRouter()

@router.get("/", response_model=List[schemas.ProjectResponse])
def get_portfolio(
    child: models.Child = Depends(security.verifyChildAccess),
    session: Session = Depends(db.get_db)
):
    """
    Retorna a grade de projetos/trabalhos da criança.
    """
    projects = child.projects
    
    response_projects = []
    for project in projects:
        # Tenta decodificar o array JSON (caso tenhamos salvo como string JSON)
        try:
            pedagogical_objectives = json.loads(project.pedagogical_objectives)
        except Exception:
            pedagogical_objectives = [project.pedagogical_objectives]

        proj_dict = {
            "id": project.id,
            "child_id": project.child_id,
            "title": project.title,
            "image_url": security.generatePresignedUrl(project.image_path),
            "completion_date": project.completion_date,
            "description": project.description,
            "pedagogical_objectives": pedagogical_objectives,
            "created_at": project.created_at
        }
        response_projects.append(proj_dict)
        
    return response_projects
