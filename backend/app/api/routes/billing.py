from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import SessionLocal
from app.models.models import BillingEvent, Tenant, User
from app.services.audit import write_audit_log

router = APIRouter(tags=["billing"])

BILLING_STATUSES = {
    "active",
    "past_due",
    "grace_period",
    "suspended_read_only",
    "suspended_full",
    "terminated",
}


class UpdateTenantBillingPayload(BaseModel):
    billing_status: str
    billing_due_date: str | None = None
    billing_grace_until: str | None = None
    billing_suspended_at: str | None = None
    billing_contact_email: str | None = None
    billing_notes: str | None = None
    payment_method: str | None = None
    contract_type: str | None = None
    billing_amount: float | None = None
    billing_currency: str | None = None
    billing_cycle: str | None = None
    plan_slug: str | None = None


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None

    normalized = value.strip()
    if not normalized:
        return None

    try:
        return datetime.fromisoformat(normalized.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Data de billing inválida") from exc


def serialize_tenant_billing(tenant: Tenant):
    return {
        "id": tenant.id,
        "name": tenant.name,
        "slug": tenant.slug,
        "scope_type": tenant.scope_type,
        "scope_value": tenant.scope_value,
        "company_logo_url": tenant.company_logo_url,
        "platform_title": f"{tenant.name} Vision Platform",
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
    }


def get_requester_and_tenant(db: Session, current_user: dict, tenant_slug: str | None):
    requester = db.query(User).filter(User.id == current_user.get("user_id")).first()
    if not requester:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    tenant = None
    normalized_slug = (tenant_slug or "").strip().lower()

    if requester.role == "super-admin":
        if normalized_slug:
            tenant = db.query(Tenant).filter(Tenant.slug == normalized_slug).first()
        elif requester.tenant_id:
            tenant = db.query(Tenant).filter(Tenant.id == requester.tenant_id).first()
        else:
            tenant = db.query(Tenant).order_by(Tenant.name.asc()).first()
    else:
        if not requester.tenant_id:
            raise HTTPException(status_code=400, detail="Usuário sem tenant vinculado")
        tenant = db.query(Tenant).filter(Tenant.id == requester.tenant_id).first()
        if normalized_slug and tenant and tenant.slug != normalized_slug:
            raise HTTPException(status_code=403, detail="Sem acesso ao billing de outro tenant")

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado")

    return requester, tenant


@router.get("/billing/current")
def get_current_billing(
    tenant_slug: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    _, tenant = get_requester_and_tenant(db, current_user, tenant_slug)
    return {"tenant": serialize_tenant_billing(tenant)}


@router.get("/billing/tenants")
def list_billing_tenants(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    requester = db.query(User).filter(User.id == current_user.get("user_id")).first()
    if not requester:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    query = db.query(Tenant).order_by(Tenant.name.asc())
    if requester.role != "super-admin":
        query = query.filter(Tenant.id == requester.tenant_id)

    tenants = query.all()
    return {"items": [serialize_tenant_billing(tenant) for tenant in tenants]}


@router.put("/admin/billing/tenants/{tenant_id}")
def update_tenant_billing(
    tenant_id: int,
    payload: UpdateTenantBillingPayload,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    requester = db.query(User).filter(User.id == current_user.get("user_id")).first()
    if not requester or requester.role != "super-admin":
        raise HTTPException(status_code=403, detail="Acesso restrito ao super-admin")

    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado")

    next_status = (payload.billing_status or "").strip().lower()
    if next_status not in BILLING_STATUSES:
        raise HTTPException(status_code=400, detail="Status de billing inválido")

    previous_status = tenant.billing_status or "active"
    tenant.billing_status = next_status
    tenant.billing_due_date = parse_datetime(payload.billing_due_date)
    tenant.billing_grace_until = parse_datetime(payload.billing_grace_until)
    tenant.billing_suspended_at = parse_datetime(payload.billing_suspended_at)
    tenant.billing_contact_email = (payload.billing_contact_email or "").strip() or None
    tenant.billing_notes = (payload.billing_notes or "").strip() or None
    tenant.payment_method = (payload.payment_method or "").strip() or None
    tenant.contract_type = (payload.contract_type or "").strip() or None
    tenant.billing_amount = payload.billing_amount
    tenant.billing_currency = (payload.billing_currency or "").strip() or None
    tenant.billing_cycle = (payload.billing_cycle or "").strip() or None
    tenant.plan_slug = (payload.plan_slug or "").strip() or "free"

    db.add(tenant)
    db.add(
        BillingEvent(
            tenant_id=tenant.id,
            event_type="billing_updated",
            previous_status=previous_status,
            next_status=tenant.billing_status,
            message=f"Status financeiro alterado de {previous_status} para {tenant.billing_status}",
            actor_user_id=requester.id,
            created_at=datetime.now().replace(tzinfo=None),
        )
    )
    db.commit()
    db.refresh(tenant)

    write_audit_log(
        db,
        user_id=requester.id,
        user_email=requester.email,
        tenant_id=tenant.id,
        action="tenant_billing_updated",
        method="PUT",
        endpoint=f"/api/admin/billing/tenants/{tenant_id}",
        status=200,
        details={
            "tenant_id": tenant.id,
            "billing_status": tenant.billing_status,
            "billing_due_date": tenant.billing_due_date.isoformat() if tenant.billing_due_date else None,
            "billing_grace_until": tenant.billing_grace_until.isoformat() if tenant.billing_grace_until else None,
            "billing_suspended_at": tenant.billing_suspended_at.isoformat() if tenant.billing_suspended_at else None,
            "billing_contact_email": tenant.billing_contact_email,
            "plan_slug": tenant.plan_slug,
        },
    )

    return {"tenant": serialize_tenant_billing(tenant)}
