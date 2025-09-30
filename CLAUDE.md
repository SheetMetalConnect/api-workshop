# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Educational workshop project** demonstrating progressive REST API development with FastAPI. Part of "Building RESTful APIs for MCP" course focused on manufacturing digital transformation and Model Context Protocol integration.

The repository contains four iterations of a Public Library REST API (educational domain), each building upon the previous to teach specific concepts:

1. **library-api-basic**: Basic REST API fundamentals (Iteration 0)
2. **library-api-with-oauth**: OAuth 2.0 authentication with Auth0 (Iteration 1)
3. **library-api-with-ratelimiting**: Rate limiting via SlowAPI (Iteration 2)
4. **library-api-with-sustainable-evolution**: API versioning with Alembic migrations (Iteration 3)

**Note**: This is a learning project with intentional limitations in early iterations. Not production code.

## Architecture

### Common Structure (All Iterations)
```
app/
├── main.py              # FastAPI entry point, router registration
├── database.py          # SQLAlchemy engine, session management
├── models/              # SQLAlchemy ORM models (author, book, branch, library_system, loan, patron)
├── schemas/             # Pydantic validation schemas
├── crud/                # CRUD operations (separated from routes)
├── routers/             # API route definitions
└── exceptions/          # Custom exception classes
```

### Key Patterns

**Database**: SQLite with SQLAlchemy ORM. Foreign key enforcement enabled via `PRAGMA foreign_keys=ON` in `database.py`. Singleton pattern for `library_system` resource.

**Routing**: Each resource (authors, books, branches, etc.) has dedicated router in `app/routers/`. Routes follow REST conventions with proper HTTP status codes (200, 201, 204, 404, 422, etc.).

**Error Handling**: Custom exceptions (e.g., `BookCRUDException`) with `error_type` field map to specific HTTP status codes in routers (e.g., `foreign_key_violation` → 422).

**OAuth Implementation** (Iteration 1+): `app/security.py` verifies JWT tokens from Auth0 using JWKS, with async caching (`async-lru`). Requires `.env` with `AUTH0_DOMAIN` and `API_AUDIENCE`.

**Rate Limiting** (Iteration 2+): SlowAPI integrated in `main.py`. Routers use factory pattern (`create_authors_router(limiter)`) to inject limiter dependency.

**Versioning** (Iteration 3): Starlette mounts separate FastAPI apps for `/api/v1` and `/api/v2`. Routers organized in `app/routers/v1/` and `app/routers/v2/` subdirectories. Database migrations managed via Alembic.

## Development Commands

**IMPORTANT - Windows PowerShell Commands**: This project runs on Windows. When executing commands in PowerShell, use the exact syntax shown below. Do NOT wrap commands in curly braces or pipe through `$null`.

### Setup

Navigate to the specific iteration directory first (e.g., `library-api-basic`), then:

**Create virtual environment:**
```powershell
python -m venv venv
```

**Activate virtual environment (Windows PowerShell):**
```powershell
.\venv\Scripts\Activate.ps1
```

**Install dependencies:**
```powershell
pip install -r requirements.txt
```

### Running the API

**Start development server with auto-reload:**
```powershell
uvicorn app.main:app --reload
```

- API runs on: `http://127.0.0.1:8000`
- Interactive docs: `http://127.0.0.1:8000/docs`

### OAuth Testing (Iteration 1+)

Create a `.env` file in the iteration directory with Auth0 credentials:
```
AUTH0_DOMAIN=your-domain.auth0.com
API_AUDIENCE=your-api-identifier
```

Use `tests/get-oauth-jwt-token.py` to obtain test tokens.

### Database Migrations (Iteration 3)

**Initialize Alembic (first time only):**
```powershell
alembic init migrations
```

**Create new migration:**
```powershell
alembic revision -m "description"
```

**Apply migrations:**
```powershell
alembic upgrade head
```

**View current schema (SQLite):**
```powershell
sqlite3 library.db ".schema {table_name}"
```

### Command Execution Notes

- Execute commands directly without wrapping in PowerShell script blocks
- Use native PowerShell syntax (`.\venv\Scripts\Activate.ps1` not `source venv/bin/activate`)
- When checking file existence, use: `Test-Path "path"`
- When listing directories, use: `Get-ChildItem` or `dir`

## Important Implementation Notes

**Database File**: Each iteration uses `library.db` in its root directory. Delete this file to reset database state.

**API Prefix**: All routes prefixed with `/api` (configurable via `API_PREFIX` in `main.py`). Iteration 3 uses `/api/v1` and `/api/v2`.

**Relationships**:
- Books → Authors (many-to-one via `author_id`)
- Loans → Books, Patrons, Branches (foreign keys)
- Library System is singleton (only one instance)

**Known Limitations (Iteration 0)**:
- Books limited to single author
- No support for multiple copies of same book
- No branch-level inventory tracking

**Security Requirements**: Write operations should be protected with JWT authentication (Iteration 1+). GET operations typically public.

**Rate Limiting**: Default limits vary by endpoint. Check router implementations for specific `@limiter.limit()` decorators.

## Learning Progression

Each iteration intentionally introduces problems solved in the next:

- **Iteration 0**: Demonstrates basic CRUD, exposes data integrity issues (no FK enforcement, single-author limitation)
- **Iteration 1**: Adds OAuth security layer, prepares for multi-client access
- **Iteration 2**: Introduces rate limiting to prevent abuse
- **Iteration 3**: Shows API versioning strategy for backwards-compatible evolution

See `problems-iteration{N}.md` files in each iteration directory for detailed problem statements and solutions.

## Educational Context

Workshop teaches API design for manufacturing/MCP contexts using simplified library domain. Focus areas:
- Progressive enhancement (basic → production-ready)
- AI integration patterns (structured data access for assistants)
- Event-driven system architecture preparation
- Unified Namespace (UNS) connectivity patterns