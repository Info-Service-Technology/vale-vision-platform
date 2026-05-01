from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile

MAX_UPLOAD_SIZE_BYTES = 5 * 1024 * 1024
UPLOADS_ROOT = Path(__file__).resolve().parents[2] / "static" / "uploads"


def ensure_upload_dir(folder: str) -> Path:
    path = UPLOADS_ROOT / folder
    path.mkdir(parents=True, exist_ok=True)
    return path


async def save_image_upload(file: UploadFile, folder: str) -> str:
    content_type = file.content_type or ""
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Arquivo deve ser uma imagem")

    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="Imagem deve ter no máximo 5 MB")

    suffix = Path(file.filename or "upload").suffix.lower() or ".png"
    filename = f"{uuid4().hex}{suffix}"
    directory = ensure_upload_dir(folder)
    destination = directory / filename
    destination.write_bytes(content)

    return f"/static/uploads/{folder}/{filename}"
