from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    create_access_token,
    decode_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.db.session import SessionLocal
from app.models.models import Tenant, User
from app.services.email import (
    email_is_enabled,
    build_reset_password_url,
    send_approval_request_email,
    send_password_reset_email,
    send_pending_approval_email,
)

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    tenant_slug: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    tenant_slug: str | None = None


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def normalize_tenant_slug(value: str | None) -> str:
    return (value or "").strip().lower()


def get_tenant_by_slug(db: Session, tenant_slug: str) -> Tenant:
    tenant = db.query(Tenant).filter(Tenant.slug == tenant_slug).first()

    if not tenant:
        raise HTTPException(status_code=404, detail="Mineradora/tenant não encontrado")

    return tenant


def build_user_response(user: User, tenant: Tenant | None):
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "approval_status": user.approval_status,
        "is_active": user.is_active,
        "tenant_id": user.tenant_id,
        "tenant_slug": tenant.slug if tenant else None,
        "tenant_name": tenant.name if tenant else None,
    }


def get_approval_recipients(db: Session, tenant_id: int | None) -> list[str]:
    query = db.query(User).filter(
        User.is_active == True,  # noqa: E712
        User.approval_status == "approved",
    )

    super_admins = query.filter(User.role == "super-admin").all()
    emails = {user.email for user in super_admins if user.email}

    if tenant_id is not None:
        tenant_admins = (
            db.query(User)
            .filter(
                User.is_active == True,  # noqa: E712
                User.approval_status == "approved",
                User.role == "admin-tenant",
                User.tenant_id == tenant_id,
            )
            .all()
        )
        emails.update(user.email for user in tenant_admins if user.email)

    if not emails and settings.email_support_address:
        emails.add(settings.email_support_address)

    return sorted(emails)


@router.post("/register")
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    tenant_slug = normalize_tenant_slug(payload.tenant_slug)

    if not tenant_slug:
        raise HTTPException(status_code=400, detail="Informe a mineradora/tenant")

    existing = db.query(User).filter(User.email == payload.email).first()

    if existing:
        raise HTTPException(status_code=400, detail="Email já cadastrado")

    tenant = get_tenant_by_slug(db, tenant_slug)

    user = User(
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role="viewer",
        tenant_id=tenant.id,
        approval_status="pending",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    send_pending_approval_email(user, tenant)

    for approver_email in get_approval_recipients(db, tenant.id):
        send_approval_request_email(
            approver_email=approver_email,
            pending_user=user,
            tenant=tenant,
        )

    return {
        "message": "Usuário criado com sucesso e aguardando aprovação",
        "user": build_user_response(user, tenant),
    }


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    if user.is_active is False:
        raise HTTPException(status_code=403, detail="Usuário inativo")

    if (user.approval_status or "approved") != "approved":
        raise HTTPException(
            status_code=403,
            detail="Usuário pendente de aprovação para acessar a plataforma",
        )

    tenant = None
    if user.tenant_id:
        tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()

    tenant_slug = normalize_tenant_slug(payload.tenant_slug)

    if tenant_slug:
        requested_tenant = get_tenant_by_slug(db, tenant_slug)

        if user.tenant_id != requested_tenant.id:
            raise HTTPException(
                status_code=403,
                detail="Usuário sem acesso à mineradora selecionada",
            )

        tenant = requested_tenant

    token = create_access_token(
        subject=str(user.id),
        claims={
            "user_id": user.id,
            "email": user.email,
            "role": user.role,
            "approval_status": user.approval_status,
            "is_active": user.is_active,
            "tenant_id": user.tenant_id,
            "tenant_slug": tenant.slug if tenant else None,
        },
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": build_user_response(user, tenant),
    }


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    debug_payload: dict[str, str] = {}

    if user:
        tenant = None
        if user.tenant_id:
            tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()

        reset_token = create_access_token(
            subject=payload.email,
            claims={
                "purpose": "password-reset",
                "email": payload.email,
            },
            expires_minutes=settings.password_reset_token_expire_minutes,
        )

        send_password_reset_email(user, reset_token, tenant)

        if not email_is_enabled() and settings.email_debug_return_tokens:
            debug_payload = {
                "reset_token": reset_token,
                "reset_url": build_reset_password_url(reset_token),
            }

    return {
        "message": "Se o e-mail existir, enviaremos instruções.",
        **debug_payload,
    }


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    token_payload = decode_token(payload.token)

    if token_payload.get("purpose") != "password-reset":
        raise HTTPException(status_code=400, detail="Token de recuperação inválido")

    email = token_payload.get("email")
    user = db.query(User).filter(User.email == email).first()

    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    user.password_hash = hash_password(payload.password)
    db.add(user)
    db.commit()

    return {"message": "Senha alterada com sucesso"}


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user = db.query(User).filter(User.id == current_user.get("user_id")).first()

    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Senha atual inválida")

    user.password_hash = hash_password(payload.new_password)
    db.add(user)
    db.commit()

    return {"message": "Senha alterada com sucesso"}
