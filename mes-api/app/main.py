from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
import os
import logging
from dotenv import load_dotenv

from app.routers import mes_operations, operation_events, profiles
from app.exceptions.mes_exceptions import (
    MESOperationException,
    DuplicateOperationException,
    InvalidOperationStateException,
    InvalidQuantityException,
)

load_dotenv()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

API_TITLE = os.getenv("API_TITLE", "MES Operations API")
API_VERSION = os.getenv("API_VERSION", "1.0.0")
API_PREFIX = "/api/v1"

app = FastAPI(
    title=API_TITLE,
    version=API_VERSION,
    description="REST API for Manufacturing Execution System (MES) operations on Supabase",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(DuplicateOperationException)
async def duplicate_operation_handler(
    request: Request, exc: DuplicateOperationException
):
    logger.warning(f"Duplicate operation: {exc.message}")
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"error": exc.error_type, "message": exc.message},
    )


@app.exception_handler(InvalidQuantityException)
async def invalid_quantity_handler(request: Request, exc: InvalidQuantityException):
    logger.warning(f"Invalid quantity: {exc.message}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": exc.error_type, "message": exc.message},
    )


@app.exception_handler(InvalidOperationStateException)
async def invalid_state_handler(request: Request, exc: InvalidOperationStateException):
    logger.warning(f"Invalid state transition: {exc.message}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": exc.error_type, "message": exc.message},
    )


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    logger.error(f"Database integrity error: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "integrity_error",
            "message": "Database constraint violation",
        },
    )


app.include_router(
    mes_operations.router, prefix=f"{API_PREFIX}/operations", tags=["MES Operations"]
)

app.include_router(
    operation_events.router, prefix=f"{API_PREFIX}/events", tags=["Operation Events"]
)

app.include_router(profiles.router, prefix=f"{API_PREFIX}/profiles", tags=["Profiles"])


@app.on_event("startup")
async def startup():
    logger.info(f"Starting {API_TITLE} v{API_VERSION}")


@app.on_event("shutdown")
async def shutdown():
    logger.info("Shutting down API")


@app.get("/", tags=["Root"])
def read_root():
    return {
        "message": "Welcome to MES Operations API",
        "version": API_VERSION,
        "docs": "/docs",
        "redoc": "/redoc",
    }


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
