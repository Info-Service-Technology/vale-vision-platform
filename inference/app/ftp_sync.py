import json
import os
import time
from datetime import datetime
from ftplib import FTP, error_perm
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import boto3

AWS_REGION = os.getenv("AWS_REGION", "sa-east-1")
APP_TIMEZONE = os.getenv("APP_TIMEZONE", "America/Sao_Paulo")
FTP_HOST = os.getenv("FTP_HOST")
FTP_PORT = int(os.getenv("FTP_PORT", "21"))
FTP_USER = os.getenv("FTP_USER")
FTP_PASSWORD = os.getenv("FTP_PASSWORD")
FTP_BASE_DIR = os.getenv("FTP_BASE_DIR", "/upload")
FTP_CAMERA_DIRS = os.getenv("FTP_CAMERA_DIRS", "cammadeira,campapelao,camplastico,camsucata")
FTP_POLL_INTERVAL_SECONDS = int(os.getenv("FTP_POLL_INTERVAL_SECONDS", "60"))
FTP_DOWNLOAD_DIR = Path(os.getenv("FTP_DOWNLOAD_DIR", "/tmp/ftp_download"))
FTP_STATE_FILE = Path(os.getenv("FTP_STATE_FILE", "/tmp/ftp_processed.json"))
FTP_MOVE_PROCESSED = os.getenv("FTP_MOVE_PROCESSED", "false").strip().lower() in {"1", "true", "yes"}
FTP_PROCESSED_SUBDIR = os.getenv("FTP_PROCESSED_SUBDIR", "processed")

S3_BUCKET = os.getenv("S3_BUCKET")
S3_PREFIX_RAW = os.getenv("S3_PREFIX_RAW", "raw/")
TENANT = os.getenv("TENANT")
S3_INCLUDE_TENANT_IN_KEY = os.getenv("S3_INCLUDE_TENANT_IN_KEY", "true").strip().lower() in {
    "1",
    "true",
    "yes",
}
VALID_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}

s3 = boto3.client("s3", region_name=AWS_REGION)


def _current_time() -> datetime:
    try:
        return datetime.now(ZoneInfo(APP_TIMEZONE))
    except Exception:
        return datetime.utcnow()


def _load_state() -> dict[str, Any]:
    if not FTP_STATE_FILE.exists():
        return {"processed_paths": {}}

    try:
        return json.loads(FTP_STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"processed_paths": {}}


def _save_state(state: dict[str, Any]) -> None:
    FTP_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    FTP_STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def _camera_dirs() -> list[str]:
    return [camera.strip() for camera in FTP_CAMERA_DIRS.split(",") if camera.strip()]


def _normalize_remote_dir(path: str) -> str:
    return path.replace("\\", "/").rstrip("/")


def _is_image_filename(filename: str) -> bool:
    return Path(filename).suffix.lower() in VALID_IMAGE_EXTENSIONS


def _build_s3_prefix(prefix: str) -> str:
    base = prefix.rstrip("/")

    if "{tenant}" in base:
        if not TENANT:
            raise RuntimeError("TENANT precisa estar configurado quando S3_PREFIX_RAW usa {tenant}.")
        return base.format(tenant=TENANT)

    if TENANT and S3_INCLUDE_TENANT_IN_KEY:
        return f"{base}/tenant={TENANT}"

    return base


def _build_s3_key(camera_name: str, filename: str) -> str:
    now = _current_time()
    prefix = _build_s3_prefix(S3_PREFIX_RAW)
    return (
        f"{prefix}/camera={camera_name}"
        f"/year={now.year:04d}/month={now.month:02d}/day={now.day:02d}/{filename}"
    )


def _connect_ftp() -> FTP:
    if not FTP_HOST or not FTP_USER or not FTP_PASSWORD:
        raise RuntimeError("FTP_HOST, FTP_USER e FTP_PASSWORD precisam estar definidos.")

    ftp = FTP()
    ftp.connect(FTP_HOST, FTP_PORT, timeout=30)
    ftp.login(FTP_USER, FTP_PASSWORD)
    return ftp


