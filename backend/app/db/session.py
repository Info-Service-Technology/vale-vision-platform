from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

DATABASE_URL = (
    f"mysql+pymysql://{settings.mysql_user}:{settings.mysql_password}"
    f"@{settings.mysql_host}:{settings.mysql_port}/{settings.mysql_db}"
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
