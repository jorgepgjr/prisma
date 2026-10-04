from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from .. import db, models, schemas, security
from ..dependencies import require_roles
from ..photos import serialize_photo

coordinator_access = require_roles([models.RoleEnum.COORDENADOR])
router = APIRouter(dependencies=[Depends(coordinator_access)])
UPLOADS_DIR = Path(__file__).resolve().parents[2] / "uploads"


def school_clusters(session, school_id):
    return session.query(models.FaceCluster).filter(
        models.FaceCluster.school_id == school_id,
        ~models.FaceCluster.faces.any(models.DetectedFace.photo.has(models.Photo.school_id != school_id)),
    )


def own_cluster(cluster_id, school_id, session):
    cluster = school_clusters(session, school_id).filter(models.FaceCluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Grupo não encontrado.")
    return cluster


def crop_relative_path(face):
    if not face.face_crop_path:
        return None
    stored = Path(face.face_crop_path)
    if stored.is_absolute():
        destination = stored.resolve()
    elif len(stored.parts) > 1:
        destination = (UPLOADS_DIR / stored).resolve()
    else:
        destination = (UPLOADS_DIR / "faces" / stored).resolve()
    try:
        return destination.relative_to(UPLOADS_DIR.resolve()).as_posix()
    except ValueError:
        return None


def crop_media_url(face):
    path = crop_relative_path(face)
    return security.generatePresignedUrl(path) if path else None


def build_cluster_response(cluster):
    faces = [face for face in cluster.faces if face.photo and face.photo.school_id == cluster.school_id]
    student = cluster.student if cluster.student and cluster.student.school_id == cluster.school_id else None
    return schemas.FaceClusterResponse(
        id=cluster.id, student_id=student.id if student else None,
        student_name=student.name if student else None,
        student_class_name=student.school_class.name if student and student.school_class else None,
        name=cluster.name, face_count=len(faces),
        photo_count=len({face.photo_id for face in faces}),
        sample_face_crops=[url for face in faces if (url := crop_media_url(face))][:4],
        created_at=cluster.created_at,
    )


@router.get("/clusters", response_model=List[schemas.FaceClusterResponse])
def list_clusters(
    status: Optional[str] = Query("all", pattern="^(unassigned|assigned|all)$"),
    class_id: Optional[int] = Query(None),
    current_user: models.User = Depends(coordinator_access),
    session: Session = Depends(db.get_db),
):
    query = school_clusters(session, current_user.school_id)
    if status == "unassigned":
        query = query.filter(models.FaceCluster.student_id.is_(None))
    elif status == "assigned":
        query = query.filter(models.FaceCluster.student_id.isnot(None))
    if class_id is not None:
        school_class = session.query(models.Class).filter(
            models.Class.id == class_id, models.Class.school_id == current_user.school_id,
        ).first()
        if not school_class:
            raise HTTPException(status_code=404, detail="Turma não encontrada.")
        query = query.filter(models.FaceCluster.faces.any(models.DetectedFace.photo.has(models.Photo.class_id == class_id)))
    return [build_cluster_response(cluster) for cluster in query.order_by(models.FaceCluster.created_at.desc()).all()]


@router.get("/clusters/{cluster_id}", response_model=schemas.FaceClusterResponse)
def get_cluster(cluster_id: str, current_user: models.User = Depends(coordinator_access), session: Session = Depends(db.get_db)):
    return build_cluster_response(own_cluster(cluster_id, current_user.school_id, session))


@router.post("/clusters/{cluster_id}/assign", response_model=schemas.FaceClusterResponse)
def assign_cluster_to_student(
    cluster_id: str, payload: schemas.FaceClusterAssignRequest,
    current_user: models.User = Depends(coordinator_access), session: Session = Depends(db.get_db),
):
    cluster = own_cluster(cluster_id, current_user.school_id, session)
    student = session.query(models.Student).filter(
        models.Student.id == payload.student_id, models.Student.school_id == current_user.school_id,
        models.Student.status == models.StudentStatusEnum.ATIVO,
    ).first()
    if not student:
        raise HTTPException(status_code=404, detail="Aluno não encontrado.")
    cluster.student_id = student.id
    for face in cluster.faces:
        if face.photo and face.photo.school_id == current_user.school_id and student not in face.photo.students:
            face.photo.students.append(student)
    session.commit()
    session.refresh(cluster)
    return build_cluster_response(cluster)


@router.delete("/clusters/{cluster_id}/assign", response_model=schemas.FaceClusterResponse)
def unassign_cluster(cluster_id: str, current_user: models.User = Depends(coordinator_access), session: Session = Depends(db.get_db)):
    cluster = own_cluster(cluster_id, current_user.school_id, session)
    cluster.student_id = None
    session.commit()
    session.refresh(cluster)
    return build_cluster_response(cluster)


@router.get("/clusters/{cluster_id}/photos", response_model=List[schemas.PhotoResponse])
def get_cluster_photos(cluster_id: str, current_user: models.User = Depends(coordinator_access), session: Session = Depends(db.get_db)):
    cluster = own_cluster(cluster_id, current_user.school_id, session)
    photo_ids = {face.photo_id for face in cluster.faces}
    photos = session.query(models.Photo).filter(
        models.Photo.id.in_(photo_ids), models.Photo.school_id == current_user.school_id,
    ).all()
    return [serialize_photo(photo) for photo in photos]


@router.get("/crop/{face_id}")
def get_face_crop(face_id: str, current_user: models.User = Depends(coordinator_access), session: Session = Depends(db.get_db)):
    face = session.query(models.DetectedFace).join(models.Photo).filter(
        models.DetectedFace.id == face_id, models.Photo.school_id == current_user.school_id,
    ).first()
    relative_path = crop_relative_path(face) if face else None
    destination = UPLOADS_DIR / relative_path if relative_path else None
    if not destination or not destination.is_file():
        raise HTTPException(status_code=404, detail="Rosto ou imagem não encontrado.")
    return FileResponse(destination)
