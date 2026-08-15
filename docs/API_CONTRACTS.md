# PHANTOM PHOENIX — API Contracts

> Phase 0 document. Defines stable interfaces between Backend ↔ Frontend, Backend ↔ AI/ML,
> Backend ↔ Reports. Updated when public behavior changes.
> Last updated: 2026-08-15 (Phase 0 baseline)

---

## 1. Conventions

- Base path: `/api/v1`. OpenAPI at `/docs` (Swagger UI) and `/openapi.json`.
- Versioning: URL segment (`v1`). Breaking changes bump to `v2` in a new router.
- Auth: `Authorization: Bearer <access_token>` (JWT). 401 on missing/expired/invalid.
- Response envelope:

```json
{
  "data": { ... },
  "error": null,
  "meta": { "request_id": "..." }
}
```

- Errors:

```json
{
  "data": null,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "human-readable",
    "details": [ { "field": "size_bytes", "msg": "too large" } ]
  },
  "meta": { "request_id": "..." }
}
```

- Status codes: 200 OK, 201 Created, 400 Validation, 401 Unauthorized, 403 Forbidden,
  404 Not Found, 409 Conflict, 422 Unprocessable (Pydantic), 429 Too Many Requests, 500 Internal.
- Error codes: stable machine-readable `code` values. Add codes; never rename existing ones.
  Current: `VALIDATION_ERROR` (400/422), `NOT_FOUND` (404), `CONFLICT` (409),
  `HTTP_ERROR` (framework/route-level), `INTERNAL_ERROR` (500, sanitized).
- Pagination (list endpoints): `?page=1&page_size=50` → `meta.pagination` = `{page, page_size, total, pages}`.
- Timestamps: ISO 8601 UTC (`2026-08-15T12:00:00Z`).
- All request bodies validated by Pydantic schemas; never DB models directly.

### Implementation status

- **Implemented**: health endpoint (§2.0), error envelope, `/api/v1` versioning, `/docs`,
  media upload (§2.2c), scans (§2.3).
- **Planned (later milestones)**: the rest of §2.1–§2.6 and §3–§5. Contracts below are
  the target; exact fields freeze when each endpoint ships.

---

## 2. Backend ↔ Frontend API

### 2.0 Meta / Health (IMPLEMENTED)

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| GET | `/api/v1/health` | no | Service liveness: identity + status + versions |

**GET /api/v1/health**
```json
Response 200: {
  "data": {
    "status": "ok",
    "service": "PHANTOM PHOENIX Backend",
    "version": "0.1.0",
    "api_version": "/api/v1"
  },
  "error": null,
  "meta": { "request_id": null, "pagination": null }
}
```
- Liveness only; deliberately independent of database and other subsystems.
- A readiness mechanism may be added later if deployment needs justify it.

### 2.1 Auth

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| POST | `/api/v1/auth/register` | no | Create user account |
| POST | `/api/v1/auth/login` | no | OAuth2 password flow → access token |
| GET | `/api/v1/auth/me` | user | Current user profile |
| POST | `/api/v1/auth/logout` | user | Invalidate client token (client-side discard v1) |

**POST /api/v1/auth/register**
```json
Request:  { "email": "a@b.com", "password": "strong!", "full_name": "Hari" }
Response: { "data": { "id": "uuid", "email": "a@b.com", "role": "user", "is_active": true, "created_at": "..." } }
```

**POST /api/v1/auth/login**
```json
Request (OAuth2 form): grant_type=password, username, password
Response: { "data": { "access_token": "jwt...", "token_type": "bearer", "expires_in": 3600 } }
```

### 2.2 Media

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| POST | `/api/v1/media/upload` | user | Upload media (multipart `file`); validates + fingerprints — IMPLEMENTED (Phase 3) |
| GET | `/api/v1/media/{media_id}` | user | Media record — planned |
| DELETE | `/api/v1/media/{media_id}` | user | Delete media + storage (owner/admin) — planned |

Implementation details and full contract: §2.2c below.

### 2.2a Media — Temporary Creation Endpoint (REMOVED, Phase 3)

The Phase 2 minimal JSON endpoint `POST /api/v1/media` was removed when the real
upload workflow landed. There is exactly one way to create a Media record: the
secure upload endpoint below. Clients can no longer supply `storage_path`,
`sha256`, or dimensions.

### 2.2c Media — Secure Upload (IMPLEMENTED, Phase 3)

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| POST | `/api/v1/media/upload` | none (auth later) | Multipart upload; validates content, fingerprints, stores, creates Media record |

