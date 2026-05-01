from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.core.security import get_current_user, get_optional_current_user
from app.db.session import SessionLocal
from app.models.models import Tenant, User
from app.services.billing_access import ensure_tenant_write_allowed
from app.services.audit import write_audit_log
from app.services.uploads import save_image_upload

router = APIRouter(tags=["tenants"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/tenants/current")
def get_current_tenant(
    slug: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: dict | None = Depends(get_optional_current_user),
):
    tenant = None

    normalized_slug = (slug or "").strip().lower()
    if normalized_slug:
        tenant = db.query(Tenant).filter(Tenant.slug == normalized_slug).first()
    elif current_user and current_user.get("tenant_id"):
        user = db.query(User).filter(User.id == current_user.get("user_id")).first()
        if user and user.tenant_id:
            tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
    else:
        tenant = db.query(Tenant).order_by(Tenant.id.asc()).first()

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado")

    return {
        "id": tenant.id,
        "name": tenant.name,
        "slug": tenant.slug,
        "scope_type": tenant.scope_type,
        "scope_value": tenant.scope_value,
        "company_logo_url": tenant.company_logo_url,
        "billing_status": tenant.billing_status or "active",
        "billing_due_date": tenant.billing_due_date.isoformat() if tenant.billing_due_date else None,
        "billing_grace_until": tenant.billing_grace_until.isoformat() if tenant.billing_grace_until else None,
        "billing_suspended_at": tenant.billing_suspended_at.isoformat() if tenant.billing_suspended_at else None,
        "billing_contact_email": tenant.billing_contact_email,
        "billing_notes": tenant.billing_notes,
        "payment_method": tenant.payment_method,
        "contract_type": tenant.contract_type,
        "billing_amount": tenant.billing_amount,
        "billing_currency": tenant.billing_currency,
        "billing_cycle": tenant.billing_cycle,
        "plan_slug": tenant.plan_slug or "free",
        "platform_title": f"{tenant.name} Vision Platform",
    }


@router.get("/tenants")
def list_tenants(db: Session = Depends(get_db)):
    tenants = db.query(Tenant).order_by(Tenant.name.asc()).all()

    return {
        "items": [
            {
                "id": tenant.id,
                "name": tenant.name,
                "slug": tenant.slug,
                "scope_type": tenant.scope_type,
                "scope_value": tenant.scope_value,
                "company_logo_url": tenant.company_logo_url,
                "billing_status": tenant.billing_status or "active",
                "billing_due_date": tenant.billing_due_date.isoformat() if tenant.billing_due_date else None,
                "billing_grace_until": tenant.billing_grace_until.isoformat() if tenant.billing_grace_until else None,
                "billing_suspended_at": tenant.billing_suspended_at.isoformat() if tenant.billing_suspended_at else None,
                "billing_contact_email": tenant.billing_contact_email,
                "billing_notes": tenant.billing_notes,
                "payment_method": tenant.payment_method,
                "contract_type": tenant.contract_type,
                "billing_amount": tenant.billing_amount,
                "billing_currency": tenant.billing_currency,
                "billing_cycle": tenant.billing_cycle,
                "plan_slug": tenant.plan_slug or "free",
                "platform_title": f"{tenant.name} Vision Platform",
            }
            for tenant in tenants
        ]
    }


@router.post("/tenants/current/logo")
async def upload_current_tenant_logo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user = db.query(User).filter(User.id == current_user.get("user_id")).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    if user.role not in {"super-admin", "admin-tenant"}:
        raise HTTPException(status_code=403, detail="Sem permissão para alterar o logo da empresa")

    ensure_tenant_write_allowed(db, user)

    if not user.tenant_id:
        raise HTTPException(status_code=400, detail="Usuário sem tenant vinculado")

    tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado")

    logo_url = await save_image_upload(file, "tenant-logos")
    tenant.company_logo_url = logo_url
    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    write_audit_log(
        db,
        user_id=user.id,
        user_email=user.email,
        tenant_id=user.tenant_id,
        action="tenant_logo_uploaded",
        method="POST",
        endpoint="/api/tenants/current/logo",
        status=200,
        details={"tenant_id": tenant.id, "company_logo_url": logo_url},
    )

    return {"company_logo_url": logo_url}
