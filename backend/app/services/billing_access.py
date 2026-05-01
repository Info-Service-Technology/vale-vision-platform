from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.models import Tenant, User

RESTRICTED_BILLING_STATUSES = {
    "suspended_read_only",
    "suspended_full",
    "terminated",
}


def normalize_billing_status(value: str | None) -> str:
    normalized = (value or "active").strip().lower()
    return normalized or "active"


def ensure_tenant_write_allowed(db: Session, user: User):
    if user.role == "super-admin":
        return

    if not user.tenant_id:
        raise HTTPException(status_code=400, detail="Usuário sem tenant vinculado")

    tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado")

    if normalize_billing_status(tenant.billing_status) in RESTRICTED_BILLING_STATUSES:
        raise HTTPException(
            status_code=403,
            detail="Este tenant está com restrição operacional por billing",
        )
