from pathlib import Path
import secrets

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles

from app.api.routes import account, admin_audit, admin_tenants, admin_users, assets, auth, billing, events, health, inference, tenants
from app.core.config import settings

app = FastAPI(
    title="Vale Vision API",
    version="0.1.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
docs_security = HTTPBasic()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(account.router, prefix="/api")
app.include_router(assets.router, prefix="/api")
app.include_router(admin_audit.router, prefix="/api")
app.include_router(admin_tenants.router, prefix="/api")
app.include_router(admin_users.router, prefix="/api")
app.include_router(billing.router, prefix="/api")
app.include_router(tenants.router, prefix="/api")
app.include_router(events.router, prefix="/api")
app.include_router(inference.router, prefix="/api")

base_dir = Path(__file__).resolve().parent
static_dir = base_dir / "static"
frontend_dir = base_dir / "web"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


def authenticate_docs(credentials: HTTPBasicCredentials = Depends(docs_security)) -> None:
    if not settings.docs_enabled:
        raise HTTPException(status_code=404, detail="Not found")

    if not settings.docs_user or not settings.docs_password:
        raise HTTPException(status_code=503, detail="Docs credentials not configured")

    correct_username = secrets.compare_digest(credentials.username, settings.docs_user)
    correct_password = secrets.compare_digest(credentials.password, settings.docs_password)

    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Basic"},
        )


@app.get("/openapi.json", include_in_schema=False)
def openapi_endpoint(_: None = Depends(authenticate_docs)):
    return JSONResponse(app.openapi())


@app.get("/docs", include_in_schema=False)
def docs_endpoint(_: None = Depends(authenticate_docs)):
    return get_swagger_ui_html(openapi_url="/openapi.json", title="Vale Vision API Docs")


@app.get("/", include_in_schema=False)
def frontend_index():
    index_file = frontend_dir / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Frontend build not found")
    return FileResponse(index_file)


@app.get("/{full_path:path}", include_in_schema=False)
def frontend_app(full_path: str):
    if full_path.startswith(("api/", "docs", "redoc", "openapi.json", "static/")):
        raise HTTPException(status_code=404, detail="Not found")

    requested_path = (frontend_dir / full_path).resolve()
    if requested_path.is_file() and frontend_dir.resolve() in requested_path.parents:
        return FileResponse(requested_path)

    index_file = frontend_dir / "index.html"
    if index_file.exists():
        return FileResponse(index_file)

    raise HTTPException(status_code=404, detail="Frontend build not found")
