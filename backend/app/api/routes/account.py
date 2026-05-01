from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import SessionLocal
from app.models.models import Tenant, User
from app.services.audit import write_audit_log
from app.services.uploads import save_image_upload

router = APIRouter(prefix="/account", tags=["account"])


class UpdateProfilePayload(BaseModel):
    name: str | None = None
    phone: str | None = None
    about: str | None = None
    avatar_url: str | None = None


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/me")
def get_me(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user = db.query(User).filter(User.id == current_user.get("user_id")).first()

    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    tenant = None
    if user.tenant_id:
        tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()

    return {
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "approval_status": user.approval_status,
            "is_active": user.is_active,
            "avatar_url": user.avatar_url,
            "phone": user.phone,
            "about": user.about,
            "tenant_id": user.tenant_id,
            "tenant_slug": tenant.slug if tenant else None,
            "tenant_name": tenant.name if tenant else None,
        },
        "tenant": (
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
            if tenant
            else None
        ),
    }


@router.put("/me")
def update_me(
    payload: UpdateProfilePayload,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user = db.query(User).filter(User.id == current_user.get("user_id")).first()

    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    if payload.name is not None:
        user.name = payload.name.strip()
    if payload.phone is not None:
        user.phone = payload.phone.strip()
    if payload.about is not None:
        user.about = payload.about.strip()
    if payload.avatar_url is not None:
        user.avatar_url = payload.avatar_url.strip()

    db.add(user)
    db.commit()
    db.refresh(user)

    write_audit_log(
        db,
        user_id=user.id,
        user_email=user.email,
        tenant_id=user.tenant_id,
        action="account_profile_updated",
        method="PUT",
        endpoint="/api/account/me",
        status=200,
        details={"user_id": user.id},
    )

    return {"message": "Perfil atualizado com sucesso"}


@router.post("/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user = db.query(User).filter(User.id == current_user.get("user_id")).first()

    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    avatar_url = await save_image_upload(file, "avatars")
    user.avatar_url = avatar_url
    db.add(user)
    db.commit()
    db.refresh(user)

    write_audit_log(
        db,
        user_id=user.id,
        user_email=user.email,
        tenant_id=user.tenant_id,
        action="account_avatar_uploaded",
        method="POST",
        endpoint="/api/account/avatar",
        status=200,
        details={"user_id": user.id, "avatar_url": avatar_url},
    )

    return {"avatar_url": avatar_url}
