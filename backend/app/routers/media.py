import os
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from jose import JWTError, jwt
from ..security import SECRET_KEY, ALGORITHM

router = APIRouter()
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")

@router.get("/")
def get_media(
    path: str = Query(...),
    signature: str = Query(...)
):
    """
    Serve a imagem local se a assinatura JWT for válida e não estiver expirada.
    Isso simula o comportamento de Pre-signed URLs do AWS S3 ou Google Cloud Storage.
    """
    try:
        payload = jwt.decode(signature, SECRET_KEY, algorithms=[ALGORITHM])
        signed_path = payload.get("path")
        if signed_path != path:
            raise HTTPException(status_code=403, detail="Invalid signature path")
    except JWTError:
        raise HTTPException(status_code=403, detail="Signature expired or invalid")
        
    file_path = os.path.join(UPLOAD_DIR, path)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
        
    return FileResponse(file_path)
