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

### 2.3a Metadata stage result (IMPLEMENTED, Phase 5)

No new endpoint. The metadata stage writes its normalized payload to the
`metadata` stage's `result_ref` (JSON), surfaced through
`GET /api/v1/scans/{scan_id}` (`data.stages[]`). Shape is stable and
deterministic; absent values are `null`/empty — never placeholders.

```json
{
  "format": "JPEG",
  "mode": "RGB",
  "dimensions": { "width": 24, "height": 16 },
  "exif": {
    "present": true,
    "camera_make": "Nikon",
    "camera_model": "Z9",
    "captured_at": "2023-05-04T10:11:12",
    "modified_at": null,
    "software": ["Adobe Photoshop 24.0"],
    "orientation": 6,
    "exposure_time": null, "f_number": null,
    "iso_speed_ratings": 400, "focal_length": null, "flash": null,
    "white_balance": null, "image_description": null, "artist": null,
    "copyright": null, "lens_make": null, "lens_model": null
  },
  "gps": {
    "present": true,
    "latitude": 37.8666667, "longitude": -122.4166667,
    "altitude_m": 12.5, "date_stamp": "2023:05:04"
  },
  "xmp": {
    "present": false,
    "creator_tool": null, "create_date": null, "modify_date": null,
    "metadata_date": null, "creators": [], "rights": null, "title": null,
    "description": null, "format": null, "software": []
  },
  "icc": { "present": false },
  "presence": { "exif": true, "xmp": false, "icc": false, "gps": true },
  "software": ["Adobe Photoshop 24.0"],
  "consistency": {
    "findings": [
      {
        "code": "gps_present",
        "evidence_type": "VERIFIED",
        "message": "GPS coordinates are present in the metadata (privacy-sensitive)"
      }
    ],
    "count": 1
  },
  "provenance": {
    "status": "UNAVAILABLE",
    "note": "C2PA/manifest provenance parsing is not implemented in this build"
  },
  "extractor": { "library": "Pillow", "errors": [] }
}
```

Contract rules:

- `evidence_type` ∈ `VERIFIED | INFERENCE | HEURISTIC | UNKNOWN` (same taxonomy
  as the evidence model). Findings carry real, parsed values only.
- Timestamps are naive ISO 8601 (EXIF carries no timezone; never assumed UTC).
- GPS values are signed decimal degrees; presence alone is flagged
  (`gps_present`) as privacy-sensitive.
- `provenance.status` is `UNAVAILABLE` until a real C2PA parser exists — a
  missing manifest is never reported as "unsigned/proven, real" or "fake".
- Editing software is evidence of processing, never a claim of AI generation
  (the message says so explicitly).
- Metadata presence/absence or any single finding is NOT a verdict.

### 2.3b Detection stage result (IMPLEMENTED, Phase 6)

No new endpoint. The `detect` stage writes a structured `DetectionResult` to its
`result_ref` (JSON), surfaced through `GET /api/v1/scans/{scan_id}`
(`data.stages[]`). Deterministic shape; absent values are `null` — never
placeholders.

```json
{
  "detector": {
    "name": "unavailable",
    "detector_version": "1",
    "model_name": null,
    "model_version": null,
    "checkpoint_sha256": null,
    "preprocessing_version": null
  },
  "media_type": "IMAGE",
  "prediction": null,
  "inference": {
    "status": "UNAVAILABLE",
    "reason": "no image detector is registered in this build",
    "device": "cpu",
    "duration_ms": 3
  },
  "evidence_type": null
}
```

With a real model the `prediction` object is:

```json
{
  "label": "FAKE",
  "score": 0.87,
  "score_semantics": "sigmoid probability",
  "class_list": ["REAL", "FAKE"]
}
```

Contract rules:

- `inference.status` ∈ `AVAILABLE | UNAVAILABLE`. UNAVAILABLE (this build)
  means no model exists — the pipeline never fabricates a prediction.
- `score` is in `[0,1]` and MUST be paired with `score_semantics` (how the score
  is derived; raw logits are never reported as a probability).
- `evidence_type` is `"INFERENCE"` only when a real prediction exists, else
  `null`. Model inference is never "verified truth".
