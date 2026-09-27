import os
import time
import shutil
from app import db, models

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
TEST_IMAGES_DIR = os.path.join(BASE_DIR, "test_images")
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(TEST_IMAGES_DIR, exist_ok=True)

VALID_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".avif", ".bmp"}


def ingest():
    print(f"Varrendo pasta de testes: {TEST_IMAGES_DIR}")
    files_in_dir = os.listdir(TEST_IMAGES_DIR)
    image_files = [f for f in files_in_dir if os.path.splitext(f.lower())[1] in VALID_IMAGE_EXTENSIONS]

    if not image_files:
        print("Nenhuma imagem encontrada em test_images/.")
        print("Coloque arquivos .jpg, .png, etc. na pasta test_images/ e execute novamente.")
        return

    session = db.SessionLocal()
    try:
        first_class = session.query(models.Class).first()
        target_class_id = first_class.id if first_class else None
        first_user = session.query(models.User).first()
        uploader_id = first_user.id if first_user else 1

        imported = 0
        for filename in image_files:
            source_path = os.path.join(TEST_IMAGES_DIR, filename)
            if not os.path.isfile(source_path):
                continue

            base_name, ext = os.path.splitext(filename)
            dest_filename = f"test_{int(time.time()*1000)}_{filename}"
            dest_path = os.path.join(UPLOADS_DIR, dest_filename)

            shutil.copy2(source_path, dest_path)

            new_photo = models.Photo(
                file_path=dest_filename,
                title=f"Teste: {base_name}",
                description="Importado via CLI ingest_test.py",
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
        print(f"Sucesso: {imported} foto(s) importada(s) para a fila com status PENDING!")
        print("Agora execute 'python worker.py --once' ou use o botão na interface web para processar.")
    finally:
        session.close()


if __name__ == "__main__":
    ingest()
