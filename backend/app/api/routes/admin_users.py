from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.security import get_current_user, hash_password
from app.db.session import SessionLocal
from app.models.models import Tenant, User
from app.services.billing_access import ensure_tenant_write_allowed
from app.services.audit import write_audit_log
from app.services.email import send_approved_user_email, send_rejected_user_email

router = APIRouter(prefix="/admin/users", tags=["admin-users"])


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

    return user


def ensure_user_admin(user: User):
    if user.role not in {"super-admin", "admin-tenant"}:
        raise HTTPException(status_code=403, detail="Acesso administrativo negado")


def can_manage_target(requester: User, target: User) -> bool:
    if requester.role == "super-admin":
        return True

    return requester.tenant_id is not None and requester.tenant_id == target.tenant_id


def allowed_roles_for(requester: User) -> set[str]:
    if requester.role == "super-admin":
        return {"super-admin", "admin-tenant", "operator", "viewer"}

    return {"admin-tenant", "operator", "viewer"}


def serialize_user(user: User, tenant: Tenant | None):
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "approval_status": user.approval_status or "approved",
        "is_active": True if user.is_active is None else user.is_active,
        "tenant_id": user.tenant_id,
        "tenant_slug": tenant.slug if tenant else None,
        "tenant_name": tenant.name if tenant else None,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


class AdminUserCreateRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str
    tenant_id: int | None = None


class AdminUserUpdateRequest(BaseModel):
    name: str
    role: str
    tenant_id: int | None = None
    password: str | None = None


@router.get("")
def list_users(
    search: str | None = Query(default=None),
    role: str | None = Query(default=None),
    approval_status: str | None = Query(default=None),
    tenant_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    requester = get_requester(db, current_user)
    ensure_user_admin(requester)

    query = db.query(User)

    if requester.role != "super-admin":
      query = query.filter(User.tenant_id == requester.tenant_id)
    elif tenant_id:
      query = query.filter(User.tenant_id == tenant_id)

    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                User.name.ilike(pattern),
                User.email.ilike(pattern),
            )
        )

    if role:
        query = query.filter(User.role == role)

    if approval_status:
        query = query.filter(User.approval_status == approval_status)

    users = query.order_by(User.id.desc()).all()
    tenants = {
        tenant.id: tenant
        for tenant in db.query(Tenant).all()
    }

    return {
        "items": [serialize_user(user, tenants.get(user.tenant_id)) for user in users],
        "total": len(users),
    }


