from urllib.error import HTTPError, URLError
from urllib.request import Request as UrllibRequest, urlopen
import json

from fastapi import APIRouter, HTTPException, Request

from app.core.config import settings

router = APIRouter(tags=["inference"])


def _inference_base_url() -> str:
    scheme = settings.inference_service_scheme.rstrip("/: ")
    return f"{scheme}://{settings.inference_service_host}:{settings.inference_service_port}"


def _forward_request(path: str, method: str = "GET", payload: dict | None = None) -> dict:
    url = _inference_base_url() + path
    data = None
    headers = {"Content-Type": "application/json"}

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    elif method == "POST":
        data = b""

    request = UrllibRequest(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else {"status": "ok"}
    except HTTPError as exc:
        try:
            body = exc.read().decode("utf-8")
            detail = json.loads(body).get("detail", body)
        except Exception:
            detail = exc.reason
        raise HTTPException(status_code=500, detail=f"Inference service HTTP {exc.code}: {detail}")
    except URLError as exc:
        raise HTTPException(status_code=502, detail=f"Não foi possível conectar ao serviço de inferência: {exc.reason}")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Resposta inválida do serviço de inferência")


@router.post("/inference/ftp/sync")
def proxy_ftp_sync():
    return _forward_request("/ftp/sync", method="POST")


@router.get("/inference/ftp/health")
def proxy_ftp_health():
    return _forward_request("/health", method="GET")


@router.post("/inference/process-s3")
async def proxy_process_s3(request: Request):
    payload = await request.json()
    return _forward_request("/process-s3", method="POST", payload=payload)
