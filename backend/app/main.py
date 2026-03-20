from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from pathlib import Path

from app.config import settings
from app.database import init_db
from app.routes import (
    auth, users, devices, distributions, 
    defects, returns, approvals, operators,
    notifications, reports, dashboard, change_requests,
    external_inventory
)
from app.middleware.error_handler import add_exception_handlers


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
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

uploads_root = Path(__file__).resolve().parents[1] / "uploads"
uploads_root.mkdir(parents=True, exist_ok=True)
app.mount(f"{settings.API_V1_PREFIX}/uploads", StaticFiles(directory=str(uploads_root)), name="uploads")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
        "docs": "/docs"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.post("/reset-and-seed", tags=["Seed"])
async def reset_and_seed_endpoint():
    """Reset database and seed with fresh user accounts"""
    from app.services.seed_service import reset_and_seed
    result = await reset_and_seed()
    return {"success": True, **result}