@router.post("")
def create_user(
    payload: AdminUserCreateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    requester = get_requester(db, current_user)
    ensure_user_admin(requester)
    ensure_tenant_write_allowed(db, requester)

    if payload.role not in allowed_roles_for(requester):
        raise HTTPException(status_code=403, detail="Perfil não permitido para este usuário")

    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email já cadastrado")

    resolved_tenant_id = payload.tenant_id
    if requester.role != "super-admin":
        resolved_tenant_id = requester.tenant_id

    if not resolved_tenant_id:
        raise HTTPException(status_code=400, detail="Tenant obrigatório")

    tenant = db.query(Tenant).filter(Tenant.id == resolved_tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado")

    user = User(
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role,
        tenant_id=resolved_tenant_id,
        approval_status="approved",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    write_audit_log(
        db,
        user_id=requester.id,
        user_email=requester.email,
        tenant_id=requester.tenant_id,
        action="admin_user_created",
        method="POST",
        endpoint="/api/admin/users",
        status=201,
        details={"created_user_id": user.id, "role": user.role, "tenant_id": user.tenant_id},
    )

    return serialize_user(user, tenant)


@router.put("/{user_id}")
def update_user(
    user_id: int,
    payload: AdminUserUpdateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    requester = get_requester(db, current_user)
    ensure_user_admin(requester)
    ensure_tenant_write_allowed(db, requester)

    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    if not can_manage_target(requester, target):
        raise HTTPException(status_code=403, detail="Sem permissão para editar este usuário")

    if payload.role not in allowed_roles_for(requester):
        raise HTTPException(status_code=403, detail="Perfil não permitido para este usuário")

    target.name = payload.name
    target.role = payload.role

    if requester.role == "super-admin":
        if not payload.tenant_id:
            raise HTTPException(status_code=400, detail="Tenant obrigatório")

        tenant = db.query(Tenant).filter(Tenant.id == payload.tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant não encontrado")
        target.tenant_id = payload.tenant_id
    else:
        tenant = db.query(Tenant).filter(Tenant.id == requester.tenant_id).first()

    if payload.password:
        target.password_hash = hash_password(payload.password)

    db.add(target)
    db.commit()
    db.refresh(target)

    write_audit_log(
        db,
        user_id=requester.id,
        user_email=requester.email,
        tenant_id=requester.tenant_id,
        action="admin_user_updated",
        method="PUT",
        endpoint=f"/api/admin/users/{user_id}",
        status=200,
        details={"target_user_id": target.id, "role": target.role, "tenant_id": target.tenant_id},
    )

    return serialize_user(target, tenant)


@router.get("/pending")
def list_pending_users(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    requester = get_requester(db, current_user)
    ensure_user_admin(requester)

    query = db.query(User).filter(User.approval_status == "pending")

    if requester.role != "super-admin":
        query = query.filter(User.tenant_id == requester.tenant_id)

    users = query.order_by(User.id.desc()).all()
    tenants = {tenant.id: tenant for tenant in db.query(Tenant).all()}

    return {
        "items": [serialize_user(user, tenants.get(user.tenant_id)) for user in users],
        "total": len(users),
    }


@router.post("/{user_id}/approve")
def approve_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    requester = get_requester(db, current_user)
    ensure_user_admin(requester)
    ensure_tenant_write_allowed(db, requester)

    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    if not can_manage_target(requester, target):
        raise HTTPException(status_code=403, detail="Sem permissão para aprovar este usuário")

    target.approval_status = "approved"
    target.is_active = True
    db.add(target)
    db.commit()
    db.refresh(target)

    write_audit_log(
        db,
        user_id=requester.id,
        user_email=requester.email,
        tenant_id=requester.tenant_id,
        action="admin_user_approved",
        method="POST",
        endpoint=f"/api/admin/users/{user_id}/approve",
        status=200,
        details={"target_user_id": target.id},
    )

    tenant = db.query(Tenant).filter(Tenant.id == target.tenant_id).first()
    send_approved_user_email(target, tenant)
    return serialize_user(target, tenant)


@router.post("/{user_id}/reject")
def reject_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    requester = get_requester(db, current_user)
    ensure_user_admin(requester)

    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    if not can_manage_target(requester, target):
        raise HTTPException(status_code=403, detail="Sem permissão para rejeitar este usuário")

    target.approval_status = "rejected"
    target.is_active = False
    db.add(target)
    db.commit()
    db.refresh(target)

    write_audit_log(
        db,
        user_id=requester.id,
        user_email=requester.email,
        tenant_id=requester.tenant_id,
        action="admin_user_rejected",
        method="POST",
        endpoint=f"/api/admin/users/{user_id}/reject",
        status=200,
        details={"target_user_id": target.id},
    )

    tenant = db.query(Tenant).filter(Tenant.id == target.tenant_id).first()
    send_rejected_user_email(target, tenant)
    return serialize_user(target, tenant)


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    requester = get_requester(db, current_user)
    ensure_user_admin(requester)

    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    if target.id == requester.id:
        raise HTTPException(status_code=400, detail="Você não pode excluir o próprio usuário")

    if not can_manage_target(requester, target):
        raise HTTPException(status_code=403, detail="Sem permissão para excluir este usuário")

    db.delete(target)
    db.commit()

    write_audit_log(
        db,
        user_id=requester.id,
        user_email=requester.email,
        tenant_id=requester.tenant_id,
        action="admin_user_deleted",
        method="DELETE",
        endpoint=f"/api/admin/users/{user_id}",
        status=200,
        details={"target_user_id": user_id},
    )

    return {"message": "Usuário removido com sucesso"}
