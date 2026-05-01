from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import SessionLocal
from app.models.models import AuditLog, Tenant, User

router = APIRouter(prefix="/admin/audit", tags=["admin-audit"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def serialize_log(log: AuditLog, tenant_name: str | None):
    return {
        "id": log.id,
        "user_id": log.user_id,
        "user_email": log.user_email,
        "tenant_id": log.tenant_id,
        "tenant": tenant_name,
        "action": log.action,
        "method": log.method,
        "endpoint": log.endpoint,
        "status": log.status,
        "details": log.details,
        "created_at": log.created_at.isoformat() if log.created_at else None,
    }


@router.get("/logs")
def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user = db.query(User).filter(User.id == current_user.get("user_id")).first()
    if not user or user.role != "super-admin":
        raise HTTPException(status_code=403, detail="Acesso à auditoria administrativa negado")

    query = db.query(AuditLog).order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
    total = query.count()
    rows = query.offset((page - 1) * page_size).limit(page_size).all()

    tenant_map = {tenant.id: tenant.name for tenant in db.query(Tenant).all()}

    return {
        "items": [serialize_log(log, tenant_map.get(log.tenant_id)) for log in rows],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "pages": (total + page_size - 1) // page_size,
            "has_prev": page > 1,
            "has_next": page * page_size < total,
        },
    }
