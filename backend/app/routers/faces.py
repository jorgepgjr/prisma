from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from .. import db, models, schemas, security
from ..config import settings
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


@router.get("/detected", response_model=List[schemas.DetectedFaceDetail])
def list_detected_faces(
    cluster_id: Optional[str] = Query(None),
    limit: int = Query(300, ge=1, le=1000),
    current_user: models.User = Depends(coordinator_access),
    session: Session = Depends(db.get_db),
):
    """
    Retorna todos os rostos detectados na escola do coordenador,
    com URL do recorte facial e identificação da pessoa/aluno.
    """
    query = session.query(models.DetectedFace).join(models.Photo).filter(
        models.Photo.school_id == current_user.school_id
    )
    if cluster_id:
        query = query.filter(models.DetectedFace.cluster_id == cluster_id)

    faces = query.order_by(models.DetectedFace.created_at.desc()).limit(limit).all()

    results = []
    for face in faces:
        cluster = face.cluster
        student = (
            cluster.student
            if cluster and cluster.student and cluster.student.school_id == current_user.school_id
            else None
        )
        results.append(
            schemas.DetectedFaceDetail(
                id=face.id,
                bounding_box=face.bounding_box or [],
                face_crop_url=crop_media_url(face),
                detection_score=face.detection_score,
                cluster_id=cluster.id if cluster else None,
                cluster_name=cluster.name if cluster else None,
                student_id=student.id if student else None,
                student_name=student.name if student else None,
            )
        )
    return results


@router.get("/match-suggestions", response_model=List[schemas.FaceMatchSuggestion])
def get_match_suggestions(
    max_distance: float = Query(default=settings.MATCH_SUGGESTION_MAX_DISTANCE, ge=0.1, le=1.0),
    min_similarity: float = Query(default=settings.MATCH_SUGGESTION_MIN_SIMILARITY, ge=0.0, le=100.0),
    limit: int = Query(default=settings.MATCH_SUGGESTION_DEFAULT_LIMIT, ge=1, le=50),
    current_user: models.User = Depends(coordinator_access),
    session: Session = Depends(db.get_db),
):
    """
    Retorna pares de pessoas/clusters não unidos cujos rostos possuem alta similaridade biométrica,
    indicando a probabilidade de serem a mesma pessoa para confirmação do usuário.
    """
    import numpy as np
    from sklearn.metrics.pairwise import cosine_distances

    clusters_db = school_clusters(session, current_user.school_id).all()
    cluster_faces = {}
    for c in clusters_db:
        valid_faces = [
            f for f in c.faces
            if f.embedding is not None and f.photo and f.photo.school_id == current_user.school_id
        ]
        if valid_faces:
            cluster_faces[c] = valid_faces

    cluster_list = list(cluster_faces.keys())
    if len(cluster_list) < 2:
        return []

    suggestions = []
    for i in range(len(cluster_list)):
        c1 = cluster_list[i]
        f1_list = cluster_faces[c1]
        m1 = np.array([f.embedding for f in f1_list], dtype=np.float32)
        norm1 = np.linalg.norm(m1, axis=1, keepdims=True)
        norm1[norm1 == 0] = 1.0
        m1 = m1 / norm1

        c1_photo_ids = {f.photo_id for f in f1_list if f.photo_id is not None}

        for j in range(i + 1, len(cluster_list)):
            c2 = cluster_list[j]
            f2_list = cluster_faces[c2]
            c2_photo_ids = {f.photo_id for f in f2_list if f.photo_id is not None}

            # REGRA: Uma pessoa não pode aparecer duas vezes na mesma imagem.
            # Se c1 e c2 compartilham alguma foto, são rostos distintos na mesma foto.
            if c1_photo_ids.intersection(c2_photo_ids):
                continue

            m2 = np.array([f.embedding for f in f2_list], dtype=np.float32)
            norm2 = np.linalg.norm(m2, axis=1, keepdims=True)
            norm2[norm2 == 0] = 1.0
            m2 = m2 / norm2

            dists = cosine_distances(m1, m2)
            min_idx = np.unravel_index(np.argmin(dists), dists.shape)
            best_dist = float(dists[min_idx])

            if best_dist <= max_distance:
                sim_pct = round(max(0.0, min(100.0, (1.0 - best_dist) * 100)), 1)
                if sim_pct >= min_similarity:
                    best_f1 = f1_list[min_idx[0]]
                    best_f2 = f2_list[min_idx[1]]

                    s1 = c1.student if c1.student and c1.student.school_id == current_user.school_id else None
                    s2 = c2.student if c2.student and c2.student.school_id == current_user.school_id else None

                    suggestions.append(schemas.FaceMatchSuggestion(
                        id=f"{c1.id}_{c2.id}",
                        source_cluster_id=c1.id,
                        source_cluster_name=c1.name,
                        source_student_id=s1.id if s1 else None,
                        source_student_name=s1.name if s1 else None,
                        source_face_id=best_f1.id,
                        source_face_crop_url=crop_media_url(best_f1),
                        source_photo_id=best_f1.photo_id,
                        source_photo_url=security.generatePresignedUrl(best_f1.photo.file_path) if best_f1.photo and best_f1.photo.file_path else None,
                        source_bounding_box=best_f1.bounding_box if best_f1 and best_f1.bounding_box else None,

                        target_cluster_id=c2.id,
                        target_cluster_name=c2.name,
                        target_student_id=s2.id if s2 else None,
                        target_student_name=s2.name if s2 else None,
                        target_face_id=best_f2.id,
                        target_face_crop_url=crop_media_url(best_f2),
                        target_photo_id=best_f2.photo_id,
                        target_photo_url=security.generatePresignedUrl(best_f2.photo.file_path) if best_f2.photo and best_f2.photo.file_path else None,
                        target_bounding_box=best_f2.bounding_box if best_f2 and best_f2.bounding_box else None,

                        distance=round(best_dist, 4),
                        similarity_percent=sim_pct,
                    ))

    suggestions.sort(key=lambda x: x.distance)
    return suggestions[:limit]