- `detector_version` is the contract version (`"1"`), not a model version;
  model identity fields are `null` when unknown — never invented.
- `duration_ms` is measured wall-clock time for the detector call.

### 2.3c Forensics stage result (IMPLEMENTED, Phase 7)

No new endpoint. The `forensics` stage writes a structured, deterministic
payload to its `result_ref` (JSON), surfaced through
`GET /api/v1/scans/{scan_id}` (`data.stages[]`).

```json
{
  "image": { "format": "PNG", "width": 64, "height": 64, "mode": "L" },
  "summary": { "analyzers": 3, "completed": 3, "failed": 0 },
  "analyzers": {
    "ela": {
      "analyzer": "ela", "version": "1", "status": "COMPLETED", "error": null,
      "parameters": { "quality": 80 },
      "measurements": {
        "mean_abs_error": 0.0, "max_error": 0,
        "p95_error": 0.0, "p99_error": 0.0, "error_ratio": 0.0
      },
      "findings": [
        { "code": "ela_measured", "evidence_type": "VERIFIED",
          "message": "Measured ELA at JPEG quality 80: mean absolute error 0.0, error ratio 0.0000" },
        { "code": "ela_interpretation", "evidence_type": "HEURISTIC",
          "message": "ELA is a supporting signal only: ..." }
      ]
    },
    "noise": {
      "analyzer": "noise", "version": "1", "status": "COMPLETED", "error": null,
      "parameters": { "blur_radius": 1.0 },
      "measurements": {
        "residual_mean": 0.0, "residual_std": 0.0, "residual_energy": 0.0,
        "p99_abs_residual": 0.0, "nonzero_ratio": 0.0
      },
      "findings": [ "...noise_measured...", "...noise_interpretation..." ]
    },
    "frequency": {
      "analyzer": "frequency", "version": "1", "status": "COMPLETED", "error": null,
      "parameters": { "low_fraction": 0.1, "mid_fraction": 0.3, "entropy_bins": 256 },
      "measurements": {
        "low_energy_ratio": 0.0, "mid_energy_ratio": 0.0,
        "high_energy_ratio": 0.0, "spectral_entropy": 0.0
      },
      "findings": [ "...frequency_measured...", "...frequency_interpretation..." ]
    }
  }
}
```

Contract rules:

- Values are MEASUREMENTS, never an authenticity probability or verdict. No
  `confidence`, `manipulation_probability`, or `AI_probability` field exists.
- `status` per analyzer ∈ `COMPLETED | FAILED`. An analyzer failure is isolated:
  it records `error` (client-safe) while other analyzers still run; the stage
  itself COMPLETES. Image-level failures (unreadable/oversized) fail the stage.
- `evidence_type` ∈ `VERIFIED | INFERENCE | HEURISTIC | UNKNOWN` (shared
  taxonomy). Findings restating a measured value are `VERIFIED`; interpretive
  statements are `HEURISTIC` and explicitly say the signal is supporting-only.
- Float measurements are rounded to 6 decimal places; output is deterministic
  for identical input bytes and settings.
- Analyzer parameters are explicit and documented (ELA quality, blur radius,
  frequency band fractions/entropy bins).

### 2.3d XAI stage result (IMPLEMENTED, Phase 8)

No new endpoint. The `xai` stage writes a structured, deterministic payload to
its `result_ref` (JSON), surfaced through `GET /api/v1/scans/{scan_id}`
(`data.stages[]`).

This build has no detector model, so the only reachable state is UNAVAILABLE
(an honest state, not an error — the stage itself COMPLETES):

```json
{
  "status": "UNAVAILABLE",
  "reason": "no detector model produced a prediction; XAI requires a real model inference to explain (detection: no image detector is registered in this build)",
  "explainer": { "name": "unavailable", "version": "1", "technique": "none", "model_type": null },
  "model": { "name": null, "version": null, "checkpoint_sha256": null },
  "heatmap": null,
  "interpretation": null
}
```

Future `COMPLETED` shape (real model + compatible explainer; NOT produced by
this build):

