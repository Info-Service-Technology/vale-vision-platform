from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import SessionLocal
from app.models.models import BillingEvent, Tenant, TenantDomain, User
from app.services.audit import write_audit_log

router = APIRouter(prefix="/admin/tenants", tags=["admin-tenants"])


class TenantPayload(BaseModel):
    name: str
    slug: str
    scope_type: str | None = None
    scope_value: str | None = None
    is_active: bool = True
    billing_contact_email: str | None = None
    plan_slug: str | None = None


class TenantDomainPayload(BaseModel):
    domain: str
    is_verified: bool = True
    is_primary: bool = False
    is_active: bool = True
    match_mode: str = "exact"


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_requester(db: Session, current_user: dict) -> User:
    user = db.query(User).filter(User.id == current_user.get("user_id")).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário autenticado não encontrado")
    if user.role != "super-admin":
        raise HTTPException(status_code=403, detail="Acesso restrito ao super-admin")
    return user


def normalize_slug(value: str) -> str:
    return str(value or "").strip().lower()


def serialize_tenant(tenant: Tenant):
    return {
        "id": tenant.id,
        "name": tenant.name,
        "slug": tenant.slug,
        "scope_type": tenant.scope_type,
        "scope_value": tenant.scope_value,
        "is_active": True if tenant.is_active is None else tenant.is_active,
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
        "company_logo_url": tenant.company_logo_url,
        "platform_title": f"{tenant.name} Vision Platform",
    }


def serialize_domain(row: TenantDomain):
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "domain": row.domain,
        "is_verified": True if row.is_verified is None else row.is_verified,
        "is_primary": True if row.is_primary else False,
        "is_active": True if row.is_active is None else row.is_active,
        "match_mode": row.match_mode or "exact",
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def serialize_billing_event(row: BillingEvent, actor_email: str | None):
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "event_type": row.event_type,
        "previous_status": row.previous_status,
        "next_status": row.next_status,
        "message": row.message,
        "actor_user_id": row.actor_user_id,
        "actor_email": actor_email,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@router.get("")
