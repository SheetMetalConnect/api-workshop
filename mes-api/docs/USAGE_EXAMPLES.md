# MES API - Usage Examples

## Setup & Running

```powershell
cd D:\GIT\api-workshop\mes-api
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

Access at: http://127.0.0.1:8000/docs

---

## Example 1: Create a New Operation

**Scenario:** New laser cutting job arrives

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/operations" \
  -H "Content-Type: application/json" \
  -d '{
    "order_no": "404000-001",
    "asset_id": 1,
    "operation_no": "0020",
    "workplace_name": "TruLaser 5060 (L76)",
    "activity_code": "LASER",
    "activity_description": "LASER",
    "status": "RELEASED",
    "qty_desired": 50,
    "qty_processed": 0,
    "qty_scrap": 0,
    "planned_start_at": "2025-10-01T08:00:00Z",
    "planned_end_at": "2025-10-01T10:00:00Z",
    "timestamp_ms": "2025-09-30T15:00:00Z",
    "change_type": "INSERT"
  }'
```

**Expected Response: 201 Created**
```json
{
  "order_no": "404000-001",
  "asset_id": 1,
  "operation_no": "0020",
  "status": "RELEASED",
  "workplace_name": "TruLaser 5060 (L76)",
  "qty_desired": 50,
  "qty_processed": 0
}
```

**Location Header:** `/api/v1/operations/404000-001/1/0020`

---

## Example 2: Operator Starts Work

**Scenario:** Operator clicks START button on shop floor terminal

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/events" \
  -H "Content-Type: application/json" \
  -d '{
    "action_type": "START",
    "order_no": "404000-001",
    "operation_no": "0020",
    "workplace_name": "TruLaser 5060 (L76)",
    "user_id": "5184123e-febc-47a3-9c5e-495ef4af4257",
    "user_email": "luke@vanenkhuizen.com",
    "operation_data": {
      "status": "RELEASED",
      "qty_desired": 50
    }
  }'
```

**Expected Response: 201 Created**

Then update operation status:

```bash
curl -X PATCH "http://127.0.0.1:8000/api/v1/operations/404000-001/1/0020" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "IN_PROGRESS",
    "actual_start_at": "2025-10-01T08:15:00Z",
    "timestamp_ms": "2025-10-01T08:15:00Z",
    "change_type": "UPDATE"
  }'
```

---

## Example 3: Update Quantity Processed

**Scenario:** Operator reports progress (25 out of 50 pieces done)

```bash
curl -X PATCH "http://127.0.0.1:8000/api/v1/operations/404000-001/1/0020" \
  -H "Content-Type: application/json" \
  -d '{
    "qty_processed": 25,
    "timestamp_ms": "2025-10-01T09:00:00Z",
    "change_type": "UPDATE"
  }'
```

**Expected Response: 200 OK** with updated operation

---

## Example 4: Report Scrap

**Scenario:** 2 pieces were rejected

```bash
curl -X PATCH "http://127.0.0.1:8000/api/v1/operations/404000-001/1/0020" \
  -H "Content-Type: application/json" \
  -d '{
    "qty_scrap": 2,
    "timestamp_ms": "2025-10-01T09:15:00Z",
    "change_type": "UPDATE"
  }'
```

---

## Example 5: Complete Operation

**Scenario:** All pieces done, mark as FINISHED

```bash
curl -X PATCH "http://127.0.0.1:8000/api/v1/operations/404000-001/1/0020" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "FINISHED",
    "qty_processed": 50,
    "actual_end_at": "2025-10-01T10:05:00Z",
    "timestamp_ms": "2025-10-01T10:05:00Z",
    "change_type": "UPDATE"
  }'
```

---

## Example 6: Query Operations

**Get all IN_PROGRESS operations:**
```bash
curl "http://127.0.0.1:8000/api/v1/operations?status=IN_PROGRESS"
```

**Get operations at specific workplace:**
```bash
curl "http://127.0.0.1:8000/api/v1/operations?workplace_name=TruLaser%205060%20(L76)"
```

**Get paginated results:**
```bash
curl "http://127.0.0.1:8000/api/v1/operations?skip=0&limit=10"
```

---

## Example 7: Query Events

**Get all START events:**
```bash
curl "http://127.0.0.1:8000/api/v1/events?action_type=START"
```

**Get events for specific order:**
```bash
curl "http://127.0.0.1:8000/api/v1/events?order_no=404000-001"
```

**Get events at workplace:**
```bash
curl "http://127.0.0.1:8000/api/v1/events/workplace/Trommelen-1"
```

---

## Example 8: Error Handling

**Attempt to create duplicate:**
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/operations" \
  -H "Content-Type: application/json" \
  -d '{
    "order_no": "404000-001",
    "asset_id": 1,
    "operation_no": "0020",
    "timestamp_ms": "2025-09-30T15:00:00Z",
    "change_type": "INSERT"
  }'
```

**Expected Response: 409 Conflict**
```json
{
  "detail": {
    "error": "duplicate_operation",
    "message": "Operation already exists: 404000-001/1/0020"
  }
}
```

---

**Attempt invalid quantity:**
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/operations" \
  -H "Content-Type: application/json" \
  -d '{
    "order_no": "404000-002",
    "asset_id": 1,
    "operation_no": "0010",
    "qty_desired": 50,
    "qty_processed": 100,
    "timestamp_ms": "2025-09-30T15:00:00Z",
    "change_type": "INSERT"
  }'
```

**Expected Response: 422 Unprocessable Entity**
```json
{
  "detail": {
    "error": "invalid_quantity",
    "message": "qty_processed (100) cannot exceed qty_desired (50)"
  }
}
```

---

**Attempt invalid status transition:**
```bash
curl -X PATCH "http://127.0.0.1:8000/api/v1/operations/404000-001/1/0020" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "IN_PROGRESS"
  }'
```

**Expected Response: 422 Unprocessable Entity** (if current status is FINISHED)
```json
{
  "detail": {
    "error": "invalid_state_transition",
    "message": "Cannot transition from FINISHED to IN_PROGRESS"
  }
}
```

---

**Get non-existent operation:**
```bash
curl "http://127.0.0.1:8000/api/v1/operations/999999/1/0010"
```

**Expected Response: 404 Not Found**
```json
{
  "detail": {
    "error": "not_found",
    "message": "Operation not found: 999999/1/0010",
    "resource": {
      "order_no": "999999",
      "asset_id": 1,
      "operation_no": "0010"
    }
  }
}
```

---

## Testing with Swagger UI

1. Open http://127.0.0.1:8000/docs
2. Click "Try it out" on any endpoint
3. Fill in parameters/body
4. Click "Execute"
5. See response below (status code, body, headers)

**Advantages:**
- No curl/Postman needed
- Auto-completion from schemas
- See all available endpoints
- Test validation errors interactively