```json
{
  "status": "COMPLETED",
  "reason": null,
  "explainer": { "name": "grad-cam-adapter-a", "version": "1", "technique": "grad-cam", "model_type": "efficientnet-b4" },
  "model": { "name": "efficientnet-b4", "version": "1.0.0", "checkpoint_sha256": "..." },
  "heatmap": { "available": true, "format": "png", "width": 224, "height": 224, "reference": "internal artifact ref" },
  "interpretation": { "target_label": "FAKE", "target_score": 0.87, "score_semantics": "sigmoid probability", "summary": "...", "limitation": "..." }
}
```

Contract rules:

- `status` ∈ `COMPLETED | UNAVAILABLE`. `UNAVAILABLE` MUST carry `reason`;
  `COMPLETED` MUST carry explainer + model + heatmap + interpretation.
- A heatmap is only valid when produced by an actual model execution. No
  `UNAVAILABLE` payload ever contains a heatmap or a numerical interpretation.
- `model` always mirrors the detection result's detector identity — the
  explanation corresponds to the SAME inference, never a separately loaded
  checkpoint.
- `target_score` is present only when the detector reported a real score and is
  always paired with `score_semantics` (same rule as detection).
- No fabricated activation maps, no region-influence claims without a real
  model execution, no fake confidence.

### 2.3e Evidence stage result (IMPLEMENTED, Phase 9)

No new endpoint. The `evidence` stage writes a structured, deterministic
payload to its `result_ref` (JSON), surfaced through `GET /api/v1/scans/{scan_id}`
(`data.stages[]`). It aggregates the persisted results of the fingerprint,
metadata, detection, forensics, and XAI stages into one normalized evidence
view. Example (this build: no detector model, no C2PA parser):

```json
{
  "status": "COMPLETED",
  "methodology": { "version": "1", "aggregation": "evidence-count", "correlation": "dedupe-by-group", "confidence": "sufficiency-based; non-numeric" },
  "availability": {
    "FINGERPRINT": "AVAILABLE",
    "METADATA": "AVAILABLE",
    "DETECTION": "UNAVAILABLE",
    "VISUAL_FORENSICS": "AVAILABLE",
    "XAI": "UNAVAILABLE"
  },
  "evidence": [
    { "code": "fingerprint.sha256", "source": "FINGERPRINT", "category": "FILE_INTEGRITY", "evidence_type": "VERIFIED", "observation": "Byte-level SHA-256 fingerprint was computed for the stored file", "interpretation": "SHA-256 uniquely identifies the file bytes; it verifies file integrity, never authenticity", "direction": "NEUTRAL", "correlation_group": null, "details": { "sha256": "...", "size_bytes": 123 } }
  ],
  "summary": {
    "total": 6,
    "independent_count": 5,
    "by_evidence_type": { "HEURISTIC": 1, "VERIFIED": 5 },
    "by_direction": { "NEUTRAL": 6 },
    "by_category": { "FILE_INTEGRITY": 1, "METADATA_CONSISTENCY": 0, "PROVENANCE": 2, "VISUAL_ANOMALY": 3 }
  },
  "correlation": {
    "groups": ["visual-compression"],
    "note": "ELA and frequency analyzers are both influenced by JPEG compression and form the visual-compression group; XAI explains the same detector inference and forms the model-inference group. Within a group only the first item counts toward independent_count, so correlated signals are never treated as fully independent."
  },
  "confidence": {
    "status": "INSUFFICIENT_EVIDENCE",
    "value": null,
    "semantics": "Confidence reflects the strength and consistency of available evidence supporting an assessment, not the probability that the media is fake.",
    "reasons": ["no calibrated probability model exists in this build; a numeric confidence would be fabricated, not computed", "sufficiency is reported, never a probability", "DETECTION evidence is unavailable", "XAI evidence is unavailable"]
  },
  "limitations": ["DETECTION evidence is unavailable: detection produced no model prediction in this build", "XAI evidence is unavailable: xai produced no model explanation in this build", "METADATA: C2PA provenance is unavailable: not implemented in this build"]
}
```

Contract rules:

- `status` is always `COMPLETED` when the stage runs: UNAVAILABLE/FAILED
  sources are recorded in `availability` and `limitations` and never fail the
  aggregation.
