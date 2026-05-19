from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from threading import Lock

from app.ftp_sync import run_once
from app.processor import process_image_from_s3


class ProcessS3Request(BaseModel):
    bucket: str
    key: str
    grupo: str | None = None
    camera_name: str | None = None
    fill_percent: float | None = None
    metadata: dict | None = None


app = FastAPI(title="Inference Service API")

_ftp_lock = Lock()


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/ftp/sync")
def trigger_ftp_sync():
    if not _ftp_lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="FTP sync já em execução")

    try:
        run_once()
        return {"status": "ok", "message": "FTP sync executado com sucesso"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        _ftp_lock.release()


@app.post("/process-s3")
def process_s3_object(payload: ProcessS3Request):
    try:
        result = process_image_from_s3(
            bucket=payload.bucket,
            key=payload.key,
            grupo=payload.grupo,
            camera_name=payload.camera_name,
            fill_percent=payload.fill_percent,
            metadata=payload.metadata,
        )
        return {"status": "ok", "result": result}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
