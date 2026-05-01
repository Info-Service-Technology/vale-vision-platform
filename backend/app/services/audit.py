from datetime import datetime, timezone
import json

from sqlalchemy.orm import Session

from app.models.models import AuditLog


def write_audit_log(
    db: Session,
    *,
    user_id: int | None,
    user_email: str | None,
    tenant_id: int | None,
    action: str,
    method: str,
    endpoint: str,
    status: int,
    details: dict | None = None,
):
    log = AuditLog(
        user_id=user_id,
        user_email=user_email,
        tenant_id=tenant_id,
        action=action,
        method=method,
        endpoint=endpoint,
        status=status,
        details=json.dumps(details or {}, ensure_ascii=False),
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log
