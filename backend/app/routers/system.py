import os
import shutil
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from .. import db, models, schemas, security
from ..face_service import process_image_batch
from ..dependencies import require_roles
from ..test_ingestion import extract_test_archives, find_test_images
from .faces import crop_media_url, own_cluster

coordinator_access = require_roles([models.RoleEnum.COORDENADOR])
router = APIRouter(dependencies=[Depends(coordinator_access)])

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
TEST_IMAGES_DIR = os.path.join(BASE_DIR, "test_images")
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(TEST_IMAGES_DIR, exist_ok=True)

@router.get("/processing-status", response_model=schemas.SystemProcessingStatusResponse)
def get_processing_status(current_user: models.User = Depends(coordinator_access), session: Session = Depends(db.get_db)):
    """
    Retorna o status quantitativo da fila de processamento de fotos e reconhecimento facial.
    """
    query = session.query(models.Photo).filter(models.Photo.school_id == current_user.school_id)
    pending = query.filter(models.Photo.process_status == models.ProcessStatusEnum.PENDING).count()
    processing = query.filter(models.Photo.process_status == models.ProcessStatusEnum.PROCESSING).count()
    completed = query.filter(models.Photo.process_status == models.ProcessStatusEnum.COMPLETED).count()
    failed = query.filter(models.Photo.process_status == models.ProcessStatusEnum.FAILED).count()
    total = query.count()

    return schemas.SystemProcessingStatusResponse(
        pending=pending,
        processing=processing,
        completed=completed,
        failed=failed,
        total=total,
    )


@router.get("/processing-photos", response_model=List[schemas.ProcessingPhotoDetail])
def get_processing_photos(
    status_filter: Optional[str] = Query("ALL", pattern="^(ALL|PENDING|PROCESSING|COMPLETED|FAILED)$"),
    cluster_id: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: models.User = Depends(coordinator_access),
    session: Session = Depends(db.get_db),
):
    """
    Retorna lista detalhada de fotos e o status individual de cada uma (incluindo faces recortadas e erros).
    Suporta filtros por status e por cluster_id (Pessoa).
    """
    query = session.query(models.Photo).filter(models.Photo.school_id == current_user.school_id)
    if status_filter != "ALL":
        query = query.filter(models.Photo.process_status == models.ProcessStatusEnum(status_filter))

    if cluster_id:
        own_cluster(cluster_id, current_user.school_id, session)
        query = query.join(models.DetectedFace, models.Photo.id == models.DetectedFace.photo_id)\
                     .filter(models.DetectedFace.cluster_id == cluster_id)\
                     .distinct()

    photos = query.order_by(models.Photo.created_at.desc()).offset(offset).limit(limit).all()

    results = []
    for photo in photos:
        face_details = []
        for face in photo.detected_faces:
            crop_url = crop_media_url(face)
            cluster = face.cluster if face.cluster and face.cluster.school_id == current_user.school_id else None
            student = cluster.student if cluster and cluster.student and cluster.student.school_id == current_user.school_id else None
            cluster_name = cluster.name if cluster else None
            student_id = student.id if student else None
            student_name = student.name if student else None

            face_details.append(schemas.DetectedFaceDetail(
                id=face.id,
                bounding_box=face.bounding_box or [],
                face_crop_url=crop_url,
                detection_score=face.detection_score,
                cluster_id=cluster.id if cluster else None,
                cluster_name=cluster_name,
                student_id=student_id,
                student_name=student_name,
            ))

        results.append(schemas.ProcessingPhotoDetail(
            id=photo.id,
            file_path=photo.file_path,
            image_url=security.generatePresignedUrl(photo.file_path),
            class_id=photo.class_id,
            class_name=photo.school_class.name if photo.school_class else None,
            process_status=photo.process_status.value if photo.process_status else "PENDING",
            process_attempts=photo.process_attempts or 0,
            process_error=photo.process_error,
            created_at=photo.created_at,
            detected_faces=face_details,
        ))

    return results


@router.post("/process-now", response_model=schemas.ProcessNowResponse)
def process_queue_now(
    batch_size: int = Query(50, ge=1, le=200),
    current_user: models.User = Depends(coordinator_access),
    session: Session = Depends(db.get_db),
):
    """
    Dispara imediatamente uma rodada de processamento de reconhecimento facial no backend.
    """
    processed = process_image_batch(session, batch_size=batch_size, school_id=current_user.school_id)
    return schemas.ProcessNowResponse(
        processed_count=processed,
        message=f"{processed} foto(s) processada(s) com sucesso." if processed > 0 else "Nenhuma foto pendente na fila."
    )