def list_tenants(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    get_requester(db, current_user)
    rows = db.query(Tenant).order_by(Tenant.name.asc()).all()
    return {"items": [serialize_tenant(row) for row in rows]}


@router.post("")
def create_tenant(
    payload: TenantPayload,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    requester = get_requester(db, current_user)
    slug = normalize_slug(payload.slug)
    if not slug:
        raise HTTPException(status_code=400, detail="Slug do tenant é obrigatório")

    existing = db.query(Tenant).filter(Tenant.slug == slug).first()
    if existing:
        raise HTTPException(status_code=400, detail="Slug do tenant já cadastrado")

    tenant = Tenant(
        name=payload.name.strip(),
        slug=slug,
        scope_type=(payload.scope_type or "ORG").strip().upper(),
        scope_value=(payload.scope_value or "global").strip(),
        is_active=payload.is_active,
        billing_status="active",
        billing_contact_email=(payload.billing_contact_email or "").strip() or None,
        billing_currency="BRL",
        billing_cycle="monthly",
        plan_slug=(payload.plan_slug or "free").strip().lower(),
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    write_audit_log(
        db,
        user_id=requester.id,
        user_email=requester.email,
        tenant_id=tenant.id,
        action="tenant_created",
        method="POST",
        endpoint="/api/admin/tenants",
        status=201,
        details={"tenant_id": tenant.id, "slug": tenant.slug},
    )

    return serialize_tenant(tenant)


@router.put("/{tenant_id}")
def update_tenant(
    tenant_id: int,
    payload: TenantPayload,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    requester = get_requester(db, current_user)
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado")

    slug = normalize_slug(payload.slug)
    existing = db.query(Tenant).filter(Tenant.slug == slug, Tenant.id != tenant_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Slug do tenant já cadastrado")

    tenant.name = payload.name.strip()
    tenant.slug = slug
    tenant.scope_type = (payload.scope_type or "ORG").strip().upper()
    tenant.scope_value = (payload.scope_value or "global").strip()
    tenant.is_active = payload.is_active
    tenant.billing_contact_email = (payload.billing_contact_email or "").strip() or None
    tenant.plan_slug = (payload.plan_slug or "free").strip().lower()
    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    write_audit_log(
        db,
        user_id=requester.id,
        user_email=requester.email,
        tenant_id=tenant.id,
        action="tenant_updated",
        method="PUT",
        endpoint=f"/api/admin/tenants/{tenant_id}",
        status=200,
        details={"tenant_id": tenant.id, "slug": tenant.slug},
    )

    return serialize_tenant(tenant)


@router.get("/{tenant_id}/domains")
def list_tenant_domains(
    tenant_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    get_requester(db, current_user)
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado")

    rows = (
        db.query(TenantDomain)
        .filter(TenantDomain.tenant_id == tenant_id)
        .order_by(TenantDomain.is_primary.desc(), TenantDomain.domain.asc())
        .all()
    )
    return {"tenant": serialize_tenant(tenant), "items": [serialize_domain(row) for row in rows]}


@router.post("/{tenant_id}/domains")
def create_tenant_domain(
    tenant_id: int,
    payload: TenantDomainPayload,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    requester = get_requester(db, current_user)
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado")

    domain = normalize_slug(payload.domain)
    if not domain or "." not in domain:
        raise HTTPException(status_code=400, detail="Domínio inválido")

    match_mode = (payload.match_mode or "exact").strip().lower()
    if match_mode not in {"exact", "suffix"}:
        raise HTTPException(status_code=400, detail="match_mode inválido")

    existing = db.query(TenantDomain).filter(TenantDomain.domain == domain).first()
    if existing:
        raise HTTPException(status_code=400, detail="Domínio já cadastrado")

    if payload.is_primary:
        (
            db.query(TenantDomain)
            .filter(TenantDomain.tenant_id == tenant_id)
            .update({"is_primary": False})
        )

    row = TenantDomain(
        tenant_id=tenant_id,
        domain=domain,
        is_verified=payload.is_verified,
        is_primary=payload.is_primary,
        is_active=payload.is_active,
        match_mode=match_mode,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    write_audit_log(
        db,
        user_id=requester.id,
        user_email=requester.email,
        tenant_id=tenant_id,
        action="tenant_domain_created",
        method="POST",
        endpoint=f"/api/admin/tenants/{tenant_id}/domains",
        status=201,
        details={"tenant_id": tenant_id, "domain": row.domain},
    )

    return serialize_domain(row)


@router.delete("/domains/{domain_id}")
def delete_tenant_domain(
    domain_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    requester = get_requester(db, current_user)
    row = db.query(TenantDomain).filter(TenantDomain.id == domain_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Domínio não encontrado")

    tenant_id = row.tenant_id
    domain = row.domain
    db.delete(row)
    db.commit()

    write_audit_log(
        db,
        user_id=requester.id,
        user_email=requester.email,
        tenant_id=tenant_id,
        action="tenant_domain_deleted",
        method="DELETE",
        endpoint=f"/api/admin/tenants/domains/{domain_id}",
        status=200,
        details={"tenant_id": tenant_id, "domain": domain},
    )

    return {"message": "Domínio removido com sucesso"}


@router.get("/{tenant_id}/billing-events")
def list_billing_events(
    tenant_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    get_requester(db, current_user)
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado")

    rows = (
        db.query(BillingEvent)
        .filter(BillingEvent.tenant_id == tenant_id)
        .order_by(BillingEvent.created_at.desc(), BillingEvent.id.desc())
        .all()
    )
    user_ids = [row.actor_user_id for row in rows if row.actor_user_id]
    users = {
        user.id: user.email
        for user in db.query(User).filter(User.id.in_(user_ids)).all()
    } if user_ids else {}

    return {
        "tenant": serialize_tenant(tenant),
        "items": [serialize_billing_event(row, users.get(row.actor_user_id)) for row in rows],
    }
