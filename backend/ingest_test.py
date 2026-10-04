import os
import shutil
import uuid
from app import db, models
from app.test_ingestion import extract_test_archives, find_test_images

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
TEST_IMAGES_DIR = os.path.join(BASE_DIR, "test_images")
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(TEST_IMAGES_DIR, exist_ok=True)

def ingest():
    print(f"Varrendo pasta de testes: {TEST_IMAGES_DIR}")
    for warning in extract_test_archives(TEST_IMAGES_DIR):
        print(f"Aviso: {warning}")
    image_paths = find_test_images(TEST_IMAGES_DIR)

    if not image_paths:
        print("Nenhuma imagem encontrada em test_images/.")
        print("Coloque arquivos .jpg, .png, etc. na pasta test_images/ e execute novamente.")
        return

    session = db.SessionLocal()
    try:
        first_user = session.query(models.User).first()
        if not first_user:
            print("Nenhum usuário cadastrado para vincular às fotos.")
            return
        school_id = first_user.school_id
        first_class = session.query(models.Class).filter(models.Class.school_id == school_id).first()
        target_class_id = first_class.id if first_class else None

        imported = 0
        for source_path in image_paths:
            filename = os.path.basename(source_path)

            base_name, ext = os.path.splitext(filename)
            dest_filename = f"test_{uuid.uuid4().hex}_{filename}"
            relative_path = os.path.join(str(school_id), dest_filename)
            dest_path = os.path.join(UPLOADS_DIR, relative_path)
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)

            shutil.copy2(source_path, dest_path)

            new_photo = models.Photo(
                school_id=school_id,
                file_path=relative_path.replace(os.sep, "/"),
                title=f"Teste: {base_name}",
                description="Importado via CLI ingest_test.py",
                uploaded_by_user_id=first_user.id,
                class_id=target_class_id,
                status=models.PhotoStatusEnum.PENDING_REVIEW,
                process_status=models.ProcessStatusEnum.PENDING,
                process_attempts=0,
                process_error=None,
            )
            session.add(new_photo)
            imported += 1

        session.commit()
        print(f"Sucesso: {imported} foto(s) importada(s) para a fila com status PENDING!")
        print("Agora execute 'python worker.py --once' ou use o botão na interface web para processar.")
    finally:
        session.close()


if __name__ == "__main__":
    ingest()