- `source` ∈ `FINGERPRINT | METADATA | DETECTION | VISUAL_FORENSICS | XAI`;
  `category` ∈ `FILE_INTEGRITY | PROVENANCE | METADATA_CONSISTENCY |
  VISUAL_ANOMALY | MODEL_BEHAVIOR | SYNTHETIC_GENERATION | AUTHENTICITY` (no
  MANIPULATION category exists in this build);
  `direction` ∈ `UNKNOWN | NEUTRAL | SUPPORTING_AUTHENTICITY |
  SUPPORTING_MANIPULATION | SUPPORTING_SYNTHETIC | SUPPORTING_EDITING_HISTORY`.
- `evidence_type` reuses the shared EvidenceType taxonomy (VERIFIED /
  INFERENCE / HEURISTIC / UNKNOWN) — never a competing scheme.
- UNAVAILABLE/FAILED sources are honest states, never negative evidence.
  Absence of metadata is never evidence of AI generation.
- `confidence.status` is always `INSUFFICIENT_EVIDENCE` and `confidence.value`
  is always `null` in this build: no validated probability model exists, so a
  numeric confidence would be fabricated. `SUFFICIENT_EVIDENCE` is reserved for
  a future validated methodology.
- Deterministic: identical pipeline results produce byte-identical payloads.

### 2.3f Decision stage results (IMPLEMENTED, Phase 10)

