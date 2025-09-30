# MES Operations API

REST API for Manufacturing Execution System (MES) operations, built with FastAPI and connected to Supabase PostgreSQL database.

## Features

- **MES Operations**: CRUD operations for manufacturing operations tracking
- **Operation Events**: Event logging for START, STOP, COMPLETE, REPORT_QUANTITY, FINISH actions
- **Profiles**: User profile management with workplace access control
- **FastAPI**: High-performance async API framework
- **PostgreSQL**: Supabase-hosted database with proper schema support
- **Interactive Docs**: Swagger UI and ReDoc for API exploration

## Database Schema

### Tables
- `mes_operations`: Manufacturing operations with composite primary key (order_no, asset_id, operation_no)
- `operation_events`: Event log for operation actions
- `profiles`: User profiles linked to Supabase auth.users

## Setup

### Prerequisites
- Python 3.9+
- Supabase account with PostgreSQL database
- Database tables already created (see schema in connection string comment)

### Installation

1. **Navigate to project directory**
```powershell
cd D:\GIT\api-workshop\mes-api
```

2. **Create virtual environment**
```powershell
python -m venv venv
```

3. **Activate virtual environment**
```powershell
.\venv\Scripts\Activate.ps1
```

4. **Install dependencies**
```powershell
pip install -r requirements.txt
```

5. **Configure environment variables**

Create a `.env` file in the project root:
```
DATABASE_URL=postgresql://postgres:YOUR-PASSWORD@db.ddmhfxeqffhtwnbwnnbk.supabase.co:5432/postgres
API_TITLE=MES Operations API
API_VERSION=1.0.0
```

Replace `YOUR-PASSWORD` with your actual Supabase database password.

### Running the API

```powershell
uvicorn app.main:app --reload
```

The API will be available at:
- **API Base**: http://127.0.0.1:8000
- **Interactive Docs (Swagger)**: http://127.0.0.1:8000/docs
- **Alternative Docs (ReDoc)**: http://127.0.0.1:8000/redoc

## API Endpoints

### MES Operations (`/api/v1/operations`)
- `GET /api/v1/operations` - List operations (supports filtering by status, workplace)
- `GET /api/v1/operations/{order_no}/{asset_id}/{operation_no}` - Get specific operation
- `POST /api/v1/operations` - Create new operation
- `PATCH /api/v1/operations/{order_no}/{asset_id}/{operation_no}` - Update operation
- `DELETE /api/v1/operations/{order_no}/{asset_id}/{operation_no}` - Delete operation

### Operation Events (`/api/v1/events`)
- `GET /api/v1/events` - List events (supports filtering by order_no, action_type)
- `GET /api/v1/events/{event_id}` - Get specific event
- `POST /api/v1/events` - Create new event
- `GET /api/v1/events/workplace/{workplace_name}` - Get events by workplace

### Profiles (`/api/v1/profiles`)
- `GET /api/v1/profiles` - List profiles
- `GET /api/v1/profiles/{profile_id}` - Get specific profile
- `POST /api/v1/profiles` - Create new profile
- `PATCH /api/v1/profiles/{profile_id}` - Update profile
- `DELETE /api/v1/profiles/{profile_id}` - Delete profile

## Project Structure

```
mes-api/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app and router configuration
│   ├── database.py          # SQLAlchemy database connection
│   ├── models/              # SQLAlchemy ORM models
│   │   ├── mes_operation.py
│   │   ├── operation_event.py
│   │   └── profile.py
│   ├── schemas/             # Pydantic validation schemas
│   │   ├── mes_operation.py
│   │   ├── operation_event.py
│   │   └── profile.py
│   ├── crud/                # Database operations
│   │   ├── mes_operation.py
│   │   ├── operation_event.py
│   │   └── profile.py
│   └── routers/             # API route handlers
│       ├── mes_operations.py
│       ├── operation_events.py
│       └── profiles.py
├── .env                     # Environment variables (not in git)
├── .env.example             # Example environment file
├── .gitignore
├── requirements.txt
└── README.md
```

## Learning Objectives

This project demonstrates:
- ✅ **REST API design** with proper resource-based structure (nouns)
- ✅ **HTTP verbs** mapping (GET, POST, PATCH, DELETE)
- ✅ **HTTP status codes** (200, 201, 204, 404, 409, 422)
- ✅ **Database integration** with PostgreSQL/Supabase
- ✅ **Composite primary keys** handling
- ✅ **JSONB support** for flexible data storage
- ✅ **Query filtering** and pagination
- ✅ **Foreign key relationships** (profile → auth.users)
- ✅ **UUID support** for unique identifiers

## Next Steps (Future Iterations)

Following the workshop pattern, you could add:
- **OAuth 2.0 authentication** with Supabase Auth
- **Rate limiting** with SlowAPI
- **API versioning** (v1, v2)
- **WebSocket support** for real-time updates
- **Webhook integration** for operation events

## Troubleshooting

### Connection Issues
- Verify your Supabase DATABASE_URL in `.env`
- Check that your IP is allowed in Supabase dashboard
- Ensure database tables exist in the `public` schema

### Import Errors
- Make sure virtual environment is activated
- Run `pip install -r requirements.txt` again

### CORS Issues
- Update `allow_origins` in `app/main.py` for production use