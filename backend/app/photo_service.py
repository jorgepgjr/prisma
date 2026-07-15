import os
import time
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.orm import Session
from .models import Photo, PhotoStatusEnum

# Define o diretório de uploads local (no nível do projeto backend/uploads)
UPLOAD_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "uploads")
)

# Garante que o diretório de uploads existe
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".avif"}

def save_photo(file: UploadFile, session: Session, user_id: int, class_id: int = None) -> Photo:
    # 1. Validação de extensão do arquivo
    original_filename = file.filename
    _, ext = os.path.splitext(original_filename.lower())
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de arquivo não permitido. Apenas {', '.join(ALLOWED_EXTENSIONS)} são aceitos."
        )

    # 2. Geração de nome único usando timestamp (milissegundos)
    unique_filename = f"{int(time.time() * 1000)}{ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    # 3. Escrita do arquivo em disco
    try:
        with open(file_path, "wb") as buffer:
            # Lê o conteúdo do UploadFile em blocos para evitar sobrecarga de memória
            while content := file.file.read(1024 * 1024):
                buffer.write(content)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao salvar arquivo localmente: {str(e)}"
        )

    # 4. Gravação dos metadados no banco de dados
    new_photo = Photo(
        file_id=unique_filename,
        title=original_filename,
        uploaded_by_user_id=user_id,
        class_id=class_id,
        status=PhotoStatusEnum.PENDING_REVIEW
    )
    
    try:
        session.add(new_photo)
        session.commit()
        session.refresh(new_photo)
    except Exception as e:
        # Em caso de falha no banco de dados, removemos o arquivo salvo para evitar lixo no disco
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao salvar registro de foto no banco de dados: {str(e)}"
        )

    return new_photo

def get_photo_path(file_id: str) -> str:
    # Evita Directory Traversal garantindo que apenas o nome do arquivo seja usado
    filename = os.path.basename(file_id)
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Arquivo de foto não encontrado."
        )
    return file_path
