from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse

from app.services.uploads import create_asset_presigned_url

router = APIRouter(tags=["assets"])


@router.get("/assets/{asset_key:path}")
def get_asset(asset_key: str):
    normalized_key = (asset_key or "").strip().lstrip("/")
    if not normalized_key:
        raise HTTPException(status_code=404, detail="Asset não encontrado")

    url = create_asset_presigned_url(normalized_key)
    return RedirectResponse(url=url, status_code=307)
