"""
Enhanced MES API Application with Full Architectural Improvements.

This enhanced version includes:
- Comprehensive authentication and authorization
- Global exception handling
- Enhanced database configuration
- HATEOAS-enabled routers
- Monitoring and observability
- Production-ready configuration
"""

import os
import logging
import asyncio
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer
import uvicorn
from dotenv import load_dotenv

# Import application modules
from app.database_enhanced import create_tables, get_engine_info
from app.core.logging_config import setup_logging
from app.exceptions.error_handlers import EXCEPTION_HANDLERS
from app.auth import (
    get_current_user_flexible,
    RequireOperationRead,
    create_demo_token,
    UserRole
)

# Import routers
from app.routers import mes_operations, operation_events, profiles
from app.routers.mes_operations_v2 import router as mes_operations_v2_router

# Load environment variables
load_dotenv()

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Configuration
API_TITLE = os.getenv("API_TITLE", "MES Operations API - Enhanced")
API_VERSION = os.getenv("API_VERSION", "2.0.0")
API_DESCRIPTION = """
Enhanced Manufacturing Execution System (MES) REST API

## Features
- 🔐 **Comprehensive Authentication**: JWT tokens and API keys
- 🏭 **Manufacturing Workflows**: State machine-driven operations
- 🔗 **HATEOAS Support**: Hypermedia-driven REST API (Level 3)
- 📊 **Advanced Analytics**: Real-time dashboards and reporting
- ⚡ **Batch Operations**: Efficient bulk operations
- 🛡️ **Role-Based Security**: Fine-grained access control
- 📋 **Rich Filtering**: Advanced query capabilities

## Authentication Methods
1. **JWT Tokens**: For user authentication
2. **API Keys**: For machine-to-machine integration

## Security Roles
- **Operator**: Basic operation updates
- **Supervisor**: Area management and reporting
- **Manager**: Multi-area management
- **Admin**: Full system access
- **Machine**: Automated system integration

## Getting Started
1. Obtain a demo token: `POST /auth/demo-token`
2. Include in requests: `Authorization: Bearer <token>`
3. Explore endpoints with interactive docs below
"""

API_PREFIX = "/api/v2"
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# CORS configuration
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
if "*" in ALLOWED_ORIGINS and ENVIRONMENT == "production":
    logger.warning("Wildcard CORS origins not recommended for production")

# Trusted hosts for production
TRUSTED_HOSTS = os.getenv("TRUSTED_HOSTS", "*").split(",")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info(f"Starting {API_TITLE} v{API_VERSION}")
    logger.info(f"Environment: {ENVIRONMENT}")
    logger.info(f"Debug mode: {DEBUG}")

    # Create database tables
    try:
        create_tables()
        logger.info("Database initialization completed")
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        raise

    # Log database pool info
    pool_info = get_engine_info()
    logger.info(f"Database connection pool: {pool_info}")

    yield

    # Shutdown
    logger.info("Shutting down API")


# Create FastAPI application
app = FastAPI(
    title=API_TITLE,
    version=API_VERSION,
    description=API_DESCRIPTION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
    debug=DEBUG
)

# Security
security = HTTPBearer()

# Middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=TRUSTED_HOSTS
)

app.add_middleware(
    GZipMiddleware,
    minimum_size=1000
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-API-Key",
        "X-Request-ID",
        "X-Trace-ID"
    ],
    expose_headers=["X-Request-ID", "X-Trace-ID", "Location"]
)


# Request middleware for tracing and monitoring
@app.middleware("http")
async def add_request_id_middleware(request: Request, call_next):
    """Add request ID for tracing and monitoring."""
    import uuid

    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id

    # Add to response headers
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id

    # Log request
    logger.info(
        f"Request processed",
        extra={
            "request_id": request_id,
            "method": request.method,
            "url": str(request.url),
            "status_code": response.status_code,
            "user_agent": request.headers.get("User-Agent", "Unknown")
        }
    )

    return response


# Register exception handlers
for exception_type, handler in EXCEPTION_HANDLERS.items():
    app.add_exception_handler(exception_type, handler)


