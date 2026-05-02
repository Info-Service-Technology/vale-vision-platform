from sqlalchemy import Boolean, Date, DateTime, Float, Integer, Numeric, String, Text, Time
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    scope_type: Mapped[str | None] = mapped_column(String(64))
    scope_value: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool | None] = mapped_column(Boolean)
    company_logo_url: Mapped[str | None] = mapped_column(String(512))
    billing_status: Mapped[str | None] = mapped_column(String(64))
    billing_due_date: Mapped[DateTime | None] = mapped_column(DateTime)
    billing_grace_until: Mapped[DateTime | None] = mapped_column(DateTime)
    billing_suspended_at: Mapped[DateTime | None] = mapped_column(DateTime)
    billing_contact_email: Mapped[str | None] = mapped_column(String(255))
    billing_notes: Mapped[str | None] = mapped_column(Text)
    payment_method: Mapped[str | None] = mapped_column(String(64))
    contract_type: Mapped[str | None] = mapped_column(String(64))
    billing_amount: Mapped[float | None] = mapped_column(Numeric(10, 2))
    billing_currency: Mapped[str | None] = mapped_column(String(16))
    billing_cycle: Mapped[str | None] = mapped_column(String(32))
    plan_slug: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[DateTime | None] = mapped_column(DateTime)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int | None] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(64), nullable=False)
    approval_status: Mapped[str | None] = mapped_column(String(64))
    is_active: Mapped[bool | None] = mapped_column(Boolean)
    avatar_url: Mapped[str | None] = mapped_column(String(512))
    phone: Mapped[str | None] = mapped_column(String(64))
    about: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[DateTime | None] = mapped_column(DateTime)


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int | None] = mapped_column(Integer)
    camera_id: Mapped[int | None] = mapped_column(Integer)
    container_id: Mapped[int | None] = mapped_column(Integer)
    data_ref: Mapped[Date | None] = mapped_column(Date)
    hora_ref: Mapped[Time | None] = mapped_column(Time)
    file_path: Mapped[str | None] = mapped_column(String(512))
    debug_path: Mapped[str | None] = mapped_column(String(512))
    status: Mapped[str | None] = mapped_column(String(64))
    fill_percent: Mapped[float | None] = mapped_column(Float)
    materiais_detectados: Mapped[str | None] = mapped_column(Text)
    contaminantes_detectados: Mapped[str | None] = mapped_column(Text)
    alerta_contaminacao: Mapped[int | None] = mapped_column(Integer)
    tipo_contaminacao: Mapped[str | None] = mapped_column(String(255))
    cacamba_esperada: Mapped[str | None] = mapped_column(String(255))
    material_esperado: Mapped[str | None] = mapped_column(String(255))
    s3_bucket: Mapped[str | None] = mapped_column(String(255))
    s3_key_raw: Mapped[str | None] = mapped_column(String(1024))
    s3_key_debug: Mapped[str | None] = mapped_column(String(1024))
    image_received_at: Mapped[DateTime | None] = mapped_column(DateTime)
    processing_status: Mapped[str | None] = mapped_column(String(64))
    resolved_at: Mapped[DateTime | None] = mapped_column(DateTime)
    resolved_by: Mapped[int | None] = mapped_column(Integer)
    resolved_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[DateTime | None] = mapped_column(DateTime)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(Integer)
    user_email: Mapped[str | None] = mapped_column(String(255))
    tenant_id: Mapped[int | None] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    method: Mapped[str | None] = mapped_column(String(16))
    endpoint: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[int | None] = mapped_column(Integer)
    details: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[DateTime | None] = mapped_column(DateTime)


class TenantDomain(Base):
    __tablename__ = "tenant_domains"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(Integer, nullable=False)
    domain: Mapped[str] = mapped_column(String(255), nullable=False)
    is_verified: Mapped[bool | None] = mapped_column(Boolean)
    is_primary: Mapped[bool | None] = mapped_column(Boolean)
    is_active: Mapped[bool | None] = mapped_column(Boolean)
    match_mode: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[DateTime | None] = mapped_column(DateTime)


class BillingEvent(Base):
    __tablename__ = "billing_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str | None] = mapped_column(String(64))
    previous_status: Mapped[str | None] = mapped_column(String(64))
    next_status: Mapped[str | None] = mapped_column(String(64))
    message: Mapped[str | None] = mapped_column(Text)
    actor_user_id: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[DateTime | None] = mapped_column(DateTime)
