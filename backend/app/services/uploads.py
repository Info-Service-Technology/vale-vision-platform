from pathlib import Path
from uuid import uuid4

import boto3
from botocore.config import Config
from fastapi import HTTPException, UploadFile

from app.core.config import settings

MAX_UPLOAD_SIZE_BYTES = 5 * 1024 * 1024
# Keep uploads inside app/static so they are served by FastAPI's /static mount.
UPLOADS_ROOT = Path(__file__).resolve().parents[1] / "static" / "uploads"


def ensure_upload_dir(folder: str) -> Path:
    path = UPLOADS_ROOT / folder
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_uploads_bucket() -> str:
    return settings.s3_bucket_uploads or settings.s3_bucket_raw or settings.s3_bucket_debug


def build_asset_api_path(key: str) -> str:
    return f"/api/assets/{key.lstrip('/')}"


async def save_image_upload(file: UploadFile, folder: str) -> str:
    content_type = file.content_type or ""
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Arquivo deve ser uma imagem")

    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="Imagem deve ter no máximo 5 MB")

    suffix = Path(file.filename or "upload").suffix.lower() or ".png"
    filename = f"{uuid4().hex}{suffix}"
    uploads_bucket = get_uploads_bucket()

    if uploads_bucket:
        key = f"branding/{folder}/{filename}"
        s3_client = boto3.client(
            "s3",
            region_name=settings.aws_region,
            config=Config(signature_version="s3v4"),
        )
        s3_client.put_object(
            Bucket=uploads_bucket,
            Key=key,
            Body=content,
            ContentType=content_type,
            CacheControl="public, max-age=300",
        )
        return build_asset_api_path(key)

    directory = ensure_upload_dir(folder)
    destination = directory / filename
    destination.write_bytes(content)
    return f"/static/uploads/{folder}/{filename}"


def create_asset_presigned_url(key: str) -> str:
    uploads_bucket = get_uploads_bucket()
    if not uploads_bucket:
        raise HTTPException(status_code=404, detail="Bucket de assets não configurado")

    s3_client = boto3.client(
        "s3",
        region_name=settings.aws_region,
        config=Config(signature_version="s3v4"),
    )
    return s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": uploads_bucket, "Key": key},
        ExpiresIn=3600,
    )