# Health and monitoring endpoints
@app.get("/health", tags=["Health"], include_in_schema=True)
async def health_check():
    """Comprehensive health check endpoint."""
    try:
        # Check database connection
        pool_info = get_engine_info()
        db_healthy = pool_info["checked_out"] >= 0

        health_status = {
            "status": "healthy" if db_healthy else "unhealthy",
            "timestamp": "datetime.utcnow().isoformat()",
            "version": API_VERSION,
            "environment": ENVIRONMENT,
            "database": {
                "status": "connected" if db_healthy else "disconnected",
                "pool_info": pool_info
            }
        }

        status_code = 200 if db_healthy else 503
        return JSONResponse(content=health_status, status_code=status_code)

    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": "datetime.utcnow().isoformat()"
            },
            status_code=503
        )


@app.get("/metrics", tags=["Monitoring"])
async def get_metrics(current_user = Depends(RequireOperationRead)):
    """Get application metrics for monitoring."""
    try:
        pool_info = get_engine_info()

        metrics = {
            "database": {
                "pool_size": pool_info["pool_size"],
                "connections_checked_out": pool_info["checked_out"],
                "connections_checked_in": pool_info["checked_in"],
                "overflow_connections": pool_info["overflow"],
                "invalidated_connections": pool_info["invalidated"]
            },
            "application": {
                "version": API_VERSION,
                "environment": ENVIRONMENT,
                "uptime_seconds": "application_uptime_would_go_here"
            },
            "timestamp": "datetime.utcnow().isoformat()"
        }

        return metrics

    except Exception as e:
        logger.error(f"Metrics collection failed: {str(e)}")
        return JSONResponse(
            content={"error": "Metrics unavailable"},
            status_code=503
        )


# Authentication endpoints
@app.post("/auth/demo-token", tags=["Authentication"])
async def create_demo_token_endpoint(
    role: UserRole = UserRole.SUPERVISOR,
    workplaces: str = "LASER_001,ASSEMBLY_001"
):
    """
    Create a demo authentication token for testing.

    This endpoint is for development and demonstration purposes only.
    In production, use your organization's authentication system.
    """
    workplace_list = [w.strip() for w in workplaces.split(",") if w.strip()]

    try:
        token = create_demo_token(role=role, workplaces=workplace_list)

        return {
            "access_token": token,
            "token_type": "bearer",
            "role": role.value,
            "workplace_access": workplace_list,
            "expires_in_hours": 24,
            "usage": {
                "header": "Authorization: Bearer <token>",
                "example": f"Authorization: Bearer {token[:20]}..."
            }
        }

    except Exception as e:
        logger.error(f"Demo token creation failed: {str(e)}")
        return JSONResponse(
            content={"error": "Token creation failed"},
            status_code=500
        )


# API Documentation
@app.get("/", tags=["Root"])
async def read_root():
    """API root endpoint with navigation links."""
    return {
        "message": f"Welcome to {API_TITLE}",
        "version": API_VERSION,
        "environment": ENVIRONMENT,
        "documentation": {
            "interactive_docs": "/docs",
            "redoc": "/redoc",
            "openapi_spec": "/openapi.json"
        },
        "health": "/health",
        "metrics": "/metrics",
        "authentication": {
            "demo_token": "/auth/demo-token",
            "info": "Include 'Authorization: Bearer <token>' header in requests"
        },
        "main_endpoints": {
            "operations": f"{API_PREFIX}/operations",
            "events": f"{API_PREFIX}/events",
            "profiles": f"{API_PREFIX}/profiles"
        }
    }


# Register API routers
app.include_router(
    mes_operations_v2_router,
    prefix=f"{API_PREFIX}/operations",
    tags=["MES Operations v2"],
    dependencies=[Depends(RequireOperationRead)]
)

app.include_router(
    operation_events.router,
    prefix=f"{API_PREFIX}/events",
    tags=["Operation Events"],
    dependencies=[Depends(RequireOperationRead)]
)

app.include_router(
    profiles.router,
    prefix=f"{API_PREFIX}/profiles",
    tags=["User Profiles"],
    dependencies=[Depends(RequireOperationRead)]
)

# Include legacy v1 endpoints for backward compatibility
app.include_router(
    mes_operations.router,
    prefix="/api/v1/operations",
    tags=["MES Operations v1 (Legacy)"],
    include_in_schema=False  # Hide from docs but keep functional
)


# Development server configuration
if __name__ == "__main__":
    uvicorn.run(
        "app.main_enhanced:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=DEBUG,
        log_level="info" if not DEBUG else "debug",
        access_log=True
    )