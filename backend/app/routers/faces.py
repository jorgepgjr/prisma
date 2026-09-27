import os
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from .. import db, models, schemas
from ..photos import serialize_photo

router = APIRouter()
FACES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads", "faces")


def build_cluster_response(cluster: models.FaceCluster) -> schemas.FaceClusterResponse:
    faces = cluster.faces or []
    distinct_photo_ids = set(f.photo_id for f in faces if f.photo_id)
    
    # Collect sample crop URLs (up to 4)
    sample_crops = []
    for f in faces:
        if f.face_crop_path:
            # Provide API crop URL
            sample_crops.append(f"/api/faces/crop/{f.id}")
        if len(sample_crops) >= 4:
            break

    student_name = cluster.student.name if cluster.student else None
    student_class_name = cluster.student.school_class.name if cluster.student and cluster.student.school_class else None

    return schemas.FaceClusterResponse(
        id=cluster.id,
        student_id=cluster.student_id,
        student_name=student_name,
        student_class_name=student_class_name,
        name=cluster.name,
        face_count=len(faces),
        photo_count=len(distinct_photo_ids),
        sample_face_crops=sample_crops,
        created_at=cluster.created_at,
    )


@router.get("/clusters", response_model=List[schemas.FaceClusterResponse])
def list_clusters(
    status: Optional[str] = Query("all", regex="^(unassigned|assigned|all)$"),
    class_id: Optional[int] = Query(None),
    session: Session = Depends(db.get_db),
):
    """
    Lista grupos de rostos (clusters) com contagem de faces, fotos e thumbnails de amostra.
    Suporta filtros por status (unassigned, assigned, all) e por class_id.
    """
    query = session.query(models.FaceCluster)

    if status == "unassigned":
        query = query.filter(models.FaceCluster.student_id == None)
    elif status == "assigned":
        query = query.filter(models.FaceCluster.student_id != None)

    if class_id is not None:
        query = query.join(models.DetectedFace, models.FaceCluster.id == models.DetectedFace.cluster_id)\
                     .join(models.Photo, models.DetectedFace.photo_id == models.Photo.id)\
                     .filter(models.Photo.class_id == class_id)\
                     .distinct()

    clusters = query.order_by(models.FaceCluster.created_at.desc()).all()
    return [build_cluster_response(c) for c in clusters]


@router.get("/clusters/{cluster_id}", response_model=schemas.FaceClusterResponse)
def get_cluster(cluster_id: str, session: Session = Depends(db.get_db)):
    cluster = session.query(models.FaceCluster).filter(models.FaceCluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster não encontrado.")
    return build_cluster_response(cluster)


@router.post("/clusters/{cluster_id}/assign", response_model=schemas.FaceClusterResponse)
def assign_cluster_to_student(
    cluster_id: str,
    payload: schemas.FaceClusterAssignRequest,
    session: Session = Depends(db.get_db),
):
    """
    Associa um cluster a um Aluno e propaga a identificação para as fotos do cluster.
    """
    cluster = session.query(models.FaceCluster).filter(models.FaceCluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster não encontrado.")

    student = session.query(models.Student).filter(models.Student.id == payload.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Aluno não encontrado.")

    cluster.student_id = student.id

    # Vincula o aluno às fotos que contêm faces deste cluster
    for face in cluster.faces:
        if face.photo and student not in face.photo.students:
            face.photo.students.append(student)

    session.commit()
    session.refresh(cluster)
    return build_cluster_response(cluster)


@router.delete("/clusters/{cluster_id}/assign", response_model=schemas.FaceClusterResponse)
def unassign_cluster(cluster_id: str, session: Session = Depends(db.get_db)):
    """
    Desvincula o cluster do aluno associado.
    """
    cluster = session.query(models.FaceCluster).filter(models.FaceCluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster não encontrado.")

    cluster.student_id = None
    session.commit()
    session.refresh(cluster)
    return build_cluster_response(cluster)


@router.get("/clusters/{cluster_id}/photos", response_model=List[schemas.PhotoResponse])
def get_cluster_photos(cluster_id: str, session: Session = Depends(db.get_db)):
    """
    Retorna todas as fotos que contêm faces pertencentes a este cluster.
    """
    cluster = session.query(models.FaceCluster).filter(models.FaceCluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster não encontrado.")

    photo_ids = set(f.photo_id for f in cluster.faces if f.photo_id)
    if not photo_ids:
        return []

    photos = session.query(models.Photo).filter(models.Photo.id.in_(photo_ids)).all()
    return [serialize_photo(p) for p in photos]


@router.get("/crop/{face_id}")
def get_face_crop(face_id: str, session: Session = Depends(db.get_db)):
    """
    Serve o arquivo de imagem do thumbnail do rosto recortado.
    """
    face = session.query(models.DetectedFace).filter(models.DetectedFace.id == face_id).first()
    if not face or not face.face_crop_path:
        raise HTTPException(status_code=404, detail="Rosto ou thumbnail não encontrado.")

    crop_file_path = os.path.join(FACES_DIR, os.path.basename(face.face_crop_path))
    if not os.path.exists(crop_file_path):
        # Fallback to direct path check
        if os.path.exists(face.face_crop_path):
            crop_file_path = face.face_crop_path
        else:
            raise HTTPException(status_code=404, detail="Arquivo de thumbnail não encontrado.")

    return FileResponse(crop_file_path)
