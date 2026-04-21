from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.models import Event

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/events")
def list_events(db: Session = Depends(get_db)):
    return db.query(Event).order_by(Event.id.desc()).limit(100).all()