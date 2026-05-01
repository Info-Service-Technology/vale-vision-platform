from math import ceil
from datetime import datetime, timezone
import boto3
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, or_, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_current_user
from app.db.session import SessionLocal
from app.models.models import Event, Tenant
from app.services.audit import write_audit_log

router = APIRouter(tags=["events"])


class ResolveEventPayload(BaseModel):
    reason: str | None = None


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def apply_tenant_scope(query, user: dict):
    role = user.get("role")
    tenant_id = user.get("tenant_id")

    if role == "super-admin":
        return query

    return query.filter(Event.tenant_id == tenant_id)


def ensure_user_can_resolve(user: dict, db: Session):
    if user.get("role") == "viewer":
        raise HTTPException(
            status_code=403,
            detail="Usuário sem permissão para resolver monitoramentos manualmente",
        )

    if user.get("role") == "super-admin":
        return

    tenant_id = user.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Usuário sem tenant vinculado")

    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado")

    if (tenant.billing_status or "active") in {"suspended_read_only", "suspended_full", "terminated"}:
        raise HTTPException(
            status_code=403,
            detail="Este tenant está com restrição operacional por billing",
        )


def apply_material_filter(query, material: str | None):
    if not material or material == "all":
        return query

    material = material.lower().strip()

    return query.filter(
        or_(
            Event.s3_key_raw.ilike(f"%/{material}_%"),
            Event.s3_key_raw.ilike(f"%/{material}-%"),
            Event.file_path.ilike(f"{material}_%"),
            Event.file_path.ilike(f"{material}-%"),
        )
    )

def serialize_event(event: Event):
    return {
        "id": event.id,
        "tenant_id": event.tenant_id,
        "camera_id": event.camera_id,
        "container_id": event.container_id,
        "data_ref": event.data_ref.isoformat() if event.data_ref else None,
        "hora_ref": str(event.hora_ref) if event.hora_ref else None,
        "file_path": event.file_path,
        "debug_path": event.debug_path,
        "status": event.status,
        "fill_percent": event.fill_percent,
        "materiais_detectados": event.materiais_detectados,
        "contaminantes_detectados": event.contaminantes_detectados,
        "alerta_contaminacao": event.alerta_contaminacao,
        "tipo_contaminacao": event.tipo_contaminacao,
        "cacamba_esperada": event.cacamba_esperada,
        "material_esperado": event.material_esperado,
        "s3_bucket": event.s3_bucket,
        "s3_key_raw": event.s3_key_raw,
        "s3_key_debug": event.s3_key_debug,
        "image_received_at": event.image_received_at.isoformat()
        if event.image_received_at
        else None,
        "processing_status": event.processing_status,
    }


@router.get("/events")
def list_events(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    container: str | None = None,
    search: str | None = None,
    active_only: bool = True,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    query = db.query(Event)
    query = apply_tenant_scope(query, user)

    if active_only:
        query = query.filter(Event.status != "resolved")

    query = apply_material_filter(query, container)

    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(
                Event.file_path.like(like),
                Event.status.like(like),
                Event.materiais_detectados.like(like),
                Event.contaminantes_detectados.like(like),
                Event.tipo_contaminacao.like(like),
                Event.cacamba_esperada.like(like),
                Event.material_esperado.like(like),
            )
        )

    total = query.count()

    rows = (
        query.order_by(Event.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "items": [serialize_event(row) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": ceil(total / page_size) if page_size else 0,
    }


@router.get("/events/metrics")
def get_events_metrics(
    container: str | None = None,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    query = db.query(Event)
    query = apply_tenant_scope(query, user)

    query = apply_material_filter(query, container)

    total_events = query.count()
    ok_events = query.filter(Event.status == "ok").count()
    active_contaminations = query.filter(Event.alerta_contaminacao == 1).count()
    avg_fill = query.with_entities(func.avg(Event.fill_percent)).scalar() or 0
    over_threshold = query.filter(Event.fill_percent >= 75).count()
    last_event = query.order_by(Event.id.desc()).first()

    resolved_count = query.filter(Event.status == "resolved").count()

    backlog = query.filter(Event.status != "resolved").count()

    resolution_rate = (
        (resolved_count / total_events) * 100
        if total_events > 0
        else 0
    )

    avg_resolution_minutes = (
        query.filter(
            Event.status == "resolved",
            Event.resolved_at.isnot(None),
            Event.created_at.isnot(None),
        )
        .with_entities(
            func.avg(
                func.timestampdiff(
                    text("MINUTE"),
                    Event.created_at,
                    Event.resolved_at,
                )
            )
        )
        .scalar()
        or 0
    )

    return {
        "total_events": total_events,
        "ok_events": ok_events,
        "active_contaminations": active_contaminations,
        "avg_fill_percent": float(avg_fill),
        "over_threshold": over_threshold,
        "system_online": True,
        "resolved_count": resolved_count,
        "backlog": backlog,
        "resolution_rate": float(resolution_rate),
        "avg_resolution_minutes": float(avg_resolution_minutes),
        "last_frame_at": last_event.image_received_at.isoformat()
        if last_event and last_event.image_received_at
        else None,
    }


@router.get("/events/{event_id}/image-url")
def get_event_image_url(
    event_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    query = db.query(Event).filter(Event.id == event_id)
    query = apply_tenant_scope(query, user)

    event = query.first()

    if not event:
        raise HTTPException(status_code=404, detail="Evento não encontrado")

    if not event.s3_bucket or not event.s3_key_raw:
        raise HTTPException(
            status_code=404,
            detail="Imagem S3 não encontrada para este evento",
        )

    s3 = boto3.client("s3", region_name=settings.aws_region)

    url = s3.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": event.s3_bucket,
            "Key": event.s3_key_raw,
        },
        ExpiresIn=600,
    )

    return {"url": url}


@router.patch("/events/{event_id}/resolve")
def resolve_event(
    event_id: int,
    payload: ResolveEventPayload,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    ensure_user_can_resolve(user, db)

    query = db.query(Event).filter(Event.id == event_id)
    query = apply_tenant_scope(query, user)

    event = query.first()

    if not event:
        raise HTTPException(status_code=404, detail="Evento não encontrado")

    event.status = "resolved"
    event.alerta_contaminacao = 0
    event.resolved_at = datetime.now(timezone.utc).replace(tzinfo=None)
    event.resolved_by = user.get("user_id")
    event.resolved_reason = payload.reason or "Resolvido manualmente pela operação"

    db.commit()

    write_audit_log(
        db,
        user_id=user.get("user_id"),
        user_email=user.get("email"),
        tenant_id=user.get("tenant_id"),
        action="monitoring_resolved",
        method="PATCH",
        endpoint=f"/api/events/{event_id}/resolve",
        status=200,
        details={"event_id": event_id, "reason": event.resolved_reason},
    )

    return {
        "status": "ok",
        "message": "Evento removido da lista",
        "event_id": event_id,
    }

@router.get("/events/resolved")
def list_resolved_events(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: str | None = None,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    query = db.query(Event)
    query = apply_tenant_scope(query, user)

    query = query.filter(Event.status == "resolved")

    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(
                Event.file_path.like(like),
                Event.s3_key_raw.like(like),
                Event.resolved_reason.like(like),
                Event.materiais_detectados.like(like),
                Event.contaminantes_detectados.like(like),
            )
        )

    total = query.count()

    rows = (
        query.order_by(Event.resolved_at.desc(), Event.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "items": [serialize_event(row) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": ceil(total / page_size) if page_size else 0,
    }
