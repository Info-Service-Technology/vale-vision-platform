from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.models import Tenant

router = APIRouter(tags=["tenants"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/tenants/current")
def get_current_tenant(db: Session = Depends(get_db)):
    tenant = db.query(Tenant).order_by(Tenant.id.asc()).first()

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado")

    return {
        "id": tenant.id,
        "name": tenant.name,
        "slug": tenant.slug,
        "scope_type": tenant.scope_type,
        "scope_value": tenant.scope_value,
        "platform_title": f"{tenant.name} Vision Platform",
    }