**POST /api/v1/media/upload**

```
Request: multipart/form-data, single field `file`
         (the file bytes; the client Content-Type and filename are NOT trusted)
```

Accepted formats (server-side detected; explicit allowlist):

| Format | MIME (detected) | Extensions |
| --- | --- | --- |
| JPEG | `image/jpeg` | `.jpg` `.jpeg` `.jpe` |
| PNG | `image/png` | `.png` |
| WebP | `image/webp` | `.webp` |

Video (MP4 and others) is rejected at this milestone — no video pipeline yet.

Size limit: `MAX_UPLOAD_SIZE_MB` (default 50). Streamed check; oversized → 400.

```json
Response 201: {
  "data": {
    "id": "uuid", "original_filename": "photo.jpg",
    "media_type": "IMAGE", "mime_type": "image/jpeg",
    "size_bytes": 123456, "sha256": "abc...", "width": 4000, "height": 3000,
    "is_deleted": false, "created_at": "..."
  },
  "error": null, "meta": { "request_id": null, "pagination": null }
}
```

`storage_path` and any filesystem detail are NEVER returned.

Validation errors (400, envelope `error.code`):

| Code | Meaning |
| --- | --- |
| `EMPTY_FILE` | Zero-byte upload |
| `FILE_TOO_LARGE` | Exceeds `MAX_UPLOAD_SIZE_MB` |
| `UNSUPPORTED_TYPE` | Content not in the allowlist (e.g. GIF, video) |
| `INVALID_CONTENT` | Corrupt/unrecognized bytes, or extension/content mismatch |
| `INVALID_FILENAME` | Missing/unsafe/too-long filename (traversal, backslash, >255 bytes) |

MIME-spoofing policy: the detected (server-side) MIME type is authoritative and
stored; the client `Content-Type` is ignored. Filename extension must match
detected content.

### 2.3 Scans

Planned: cancel, results endpoints (later milestones). Marked below: what exists.

| Method | Path | Auth | Description | Status |
| --- | --- | --- | --- | --- |
| POST | `/api/v1/scans` | user | Create scan for media | **IMPLEMENTED** |
| GET | `/api/v1/scans/{scan_id}` | user | Scan + status + stage progress | **IMPLEMENTED** |
| GET | `/api/v1/scans` | user | List my scans (paginated, filter by status) | **IMPLEMENTED** |
| POST | `/api/v1/scans/{scan_id}/cancel` | user | Cancel queued/processing scan | planned |
| GET | `/api/v1/scans/{scan_id}/results` | user | All result groups for a scan | planned |

**POST /api/v1/scans** (IMPLEMENTED)
```json
Request:  { "media_id": "uuid" }
Response 201: {
  "data": {
    "id": "uuid", "media_id": "uuid", "status": "CREATED",
    "started_at": null, "completed_at": null, "error_message": null,
    "created_at": "...",
    "media": { /* MediaRead, see §2.2a */ },
    "stages": [ { "id": "uuid", "scan_id": "uuid", "name": "validate",
                  "status": "PENDING", "sequence": 0, "started_at": null,
                  "completed_at": null, "duration_ms": null,
                  "error_message": null, "result_ref": null }, "... (11 stages)" ]
  }
}
```
Behavior: creates the case record only. NO media upload, NO AI analysis. The 11
pipeline stages are created PENDING in canonical order
(`validate, fingerprint, metadata, detect, forensics, xai, evidence, confidence,
risk, verdict, report`).
Errors: 404 `NOT_FOUND` (media_id unknown), 422 `VALIDATION_ERROR`.

**GET /api/v1/scans/{id}** (IMPLEMENTED)
```json
Response 200: same shape as POST response (full detail: media + stages).
Errors: 404 `NOT_FOUND`.
```

**GET /api/v1/scans** (IMPLEMENTED)
```json
Query: page (>=1, default 1), page_size (1..100, default 20), status (optional ScanStatus)
Response 200: {
  "data": [ /* ScanRead (no stages/media detail) */ ],
  "meta": { "pagination": { "page": 1, "page_size": 20, "total": 42, "pages": 3 } }
}
```

Scan lifecycle statuses (state machine in `app/domain/scan.py`):
`CREATED → VALIDATING → QUEUED → PROCESSING → COMPLETED`, with `FAILED` reachable
from `VALIDATING` and `PROCESSING`. `FAILED` is terminal (no retry support yet).
Status is only changed through the scan lifecycle service — never via these
endpoints.

