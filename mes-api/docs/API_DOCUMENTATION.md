# MES Operations API - REST Documentation

## Base URL
```
http://127.0.0.1:8000/api/v1
```

## Resource: MES Operations

Manufacturing operations tracking with composite primary key `(order_no, asset_id, operation_no)`.

### Endpoints

#### `GET /operations`
List all operations with optional filtering.

**Query Parameters:**
- `skip` (int): Pagination offset (default: 0)
- `limit` (int): Max results, 1-500 (default: 100)
- `status` (string): Filter by status (RELEASED, IN_PROGRESS, FINISHED, CANCELLED)
- `workplace_name` (string): Filter by workplace

**Response: 200 OK**
```json
[
  {
    "order_no": "403860-001",
    "asset_id": 1,
    "operation_no": "0020",
    "status": "IN_PROGRESS",
    "workplace_name": "Programmierung",
    "qty_desired": 10,
    "qty_processed": 5,
    "qty_scrap": 0,
    "timestamp_ms": "2025-09-10T20:18:03Z",
    "change_type": "UPDATE"
  }
]
```

---

#### `GET /operations/{order_no}/{asset_id}/{operation_no}`
Get specific operation by composite key.

**Response: 200 OK** - Operation found
**Response: 404 Not Found**
```json
{
  "detail": {
    "error": "not_found",
    "message": "Operation not found: 403860-001/1/0020",
    "resource": {
      "order_no": "403860-001",
      "asset_id": 1,
      "operation_no": "0020"
    }
  }
}
```

---

#### `POST /operations`
Create new operation.

**Request Body:**
```json
{
  "order_no": "403860-001",
  "asset_id": 1,
  "operation_no": "0030",
  "workplace_name": "TruLaser 5060 (L76)",
  "activity_code": "LASER",
  "status": "RELEASED",
  "qty_desired": 100,
  "qty_processed": 0,
  "qty_scrap": 0,
  "timestamp_ms": "2025-09-30T10:00:00Z",
  "change_type": "INSERT"
}
```

**Response: 201 Created**
- Returns created operation
- Sets `Location` header: `/api/v1/operations/{order_no}/{asset_id}/{operation_no}`

**Response: 409 Conflict** - Operation already exists
**Response: 422 Unprocessable Entity** - Validation error (e.g., qty_processed > qty_desired)

---

#### `PATCH /operations/{order_no}/{asset_id}/{operation_no}`
Partial update of operation.

**Request Body (all fields optional):**
```json
{
  "qty_processed": 50,
  "timestamp_ms": "2025-09-30T11:00:00Z",
  "change_type": "UPDATE"
}
```

**Response: 200 OK** - Returns updated operation
**Response: 404 Not Found** - Operation doesn't exist
**Response: 422 Unprocessable Entity** - Business rule violation

**Business Rules:**
- `qty_processed` cannot exceed `qty_desired`
- Cannot transition from FINISHED to IN_PROGRESS

---

#### `DELETE /operations/{order_no}/{asset_id}/{operation_no}`
Delete operation.

**Response: 204 No Content** - Successfully deleted
**Response: 404 Not Found** - Operation doesn't exist

**Note:** Consider using `status='CANCELLED'` instead for audit trail.

---

## Resource: Operation Events

Event log for manufacturing floor actions (START, STOP, COMPLETE, REPORT_QUANTITY, FINISH).

### Endpoints

#### `GET /events`
List events with filtering.

**Query Parameters:**
- `skip`, `limit` (pagination)
- `order_no` (string): Filter by work order
- `action_type` (string): Filter by action (START, STOP, COMPLETE, REPORT_QUANTITY, FINISH)

**Response: 200 OK**
```json
[
  {
    "id": "10c5d829-abde-49ce-93ef-598d5ef10ee0",
    "action_type": "START",
    "order_no": "403841-008",
    "operation_no": "0020",
    "workplace_name": "Trommelen-1",
    "user_id": "5184123e-febc-47a3-9c5e-495ef4af4257",
    "user_email": "luke@vanenkhuizen.com",
    "operation_data": {...},
    "webhook_success": true,
    "created_at": "2025-09-11T12:02:25.669897Z"
  }
]
```

---

#### `GET /events/{event_id}`
Get specific event by UUID.

**Response: 200 OK** - Event found
**Response: 404 Not Found**

---

#### `POST /events`
Create new event (operator action logging).

**Request Body:**
```json
{
  "action_type": "START",
  "order_no": "403841-008",
  "operation_no": "0020",
  "workplace_name": "Trommelen-1",
  "user_id": "5184123e-febc-47a3-9c5e-495ef4af4257",
  "user_email": "luke@vanenkhuizen.com",
  "operation_data": {
    "status": "RELEASED",
    "qty_desired": 250,
    "activity_code": "TROMMELEN"
  }
}
```

**Response: 201 Created**
- Returns created event
- Sets `Location` header

**Validation:** `action_type` must be one of 5 allowed values (enforced by Pydantic Literal)

---

#### `GET /events/workplace/{workplace_name}`
Get events for specific workplace.

**Response: 200 OK** - List of events for that workplace

---

## Resource: Profiles

User profiles (managed by Supabase Auth, API primarily for reading).

### Endpoints

#### `GET /profiles`
List all profiles.

#### `GET /profiles/{profile_id}`
Get specific profile by UUID.

#### `POST /profiles`
Create profile (typically via Supabase trigger).

**Response: 409 Conflict** - Profile already exists

#### `PATCH /profiles/{profile_id}`
Update profile (role, workplace_access).

#### `DELETE /profiles/{profile_id}`
Delete profile.

**Response: 204 No Content**

---

## HTTP Status Codes Used

| Code | Usage |
|------|-------|
| 200 OK | Successful GET/PATCH |
| 201 Created | Successful POST (resource created) |
| 204 No Content | Successful DELETE (no body returned) |
| 400 Bad Request | Database integrity error |
| 404 Not Found | Resource doesn't exist |
| 409 Conflict | Resource already exists (duplicate key) |
| 422 Unprocessable Entity | Validation error or business rule violation |

---

## Error Response Format

All errors return JSON with consistent structure:

```json
{
  "detail": {
    "error": "error_type",
    "message": "Human-readable error message"
  }
}
```

**Error Types:**
- `not_found` - Resource doesn't exist (404)
- `duplicate_operation` / `duplicate_profile` - Already exists (409)
- `invalid_quantity` - Business rule: qty_processed > qty_desired (422)
- `invalid_state_transition` - Business rule: invalid status change (422)
- `integrity_error` - Database constraint violation (400)

---

## REST Principles Demonstrated

✅ **Resource-based URLs** (nouns, not verbs)  
✅ **HTTP verbs** map to CRUD (GET, POST, PATCH, DELETE)  
✅ **Proper status codes** (200, 201, 204, 404, 409, 422)  
✅ **Location headers** on 201 Created responses  
✅ **Structured error responses** with error types  
✅ **Query parameters** for filtering/pagination  
✅ **Partial updates** via PATCH (not PUT)  
✅ **Composite keys** in URL paths  
✅ **No verbs in URLs** (use HTTP methods instead)