def _list_remote_files(ftp: FTP, remote_dir: str) -> list[str]:
    remote_dir = _normalize_remote_dir(remote_dir)
    try:
        ftp.cwd(remote_dir)
    except Exception as exc:
        print(f"[ftp_sync] Não foi possível acessar {remote_dir}: {exc}")
        return []

    try:
        files = ftp.nlst()
    except error_perm as exc:
        msg = str(exc)
        if "No such file or directory" in msg or "550" in msg:
            return []
        raise

    return [name for name in files if name not in {".", ".."}]


def _download_file(ftp: FTP, remote_path: str, local_path: Path) -> None:
    local_path.parent.mkdir(parents=True, exist_ok=True)
    with local_path.open("wb") as handle:
        ftp.retrbinary(f"RETR {remote_path}", handle.write)


def _upload_to_s3(local_path: Path, bucket: str, key: str) -> None:
    s3.upload_file(str(local_path), bucket, key)


def _move_remote_to_processed(ftp: FTP, remote_path: str) -> None:
    if not FTP_MOVE_PROCESSED:
        return

    source = _normalize_remote_dir(remote_path)
    base_dir = str(Path(source).parent)
    target_dir = f"{base_dir}/{FTP_PROCESSED_SUBDIR}".replace("\\", "/")

    try:
        ftp.cwd(target_dir)
    except Exception:
        try:
            ftp.mkd(target_dir)
        except Exception as exc:
            print(f"[ftp_sync] Falha ao criar diretório remoto {target_dir}: {exc}")
            return

    target_path = f"{target_dir}/{Path(source).name}".replace("\\", "/")
    try:
        ftp.rename(source, target_path)
        print(f"[ftp_sync] Arquivo remoto movido para {target_path}")
    except Exception as exc:
        print(f"[ftp_sync] Não foi possível mover {source} para {target_path}: {exc}")


def _process_camera_directory(ftp: FTP, state: dict[str, Any], camera_name: str) -> None:
    remote_dir = f"{FTP_BASE_DIR.rstrip('/')}/{camera_name}".replace("\\", "/")
    files = _list_remote_files(ftp, remote_dir)
    processed_paths = state.setdefault("processed_paths", {})

    for filename in sorted(files):
        if not _is_image_filename(filename):
            continue

        remote_path = f"{remote_dir}/{filename}".replace("\\", "/")
        if remote_path in processed_paths:
            continue

        local_path = FTP_DOWNLOAD_DIR / camera_name / filename

        try:
            print(f"[ftp_sync] Baixando {remote_path}")
            _download_file(ftp, remote_path, local_path)

            s3_key = _build_s3_key(camera_name, filename)
            _upload_to_s3(local_path, S3_BUCKET, s3_key)

            processed_paths[remote_path] = {
                "uploaded_at": _current_time().isoformat(),
                "s3_key": s3_key,
                "camera": camera_name,
            }
            _save_state(state)

            print(f"[ftp_sync] Enviado para S3: s3://{S3_BUCKET}/{s3_key}")

            _move_remote_to_processed(ftp, remote_path)

        except Exception as exc:
            print(f"[ftp_sync][erro] Falha no arquivo {remote_path}: {exc}")
        finally:
            try:
                if local_path.exists():
                    local_path.unlink()
            except Exception:
                pass


def run_once() -> None:
    if not S3_BUCKET:
        raise RuntimeError("S3_BUCKET precisa estar configurado.")

    state = _load_state()
    with _connect_ftp() as ftp:
        for camera_name in _camera_dirs():
            _process_camera_directory(ftp, state, camera_name)


def run_daemon() -> None:
    print("[ftp_sync] Iniciando watcher FTP")
    while True:
        try:
            run_once()
        except Exception as exc:
            print(f"[ftp_sync][erro] Falha no ciclo FTP: {exc}")
        time.sleep(FTP_POLL_INTERVAL_SECONDS)