**Execution (IMPLEMENTED, Phase 4)** — a scan is not analyzed by `POST /scans`.
It must be advanced to `QUEUED` by the service layer, after which the analysis
worker claims it (`FOR UPDATE SKIP LOCKED`), runs the pipeline, and finalizes it:

- `COMPLETED`: `validate` + `fingerprint` stages are `COMPLETED` (real results,
  fingerprint `result_ref` = JSON `{"sha256", "d_hash", "size_bytes"}`);
  all unregistered future stages are `SKIPPED` with
  `error_message: "'<name>' stage not implemented in this build"`.
- `FAILED`: e.g. stored file missing (`"stored media file is missing"`) or
  stored-content hash mismatch (`"stored media sha256 mismatch"`); `error_message`
  set on the scan and the failing stage.
- Worker is opt-in (`ANALYSIS_WORKER_ENABLED=true`); in-process v1, replaceable
  by Celery. Stage rows expose `status`, `error_message`, `result_ref`,
  `duration_ms`.

### 2.4 Results

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/v1/scans/{scan_id}/results/detection` | Model predictions |
| GET | `/api/v1/scans/{scan_id}/results/metadata` | EXIF/XMP findings |
| GET | `/api/v1/scans/{scan_id}/results/forensics` | Visual forensic evidence |
| GET | `/api/v1/scans/{scan_id}/results/attribution` | Generator attribution |
| GET | `/api/v1/scans/{scan_id}/results/xai` | Explainability artifacts |
| GET | `/api/v1/scans/{scan_id}/results/assessment` | Evidence summary + confidence + risk + verdict |

**GET .../results/detection** (per model run)
```json
{
  "data": [
    {
      "model": { "name": "efficientnet-b4", "version": "1.0.0", "task": "image_detection" },
      "input_type": "image", "label": "fake", "prediction": "fake",
      "confidence": 0.87, "is_simulation": false,
      "limitations": "Training-distribution bound; not forensic truth.",
      "created_at": "..."
    }
  ]
}
```

**GET .../results/metadata**
```json
{
  "data": {
    "sources": [ { "source": "exif", "status": "present", "extracted": { "Make": "...", "DateTimeOriginal": "..." } } ],
    "findings": [
      {
        "severity": "medium", "evidence_type": "heuristic",
        "finding": "Editing software present (Adobe Photoshop)",
        "details": { "keys": ["Software"] }
      }
    ]
  }
}
```

**GET .../results/forensics** — array of evidence records (see §3 evidence JSON).

**GET .../results/attribution**
```json
{
  "data": [
    {
      "attribution_class": "unknown", "confidence": 0.0, "method": "not_available",
      "model": { "name": null, "version": null },
      "note": "Attribution requires a validated model; not yet available.",
      "created_at": "..."
    }
  ]
}
```

**GET .../results/assessment**
```json
{
  "data": {
    "evidence_summary": { "total": 12, "by_type": { "verified": 0, "model_inference": 3, "heuristic": 9, "unknown": 0 } },
    "confidence": { "score": 0.61, "method": "documented weighted aggregation", "components": { "detection": 0.35, "metadata": 0.08, "forensics": 0.18, "attribution": 0.0, "xai": 0.0 } },
    "risk": { "level": "MEDIUM", "score": 0.55, "rationale": "..." },
    "verdict": { "verdict": "LIKELY_MANIPULATED", "confidence": 0.61, "basis": ["evidence-id-1", "..."] },
    "caution": "Aggregate confidence is NOT probability of manipulation."
  }
}
```

### 2.5 Reports

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| GET | `/api/v1/scans/{scan_id}/report` | user | Report record (status + content summary) |
| GET | `/api/v1/scans/{scan_id}/report/download` | user | PDF file (`application/pdf`) |
| POST | `/api/v1/scans/{scan_id}/report/generate` | user | Trigger/refresh PDF |

### 2.6 Admin

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| GET | `/api/v1/admin/users` | admin | List users (paginated) |
| PATCH | `/api/v1/admin/users/{id}` | admin | Activate/deactivate, change role |
| GET | `/api/v1/admin/scans` | admin | All scans (paginated, filters) |
| GET | `/api/v1/admin/stats` | admin | Dashboard stats (scans/day, status distribution, avg duration) |
| GET | `/api/v1/admin/models` | admin | Model versions registry |
| POST | `/api/v1/admin/models` | admin | Register model version |
| PATCH | `/api/v1/admin/models/{id}` | admin | Set active/deprecated status |

---

## 3. Evidence JSON Contract (Backend ↔ Frontend ↔ Reports)

Standard shape for any forensic/evidence record. Frontend renders by `evidence_type` +
`category`; report renders from same object.

```json
{
  "id": "uuid",
  "scan_id": "uuid",
  "module": "forensics.ela",
  "evidence_type": "model_inference | verified | heuristic | unknown",
  "evidence_category": "compression_artifact | noise_residual | frequency | metadata_inconsistency | prediction | attribution | xai_coverage | ...",
  "strength": 0.0,
  "severity": "low | medium | high | critical",
  "location": { "kind": "whole_image | region | frame | metadata", "region": null, "bbox": null, "frame": null },
  "details": {},
  "model": { "name": null, "version": null },
  "limitations": "string",
  "created_at": "ISO8601"
}
```

## 4. Backend ↔ AI/ML Interface

### 4.1 Detector interface (Python, `app/inference/base.py`)

```python
class Prediction(BaseModel):
    task: str                       # image_detection | video_detection | attribution | xai
    label: str                      # e.g. "fake" / "real" / class name
    confidence: float               # 0..1, model confidence, NOT truth probability
    is_simulation: bool             # True when no real model produced this
    model_name: str | None
    model_version: str | None
    model_metadata: dict            # architecture, checkpoint, preprocessor config
    limitations: str
    created_at: datetime

