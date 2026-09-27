import os
import shutil
import time
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from .. import db, models, schemas
from ..face_service import process_image_batch

router = APIRouter()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
TEST_IMAGES_DIR = os.path.join(BASE_DIR, "test_images")
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(TEST_IMAGES_DIR, exist_ok=True)

VALID_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".avif", ".bmp"}


@router.get("/processing-status", response_model=schemas.SystemProcessingStatusResponse)
def get_processing_status(session: Session = Depends(db.get_db)):
    """
    Retorna o status quantitativo da fila de processamento de fotos e reconhecimento facial.
    """
    pending = session.query(models.Photo).filter(models.Photo.process_status == models.ProcessStatusEnum.PENDING).count()
    processing = session.query(models.Photo).filter(models.Photo.process_status == models.ProcessStatusEnum.PROCESSING).count()
    completed = session.query(models.Photo).filter(models.Photo.process_status == models.ProcessStatusEnum.COMPLETED).count()
    failed = session.query(models.Photo).filter(models.Photo.process_status == models.ProcessStatusEnum.FAILED).count()
    total = session.query(models.Photo).count()

    return schemas.SystemProcessingStatusResponse(
        pending=pending,
        processing=processing,
        completed=completed,
        failed=failed,
        total=total,
    )


@router.get("/processing-photos", response_model=List[schemas.ProcessingPhotoDetail])
def get_processing_photos(
    status_filter: Optional[str] = Query("ALL", regex="^(ALL|PENDING|PROCESSING|COMPLETED|FAILED)$"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session = Depends(db.get_db),
):
    """
    Retorna lista detalhada de fotos e o status individual de cada uma (incluindo faces recortadas e erros).
    """
    query = session.query(models.Photo)
    if status_filter != "ALL":
        query = query.filter(models.Photo.process_status == models.ProcessStatusEnum(status_filter))

    photos = query.order_by(models.Photo.created_at.desc()).offset(offset).limit(limit).all()

    results = []
    for photo in photos:
        face_details = []
        for face in photo.detected_faces:
            crop_url = f"/api/faces/crop/{face.id}" if face.face_crop_path else None
            cluster_name = face.cluster.name if face.cluster else None
            student_id = face.cluster.student_id if face.cluster else None
            student_name = face.cluster.student.name if face.cluster and face.cluster.student else None

            face_details.append(schemas.DetectedFaceDetail(
                id=face.id,
                bounding_box=face.bounding_box or [],
                face_crop_url=crop_url,
                detection_score=face.detection_score,
                cluster_id=face.cluster_id,
                cluster_name=cluster_name,
                student_id=student_id,
                student_name=student_name,
            ))

        results.append(schemas.ProcessingPhotoDetail(
            id=photo.id,
            file_path=photo.file_path,
            image_url=f"/api/photos/file/{photo.file_path}",
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
    session: Session = Depends(db.get_db),
):
    """
    Dispara imediatamente uma rodada de processamento de reconhecimento facial no backend.
    """
    processed = process_image_batch(session, batch_size=batch_size)
    return schemas.ProcessNowResponse(
        processed_count=processed,
        message=f"{processed} foto(s) processada(s) com sucesso." if processed > 0 else "Nenhuma foto pendente na fila."
    )


@router.post("/ingest-test-folder", response_model=schemas.IngestTestFolderResponse)
def ingest_test_folder(
    class_id: Optional[int] = Query(None),
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

    # Identifica turma padrão se não fornecida
    target_class_id = class_id
    if target_class_id is None:
        first_class = session.query(models.Class).first()
        target_class_id = first_class.id if first_class else None

    # Identifica usuário uploader padrão
    first_user = session.query(models.User).first()
    uploader_id = first_user.id if first_user else 1

    files_in_dir = os.listdir(TEST_IMAGES_DIR)
    image_files = [f for f in files_in_dir if os.path.splitext(f.lower())[1] in VALID_IMAGE_EXTENSIONS]

    if not image_files:
        return schemas.IngestTestFolderResponse(
            imported_count=0,
            skipped_count=0,
            total_found=0,
            message="Nenhuma imagem encontrada em test_images/ (formatos aceitos: jpg, png, webp, heic, avif)."
        )

    imported = 0
    skipped = 0

    for filename in image_files:
        source_path = os.path.join(TEST_IMAGES_DIR, filename)
        if not os.path.isfile(source_path):
            continue

        # Nome de destino único para evitar colisões
        base_name, ext = os.path.splitext(filename)
        dest_filename = f"test_{int(time.time()*1000)}_{filename}"
        dest_path = os.path.join(UPLOADS_DIR, dest_filename)

        # Copia arquivo para uploads/
        shutil.copy2(source_path, dest_path)

        # Registra Photo com status PENDING
        new_photo = models.Photo(
            file_path=dest_filename,
            title=f"Teste: {base_name}",
            description="Importado da pasta de testes para reconhecimento facial",
            uploaded_by_user_id=uploader_id,
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
        total_found=len(image_files),
        message=f"{imported} foto(s) importada(s) da pasta test_images com sucesso para a fila (status PENDING)."
    )


@router.post("/reprocess-failed")
def reprocess_failed_photos(session: Session = Depends(db.get_db)):
    """
    Reinicia o status das fotos marcadas como FAILED de volta para PENDING.
    """
    failed_photos = session.query(models.Photo).filter(models.Photo.process_status == models.ProcessStatusEnum.FAILED).all()
    count = len(failed_photos)
    for photo in failed_photos:
        photo.process_status = models.ProcessStatusEnum.PENDING
        photo.process_error = None
    session.commit()
    return {"message": f"{count} fotos re-enfileiradas para processamento."}


@router.post("/reprocess-all")
def reprocess_all_photos(session: Session = Depends(db.get_db)):
    """
    Reinicia o status de todas as fotos para PENDING para re-processamento geral.
    """
    photos = session.query(models.Photo).all()
    count = len(photos)
    for photo in photos:
        photo.process_status = models.ProcessStatusEnum.PENDING
        photo.process_attempts = 0
        photo.process_error = None
    session.commit()
    return {"message": f"{count} fotos re-enfileiradas para processamento completo."}
