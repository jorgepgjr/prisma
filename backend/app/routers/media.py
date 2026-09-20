import os
from io import BytesIO
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, Response
from jose import JWTError, jwt
from PIL import Image, ImageOps
from pillow_heif import register_heif_opener
from ..security import SECRET_KEY, ALGORITHM

router = APIRouter()
UPLOAD_DIR = Path(__file__).resolve().parents[2] / "uploads"
register_heif_opener()
MOBILE_IMAGE_SUFFIXES = {".avif", ".heic", ".heif"}

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
        
    safe_path = os.path.basename(path)
    file_path = UPLOAD_DIR / safe_path
    if safe_path != path or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
        
    if file_path.suffix.lower() in MOBILE_IMAGE_SUFFIXES:
        try:
            with Image.open(file_path) as source:
                image = ImageOps.exif_transpose(source)
                if image.mode in {"RGBA", "LA"}:
                    background = Image.new("RGB", image.size, "white")
                    background.paste(image, mask=image.getchannel("A"))
                    image = background
                elif image.mode != "RGB":
                    image = image.convert("RGB")
                image.thumbnail((2560, 2560))
                output = BytesIO()
                image.save(output, format="JPEG", quality=90, optimize=True)
            return Response(
                content=output.getvalue(),
                media_type="image/jpeg",
                headers={"Cache-Control": "private, max-age=900"},
            )
        except Exception as error:
            raise HTTPException(status_code=500, detail="Não foi possível preparar a imagem.") from error

    return FileResponse(file_path)