class Detector(Protocol):
    id: str
    supports: set[str]              # tasks it can serve
    def detect(self, media_path: str, context: dict) -> Prediction: ...
```

### 4.2 Model version tracking

```json
{ "name": "efficientnet-b4", "version": "1.2.0", "task": "image_detection",
  "architecture": "EfficientNet-B4", "status": "active", "notes": "...", "created_at": "..." }
```
Rules: exactly one `active` version per `(name, task)` at a time; every result row stores
the producing `model_version_id`; accuracy claims require measured evaluation data in `notes`.

### 4.3 Contract rules

- Detector returns raw model confidence; calibration/aggregation lives in the confidence engine.
- Any synthetic/baseline output MUST set `is_simulation: true` and `model_name: null`-or-`simulation-*`.
- Attribution returns `attribution_class` from the fixed taxonomy + confidence + `method`;
  `method` describes the evidence source (model, heuristics, metadata).
- XAI provider returns artifact paths + summary; artifacts are real, never synthesized.

## 5. Backend ↔ Reports Interface

- Report builder consumes only persisted results (same JSON as §2.4/§3).
- Report JSON mirrors the document sections in `docs/BACKEND_IMPLEMENTATION.md` §15.
- PDF renderer maps report JSON → ReportLab layout; determinism: same scan → same PDF bytes
  (modulo timestamps) for given report version.
- A report is `status: ready | generating | failed`; failed reports expose `error` message.

## 6. Validation Rules (shared contract)

- Media: max size `MAX_UPLOAD_SIZE_MB` (default 50); allowlist JPEG/PNG/WebP (video deferred);
  content sniffing required (magic bytes + safe parse); SHA-256 computed server-side from raw
  bytes; detected MIME authoritative; filename extension must match detected content.
- Pagination caps: `page_size` 1..100 (default 20).
- Auth: access token TTL default 60 min; refresh flow out of v1 scope.
- Errors: machine-readable `code` stable; add codes, never rename existing ones.

## 7. Change History

| Date | Change |
| --- | --- |
| 2026-08-15 | Phase 0 baseline: contracts for auth, media, scans, results, assessment, reports, admin, AI/ML, reports |
| 2026-08-15 | Phase 1: health endpoint contract (implemented), error code list, implementation-status markers for planned sections |
| 2026-08-15 | Phase 2: implement POST/GET /api/v1/media (minimal creation, no upload); POST /api/v1/scans, GET /api/v1/scans/{id}, GET /api/v1/scans (paginated, status filter); scan lifecycle statuses + state machine; 11 canonical pipeline stages |
| 2026-08-16 | Phase 3: replace POST /api/v1/media with POST /api/v1/media/upload (multipart, secure ingestion); error codes EMPTY_FILE/FILE_TOO_LARGE/UNSUPPORTED_TYPE/INVALID_CONTENT/INVALID_FILENAME; max size default 50 MB; allowlist JPEG/PNG/WebP; MIME-spoofing policy; upload contract §2.2c |
| 2026-08-16 | Phase 4: scan execution path documented (worker claims QUEUED, pipeline runs validate+fingerprint, COMPLETED/FAILED semantics, SKIPPED reasons, result_ref JSON for fingerprint); worker opt-in flag; replaceable in-process worker |