@router.post("/clusters/merge", response_model=schemas.FaceClusterResponse)
def merge_clusters(
    payload: schemas.FaceClusterMergeRequest,
    current_user: models.User = Depends(coordinator_access),
    session: Session = Depends(db.get_db),
):
    """
    Funde dois clusters de pessoas em um único grupo e sincroniza os vínculos com o aluno nas fotos.
    """
    from ..face_service import sync_cluster_student_links

    source_cluster = own_cluster(payload.source_cluster_id, current_user.school_id, session)
    target_cluster = own_cluster(payload.target_cluster_id, current_user.school_id, session)

    if source_cluster.id == target_cluster.id:
        return build_cluster_response(target_cluster)

    # REGRA: Uma pessoa não pode ter dois rostos na mesma imagem!
    source_photos = {f.photo_id for f in source_cluster.faces if f.photo_id is not None}
    target_photos = {f.photo_id for f in target_cluster.faces if f.photo_id is not None}
    common_photos = source_photos.intersection(target_photos)
    if common_photos:
        raise HTTPException(
            status_code=400,
            detail=f"Não é permitido associar estes grupos: ambos contêm rostos na mesma imagem (Foto #{next(iter(common_photos))}). Uma pessoa não pode aparecer duas vezes na mesma foto.",
        )

    # Se target não tiver aluno mas source tiver, herda o aluno
    if target_cluster.student_id is None and source_cluster.student_id is not None:
        target_cluster.student_id = source_cluster.student_id

    # Transfere todas as faces de source para target
    for face in list(source_cluster.faces):
        face.cluster_id = target_cluster.id

    session.flush()
    session.delete(source_cluster)
    session.commit()

    sync_cluster_student_links(session, school_id=current_user.school_id)
    session.refresh(target_cluster)
    return build_cluster_response(target_cluster)
