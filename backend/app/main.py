from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from contextlib import asynccontextmanager
from pathlib import Path
import re
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from starlette_csrf import CSRFMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.config import settings
from app.database import init_db
from app.routes import (
    auth, users, devices, distributions, 
    defects, returns, approvals, operators,
    notifications, reports, dashboard, change_requests,
    external_inventory
)
from app.middleware.error_handler import add_exception_handlers
from app.middleware.auth_middleware import get_current_user, require_admin
from app.core.rate_limiter import limiter
from app.core.audit import audit_logger


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Apply standard security headers to all responses."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        if settings.ENVIRONMENT == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        docs_paths = {"/docs", "/redoc", "/openapi.json", "/docs/oauth2-redirect"}
        if request.url.path not in docs_paths:
            response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response


class HttpsEnforcementMiddleware(BaseHTTPMiddleware):
    """Redirect plaintext HTTP requests to HTTPS when explicitly enabled."""

    async def dispatch(self, request: Request, call_next):
        if settings.ENFORCE_HTTPS:
            forwarded_proto = request.headers.get("x-forwarded-proto", request.url.scheme)
            if forwarded_proto.lower() != "https":
                https_url = request.url.replace(scheme="https")
                return RedirectResponse(url=str(https_url), status_code=307)

        return await call_next(request)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    # Startup - initialize SQLite database
    await init_db()
    
    # Seed initial data
    from app.services.seed_service import seed_initial_data
    await seed_initial_data()
    
    yield
    
    # Shutdown - nothing to clean up for SQLite


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Backend API for Distribution Management System",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

uploads_root = Path(__file__).resolve().parents[1] / "uploads"
uploads_root.mkdir(parents=True, exist_ok=True)

app.add_middleware(
    CSRFMiddleware,
    secret=settings.SECRET_KEY,
    cookie_name=settings.CSRF_COOKIE_NAME,
    cookie_secure=settings.CSRF_COOKIE_SECURE,
    cookie_samesite="strict",
    sensitive_cookies={"access_token", "refresh_token"},
    exempt_urls=[re.compile(r"^/api/auth/login$")],
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Requested-With", "X-CSRFToken"],
    expose_headers=["Content-Disposition"],
    max_age=600,
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(HttpsEnforcementMiddleware)

# Add exception handlers
add_exception_handlers(app)

# Include routers
app.include_router(auth.router, prefix=f"{settings.API_V1_PREFIX}/auth", tags=["Authentication"])
app.include_router(users.router, prefix=f"{settings.API_V1_PREFIX}/users", tags=["Users"])
app.include_router(devices.router, prefix=f"{settings.API_V1_PREFIX}/devices", tags=["Devices"])
app.include_router(distributions.router, prefix=f"{settings.API_V1_PREFIX}/distributions", tags=["Distributions"])
app.include_router(defects.router, prefix=f"{settings.API_V1_PREFIX}/defects", tags=["Defects"])
app.include_router(returns.router, prefix=f"{settings.API_V1_PREFIX}/returns", tags=["Returns"])
app.include_router(approvals.router, prefix=f"{settings.API_V1_PREFIX}/approvals", tags=["Approvals"])
app.include_router(operators.router, prefix=f"{settings.API_V1_PREFIX}/operators", tags=["Operators"])
app.include_router(notifications.router, prefix=f"{settings.API_V1_PREFIX}/notifications", tags=["Notifications"])
app.include_router(reports.router, prefix=f"{settings.API_V1_PREFIX}/reports", tags=["Reports"])
app.include_router(dashboard.router, prefix=f"{settings.API_V1_PREFIX}/dashboard", tags=["Dashboard"])
app.include_router(change_requests.router, prefix=f"{settings.API_V1_PREFIX}/change-requests", tags=["Change Requests"])
app.include_router(external_inventory.router, prefix=f"{settings.API_V1_PREFIX}/external-inventory", tags=["External Inventory"])


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint"""
    return {
        "message": "Distribution Management System API",
        "version": settings.APP_VERSION,
        "docs": "/docs" if settings.DEBUG else None
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.get(f"{settings.API_V1_PREFIX}/uploads/{{file_path:path}}", tags=["Uploads"])
async def serve_upload(file_path: str, current_user: dict = Depends(get_current_user)):
    """Serve uploaded files only to authenticated users."""
    resolved_root = uploads_root.resolve()
    safe_path = (resolved_root / file_path).resolve()

    if resolved_root not in safe_path.parents and safe_path != resolved_root:
        raise HTTPException(status_code=403, detail="Access denied")
    if not safe_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(path=str(safe_path))


@app.post("/reset-and-seed", tags=["Seed"], dependencies=[Depends(require_admin)])
async def reset_and_seed_endpoint(request: Request, current_user: dict = Depends(get_current_user)):
    """Reset database and seed with fresh user accounts - ADMIN ONLY"""
    if settings.ENVIRONMENT != "development":
        raise HTTPException(status_code=403, detail="Not allowed in production")

    audit_logger.critical(
        "DB_RESET | user_id=%s | email=%s | ip=%s",
        current_user.get("id"),
        current_user.get("email"),
        request.client.host if request.client else "unknown",
    )

    from app.services.seed_service import reset_and_seed
    result = await reset_and_seed()
    return {"success": True, **result}