@router.post("/ingest-test-folder", response_model=schemas.IngestTestFolderResponse)
def ingest_test_folder(
    class_id: Optional[int] = Query(None),
    current_user: models.User = Depends(coordinator_access),
    session: Session = Depends(db.get_db),
):
    """
    Lê a pasta backend/test_images/, copia as imagens para uploads/ e cadastra na tabela photos como PENDING.
    """
    if not os.path.exists(TEST_IMAGES_DIR):
        os.makedirs(TEST_IMAGES_DIR, exist_ok=True)
        return schemas.IngestTestFolderResponse(
            imported_count=0,
            skipped_count=0,
            total_found=0,
            message="A pasta test_images estava vazia e foi criada. Coloque arquivos de imagem lá para testar."
        )

    archive_warnings = extract_test_archives(TEST_IMAGES_DIR)

    # Identifica turma padrão se não fornecida
    target_class_id = class_id
    if target_class_id is not None:
        target_class = session.query(models.Class).filter(
            models.Class.id == target_class_id,
            models.Class.school_id == current_user.school_id,
        ).first()
        if not target_class:
            raise HTTPException(status_code=404, detail="Turma não encontrada.")
    else:
        first_class = session.query(models.Class).filter(
            models.Class.school_id == current_user.school_id,
        ).first()
        target_class_id = first_class.id if first_class else None

    image_paths = find_test_images(TEST_IMAGES_DIR)

    if not image_paths:
        warning_message = f" Avisos: {'; '.join(archive_warnings)}" if archive_warnings else ""
        return schemas.IngestTestFolderResponse(
            imported_count=0,
            skipped_count=0,
            total_found=0,
            message=f"Nenhuma imagem encontrada em test_images/ (formatos aceitos: jpg, png, webp, heic, avif, bmp).{warning_message}"
        )

    imported = 0
    skipped = 0

    for source_path in image_paths:
        filename = os.path.basename(source_path)

        # Nome de destino único para evitar colisões
        base_name, ext = os.path.splitext(filename)
        dest_filename = f"test_{uuid.uuid4().hex}_{filename}"
        relative_path = os.path.join(str(current_user.school_id), dest_filename)
        dest_path = os.path.join(UPLOADS_DIR, relative_path)
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)

        # Copia arquivo para uploads/
        shutil.copy2(source_path, dest_path)

        # Registra Photo com status PENDING
        new_photo = models.Photo(
            school_id=current_user.school_id,
            file_path=relative_path.replace(os.sep, "/"),
            title=f"Teste: {base_name}",
            description="Importado da pasta de testes para reconhecimento facial",
            uploaded_by_user_id=current_user.id,
            class_id=target_class_id,
            status=models.PhotoStatusEnum.PENDING_REVIEW,
            process_status=models.ProcessStatusEnum.PENDING,
            process_attempts=0,
            process_error=None,
        )
        session.add(new_photo)
        imported += 1

    session.commit()

    return schemas.IngestTestFolderResponse(
        imported_count=imported,
        skipped_count=skipped,
        total_found=len(image_paths),
        message=(
            f"{imported} foto(s) importada(s) da pasta test_images com sucesso para a fila (status PENDING)."
            + (f" Avisos: {'; '.join(archive_warnings)}" if archive_warnings else "")
        )
    )


@router.post("/reprocess-failed")
def reprocess_failed_photos(current_user: models.User = Depends(coordinator_access), session: Session = Depends(db.get_db)):
    """
    Reinicia o status das fotos marcadas como FAILED de volta para PENDING.
    """
    failed_photos = session.query(models.Photo).filter(
        models.Photo.school_id == current_user.school_id, models.Photo.process_status == models.ProcessStatusEnum.FAILED,
    ).all()
    count = len(failed_photos)
    for photo in failed_photos:
        photo.process_status = models.ProcessStatusEnum.PENDING
        photo.process_error = None
    session.commit()
    return {"message": f"{count} fotos re-enfileiradas para processamento."}


@router.post("/reprocess-all")
def reprocess_all_photos(current_user: models.User = Depends(coordinator_access), session: Session = Depends(db.get_db)):
    """
    Reinicia o status de todas as fotos para PENDING para re-processamento geral.
    """
    photos = session.query(models.Photo).filter(models.Photo.school_id == current_user.school_id).all()
    count = len(photos)
    for photo in photos:
        photo.process_status = models.ProcessStatusEnum.PENDING
        photo.process_attempts = 0
        photo.process_error = None
    session.commit()
    return {"message": f"{count} fotos re-enfileiradas para processamento completo."}


@router.post("/recluster-all")
def recluster_faces(
    threshold: float = Query(0.48, ge=0.2, le=0.8),
    current_user: models.User = Depends(coordinator_access),
    session: Session = Depends(db.get_db),
):
    """
    Reagrupa todas as faces do banco de dados com DBSCAN utilizando a distância de cosseno calibrada.
    """
    from ..face_service import recluster_all_faces
    result = recluster_all_faces(session, distance_threshold=threshold, school_id=current_user.school_id)
    return {
        "message": f"{result['total_faces']} faces reagrupadas em {result['clusters_created']} pessoa(s)/cluster(s) com sucesso!",
        "result": result,
    }