No new endpoints. The `confidence`, `risk`, and `verdict` stages each write a
structured, deterministic payload to their `result_ref` (JSON), surfaced
through `GET /api/v1/scans/{scan_id}` (`data.stages[]`). They consume only the
persisted `evidence` result (and each other's results) and never re-run
analysis. Example (this build):

```json
{
  "confidence": {
    "status": "COMPLETED",
    "confidence_status": "INSUFFICIENT_EVIDENCE",
    "value": null,
    "semantics": "Confidence reflects the strength and consistency of available evidence supporting an assessment — never the probability that the media is fake. In this build no validated, calibrated methodology is registered, so confidence is INSUFFICIENT_EVIDENCE and carries no numeric value.",
    "basis": [
      { "code": "fingerprint.sha256", "source": "FINGERPRINT", "category": "FILE_INTEGRITY", "evidence_type": "VERIFIED", "direction": "NEUTRAL", "correlation_group": null, "directional": false, "dimension": "UNKNOWN" }
    ],
    "by_dimension": { "AUTHENTIC": 0, "MANIPULATED": 0, "SYNTHETIC": 0, "UNKNOWN": 6 },
    "reasons": ["all evidence items are neutral observations; none supports any assessment direction", "no calibrated confidence methodology is registered in this build; numeric and qualitative confidence levels are not emitted", "evidence methodology version 1; correlation groups considered: [\"visual-compression\"]"],
    "limitations": ["DETECTION evidence is unavailable; absence is not negative evidence and cannot reduce confidence", "XAI evidence is unavailable; absence is not negative evidence and cannot reduce confidence"],
    "methodology_version": "1"
  },
  "risk": {
    "status": "COMPLETED",
    "risk_level": "UNDETERMINED",
    "value": null,
    "semantics": "Risk reflects how concerning/actionable an established assessment is for review. It is never an authenticity probability, never equal to confidence, and never derived from a raw detector score. With no directional assessment established, risk cannot be determined.",
    "basis": [],
    "reasons": ["confidence is not SUFFICIENT_EVIDENCE; no directional assessment is established, so risk cannot be determined"],
    "limitations": [],
    "methodology_version": "1"
  },
  "verdict": {
    "status": "COMPLETED",
    "verdict": "INSUFFICIENT_EVIDENCE",
    "semantics": "The verdict is the final defensible conclusion of the pipeline. It is never stronger than the evidence: without a validated methodology and a directional assessment, the honest verdict is INSUFFICIENT_EVIDENCE.",
    "basis": [
      { "code": "fingerprint.sha256", "source": "FINGERPRINT", "category": "FILE_INTEGRITY", "evidence_type": "VERIFIED", "direction": "NEUTRAL", "correlation_group": null, "directional": false, "dimension": "UNKNOWN" }
    ],
    "reasons": ["confidence is not SUFFICIENT_EVIDENCE; no defensible conclusion can be reached"],
    "limitations": [],
    "methodology_version": "1"
  }
}
```

Contract rules:

- `confidence_status` ∈ `INSUFFICIENT_EVIDENCE | SUFFICIENT_EVIDENCE`. This
  build ALWAYS emits `INSUFFICIENT_EVIDENCE` with `value = null`.
  `SUFFICIENT_EVIDENCE` is reserved for a validated methodology and is never
  emitted. A detector score is a model output with its own `score_semantics`,
  never a calibrated probability.
- `dimension` ∈ `AUTHENTIC | MANIPULATED | SYNTHETIC | UNKNOWN` is a derived,
  documented classification of what each evidence item may lean toward — never
  a verdict. Editing-history evidence maps to `MANIPULATED`, never `SYNTHETIC`.
- `risk_level` ∈ `UNDETERMINED | LOW | MEDIUM | HIGH | CRITICAL`. This build
  ALWAYS emits `UNDETERMINED` with `value = null`: an arbitrary weight/score
  formula would fabricate risk, so it is never used.
- `verdict` ∈ `INSUFFICIENT_EVIDENCE | INCONCLUSIVE | LIKELY_AUTHENTIC |
  LIKELY_MANIPULATED | LIKELY_SYNTHETIC`. This build ALWAYS emits
  `INSUFFICIENT_EVIDENCE`. The `LIKELY_*` levels require a validated
  methodology; manipulation and synthetic generation are distinct verdicts.
- Decision stages fail safely: a missing/failed/unparseable `evidence` or
  `confidence` result still COMPLETES toward `INSUFFICIENT_EVIDENCE` /
  `UNDETERMINED` — it never fails the scan.
- `status` is always `COMPLETED` when a decision stage runs; `report` consumes
  these results and is described in §2.3g.
- Deterministic: identical pipeline results produce byte-identical payloads.

### 2.3g Report stage result (IMPLEMENTED, Phase 11)

No new endpoints. The `report` stage consumes the persisted results of the ten
prior stages (§2.3–§2.3f) — it never re-runs analysis, never re-opens the
image, and never recomputes confidence/risk/verdict. It writes a
`ReportResult` to its `result_ref` (JSON) and stores the PDF artifact at
`storage_dir/reports/{scan_id}.pdf`, surfaced through
`GET /api/v1/scans/{scan_id}` (`data.stages[]`). Report status is `COMPLETED`
or `FAILED`; it is unrelated to verdict strength (a `COMPLETED` report can
carry an `INSUFFICIENT_EVIDENCE` verdict).

```json
{
  "status": "COMPLETED",
  "format": "pdf",
  "version": "1",
  "reference": "018f9a77-b2ef-4c1a-8d0f-8a1c2d3e4f5a.pdf",
  "artifact": {
    "format": "pdf",
    "reference": "018f9a77-b2ef-4c1a-8d0f-8a1c2d3e4f5a.pdf",
    "size_bytes": 5213,
    "available": true
  },
  "document": {
    "report_version": "1",
    "case_id": "scan-...",
    "media_id": "media-...",
    "created_at": "2026-08-16T11:00:00.000Z",
    "analyzed_at": "2026-08-16T12:00:00.000Z",
    "media_type": "IMAGE",
    "original_filename": "sample.png",
    "size_bytes": 2048,
    "mime_type": "image/png",
    "pipeline_status": "COMPLETED",
    "summary": "The available analysis produced insufficient evidence for a stronger authenticity or manipulation conclusion. Confidence is not quantified: no validated, calibrated methodology is registered in this build. Risk could not be determined because no directional assessment was established. No detector model was available, so model-based synthetic-generation analysis was not performed. No explainability heatmap was generated because no compatible detector/explainer was available.",
    "sections": [
      { "title": "Case Information", "rows": [ { "label": "Case ID", "value": "scan-..." } ], "statements": [] },
      { "title": "Executive Summary", "rows": [], "statements": ["The available analysis produced insufficient evidence for a stronger authenticity or manipulation conclusion."] },
      { "title": "Pipeline Status", "rows": [ { "label": "validate", "value": "COMPLETED" } ], "statements": [] },
      { "title": "Fingerprint", "rows": [ { "label": "SHA-256", "value": "<hex>" } ], "statements": [] },
      { "title": "Metadata", "rows": [ { "label": "Provenance Status", "value": "UNAVAILABLE" } ], "statements": [] },
      { "title": "Detection", "rows": [ { "label": "Status", "value": "UNAVAILABLE" } ], "statements": ["No detector model was available; no prediction, score, probability or model identity is reported."] },
      { "title": "Visual Forensics", "rows": [ { "label": "ela measurements", "value": "{\"ela_mean\": 0.5, \"ela_std\": 0.1}" } ], "statements": [] },
      { "title": "XAI", "rows": [ { "label": "Status", "value": "UNAVAILABLE" } ], "statements": ["No explainability heatmap was generated."] },
      { "title": "Evidence Aggregation", "rows": [ { "label": "Source: FINGERPRINT", "value": "AVAILABLE" } ], "statements": [] },
      { "title": "Confidence", "rows": [ { "label": "Value", "value": "NOT QUANTIFIED" } ], "statements": [] },
      { "title": "Risk", "rows": [ { "label": "Risk Level", "value": "UNDETERMINED" } ], "statements": [] },
      { "title": "Verdict", "rows": [ { "label": "Verdict", "value": "INSUFFICIENT_EVIDENCE" } ], "statements": [] }
    ],
    "limitations": [
      "METADATA: C2PA provenance is unavailable: not implemented in this build",
      "DETECTION: detection produced no model prediction in this build",
      "XAI: xai produced no model explanation in this build",
      "DETECTION evidence is unavailable; absence is not negative evidence and cannot reduce confidence",
      "XAI evidence is unavailable; absence is not negative evidence and cannot reduce confidence",
      "detector unavailable: no image detector is registered in this build",
      "XAI unavailable: no detector model produced a prediction; XAI requires a real model inference to explain",
      "confidence not calibrated: no validated, calibrated methodology is registered in this build",
      "risk methodology cannot produce a supported level without an established directional assessment",
      "verdict remains insufficient: not enough validated evidence for a stronger conclusion",
      "visual forensic measurements are observational and content-dependent",
      "no face/identity assessment was performed in this build"
    ],
    "methodology": {
      "confidence_methodology_version": "1",
      "detector": "UNAVAILABLE",
      "detector_checkpoint_sha256": "UNAVAILABLE",
      "detector_model": "UNAVAILABLE",
      "detector_model_version": "UNAVAILABLE",
      "detector_preprocessing_version": "UNAVAILABLE",
      "detector_version": "UNAVAILABLE",
      "forensic_analyzer_versions": "{\"ela\": \"1\", \"frequency\": \"1\", \"noise\": \"1\"}",
      "report_version": "1",
      "risk_methodology_version": "1",
      "verdict_methodology_version": "1",
      "xai_explainer": "NOT IMPLEMENTED",
      "xai_explainer_version": "NOT IMPLEMENTED",
      "xai_technique": "NOT IMPLEMENTED"
    }
  },
  "summary": "The available analysis produced insufficient evidence for a stronger authenticity or manipulation conclusion. Confidence is not quantified: no validated, calibrated methodology is registered in this build. Risk could not be determined because no directional assessment was established. No detector model was available, so model-based synthetic-generation analysis was not performed. No explainability heatmap was generated because no compatible detector/explainer was available.",
  "limitations": []
}
```

Contract rules:

- `status` ∈ `COMPLETED | FAILED`. The stage only FAILS on render/persist
  errors; missing upstream results are reported as unavailable, never failed.
- `format` ∈ `pdf` (a `report-document`/plain-text form is reserved) and
  `version` is `"1"`.
- `reference` and `artifact.reference` are server-generated safe storage
  references (plain filenames inside the report storage root) — never absolute
  filesystem paths, never client-controlled.
- The `document.sections` (12 in this build), `methodology` keys, and
  `limitations` order are deterministic; identical inputs ⇒ byte-identical
  `result_ref` and PDF.
- Presentation rules (enforced and tested): `null` confidence renders as
  `NOT QUANTIFIED`, never `0` or a percentage; `UNAVAILABLE` detector/XAI/
  provenance states carry their real reason; a detector score is shown with
  its `score_semantics` and is never called confidence/probability; no
  heatmaps, charts, risk gauges, model identity, filesystem paths, secrets, or
  legal/admissibility claims are ever included.

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

### 4.1 Detector interface (Python, `app/inference/base.py`, IMPLEMENTED Phase 6)

```python
class DetectorIdentity(BaseModel):
    name: str
    detector_version: str = DETECTOR_CONTRACT_VERSION   # "1"
    model_name: str | None = None
    model_version: str | None = None
    checkpoint_sha256: str | None = None
    preprocessing_version: str | None = None

class DetectionPrediction(BaseModel):
    label: str                    # min length 1
    score: float                  # 0..1
    score_semantics: str          # e.g. "sigmoid probability"; raw logits prohibited
    class_list: tuple[str, ...] | None = None

class InferenceSummary(BaseModel):
    status: Literal["AVAILABLE", "UNAVAILABLE"]
    reason: str | None = None
    device: str | None = None
    duration_ms: int | None = None

class DetectionResult(BaseModel):
    detector: DetectorIdentity
    media_type: MediaType
    prediction: DetectionPrediction | None = None
    inference: InferenceSummary
    evidence_type: EvidenceType | None = None   # INFERENCE only with a prediction

class Detector(Protocol):
    name: str
    media_type: MediaType
    @property
    def identity(self) -> DetectorIdentity: ...
    def detect(self, path: Path, *, device: str) -> DetectionResult: ...
```

`DetectorRegistry` (`app/inference/registry.py`) holds detectors by name
(duplicate names rejected); `find(media_type)` returns the first detector for a
media type. This build ships `UnavailableDetector` only
(`app/inference/detectors/`), so `find(IMAGE)` always returns an honest
UNAVAILABLE result. Future detectors register in
`build_default_detector_registry()`.

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
| 2026-08-16 | Phase 5: metadata stage contract §2.3a (extraction/normalization, evidence-classified consistency findings, provenance UNAVAILABLE, result_ref JSON shape); `scan_stages.result_ref` widened to TEXT |
| 2026-08-16 | Phase 6: detection stage contract §2.3b + AI/ML interface §4.1 implemented (Detector protocol, DetectionResult schema, score_semantics rule, UNAVAILABLE semantics); detector registry; detect stage after metadata |
| 2026-08-16 | Phase 7: forensics stage contract §2.3c (measurements-only payload, per-analyzer status, VERIFIED/HEURISTIC findings, no authenticity probability); forensics stage after detect |
| 2026-08-16 | Phase 8: XAI stage contract §2.3d (UNAVAILABLE when no real detector model; heatmap only from actual model execution; same-inference guarantee); xai stage after forensics |
| 2026-08-16 | Phase 9: evidence stage contract §2.3e (normalized EvidenceItem model reusing EvidenceType, availability map with honest UNAVAILABLE/FAILED, correlation dedupe, INSUFFICIENT_EVIDENCE non-numeric confidence); evidence stage after xai |
| 2026-08-16 | Phase 10: decision stage contracts §2.3f (confidence/risk/verdict result_ref payloads; always INSUFFICIENT_EVIDENCE / UNDETERMINED / INSUFFICIENT_EVIDENCE in this build, no fabricated numeric confidence/risk/verdict; EvidenceReference basis with derived dimension; fail-safe dependency reading); confidence/risk/verdict stages after evidence; report still SKIPPED |
| 2026-08-16 | Phase 11: report stage contract §2.3g (ReportResult + ReportDocument + PDF artifact; consumes persisted outputs only, never re-runs analysis; COMPLETED/FAILED unrelated to verdict strength; deterministic sections/methodology/limitations; NOT QUANTIFIED/UNAVAILABLE/UNDETERMINED/INSUFFICIENT_EVIDENCE presentation rules; internal-only storage_path; no heatmaps/charts/model identity/paths/secrets/legal claims); report stage after verdict, none SKIPPED |
