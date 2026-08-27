# API Contract

## API version boundary

All application HTTP resources use the versioned prefix:

```text
/api/v1
```

Future resources must live below this boundary unless a later explicit architecture decision changes it.

## Current implemented endpoint

```http
GET /api/v1/health
```

Response (HTTP 200):

```json
{
  "status": "ok"
}
```

This is the only implemented business-independent API endpoint at present.

## Contract source

- FastAPI's generated OpenAPI schema is the source of truth for HTTP request and response contracts.
- Request and response schemas use Pydantic models in the API layer.
- Frontend clients and types should later be generated or derived from OpenAPI rather than manually duplicating backend domain models.

## Layer boundary

- The API/router layer owns HTTP contracts only.
- Routers do not contain domain or business logic.
- Database access does not occur directly in routers.
- The frontend does not own authorization or technical-debt lifecycle rules.

## Future resources

Resources such as assets, signals, candidates, debts, governance, and agent runs will be introduced incrementally by later work packages. Their field-level contracts are not defined here.
