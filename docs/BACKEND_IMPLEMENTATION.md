# PHANTOM PHOENIX — Backend Implementation Record & Architecture Blueprint

> Phase 0 document. Engineering record — updated continuously as implementation progresses.
> Last updated: 2026-08-16 (Phase 9)

---

## 1. Purpose

PHANTOM PHOENIX is a Digital Media Authenticity & AI Forensic Intelligence Platform.
The backend is the central orchestration layer for the analysis pipeline:

```
UPLOAD → CREATE SCAN → MEDIA VALIDATION → AI/DEEPFAKE DETECTION →
FORENSIC ANALYSIS → METADATA ANALYSIS → VISUAL ANALYSIS → AI ATTRIBUTION →
EXPLAINABLE AI → EVIDENCE AGGREGATION → CONFIDENCE → RISK ASSESSMENT →
FINAL VERDICT → FORENSIC REPORT → PDF DOWNLOAD
```

The central question is not "is this media fake?" but:

> What can we determine about the authenticity, manipulation, origin, and forensic
> characteristics of this media, and what evidence supports the conclusion?

### Scientific honesty principle

**Classifier confidence is NOT forensic truth.** A 99% model prediction is not a 99%
probability that the media is fake. The system must preserve the distinction between:

1. **VERIFIED EVIDENCE** — established from provenance/authentic metadata/C2PA.
2. **MODEL INFERENCE** — output of a detector; bounded by training distribution.
3. **HEURISTIC EVIDENCE** — computed signal with known false-positive behavior.
4. **UNKNOWN** — no defensible signal.

Never fabricate evidence, heatmaps, accuracy, datasets, or results.

---

## 2. Repository & Environment Baseline (verified 2026-08-15)

| Item | Status |
| --- | --- |
| Working directory | `/home/hari007/Projects/git projects/MainProject/Backend` (project root, not nested) |
| Git | initialized, remote `origin` = `https://github.com/Phantom773-del/major-project-Deepfake-Detection` |
| Branches | `main` (current work branch) and `backend` (kept separate by team-leader instruction) |
| Python | 3.14.6 (`/usr/bin/python3`), pip 26.0.1 |
| Package manager | uv 0.12.2 (`/home/hari007/.local/bin/uv`) |
| Docker | 29.6.2, Compose 5.3.1; `postgres:16-alpine` image already pulled locally |
| PostgreSQL host service | NOT running — no `psql`, port 5432 closed. Dev DB runs via Docker. |
| Working tree | clean (Phase 1 committed) |

### Tooling decisions

- **uv** for dependency management + virtual environments (`pyproject.toml` + `uv.lock`).
- **PostgreSQL via Docker Compose** for all local development and testing.
- **Python 3.14** locked as the project runtime (decision below).

### Runtime decision: Python 3.14 (decided 2026-08-15, empirical)

Phase 1 verified compatibility empirically rather than by assumption. The full anticipated
dependency set was dry-resolved with `uv` against CPython 3.14 and 3.12:

| Dependency | Resolves on 3.14.6 |
| --- | --- |
| FastAPI, Pydantic v2, SQLAlchemy 2.x, psycopg3, Alembic, uvicorn | Yes |
| pytest, pytest-asyncio, httpx, ruff, mypy | Yes |
| torch 2.13.0, numpy 2.5.2, pillow 12.3.0 (future ML/forensics) | Yes |
| reportlab, pyjwt, pwdlib, defusedxml, imagehash (future milestones) | Yes |

No 3.14 compatibility blockers found for the current or planned dependency set.
**Decision: Python 3.14 is the project runtime** for local dev and Docker
(`requires-python = ">=3.14,<3.15"`, `.python-version` = `3.14`, enforced via uv).

### Package management decision

`uv` only: `pyproject.toml` declares ranges; `uv.lock` pins exact versions; `uv sync --frozen`
is reproducible. No extra libraries added without a current-milestone need. Quality tooling
(`ruff`, `mypy`) configured in `pyproject.toml`.

---

## 2a. Phase 1 Foundation — Implementation Status

Status: **COMPLETED and validated** (pytest 17 passed, ruff clean, mypy strict clean,
Alembic upgrade applied, live uvicorn `/api/v1/health` → 200).

### Sync vs async decision: ASYNC (decided 2026-08-15)

The application uses the **async SQLAlchemy 2.x stack with psycopg3** (`create_async_engine`,
`async_sessionmaker`, `AsyncSession`). Rationale: consistent async FastAPI architecture,
psycopg3 supports async cleanly, ML work later runs in worker threads anyway. Alembic
migrations use a **sync engine** (`app/db/migrations/env.py`) sourcing the same URL from
settings — standard practice, documented.

### What was implemented

- **Project skeleton**: all Phase 0 packages created under `app/` with minimal `__init__.py`
  (no fake implementations). `alembic.ini`, `docker-compose.yml`, `.env.example`, README.
- **Application factory** `create_app()` (`app/main.py`): metadata/title/version, v1 router
  mount, CORS middleware, exception handlers, lifespan (runtime dirs on start, engine
  dispose on shutdown). Global `app = create_app()` for uvicorn.
- **Configuration** (`app/core/config.py`): pydantic-settings `Settings` + `get_settings()`
  singleton; env-driven; categories for app/db/auth/storage/http. `.env.example` committed;
  no `.env` ever.
- **Logging** (`app/core/logging.py`): minimal console handler; never logs secrets, tokens,
  media contents or full request bodies.
- **Exceptions** (`app/domain/exceptions.py`, `app/api/errors.py`): `AppError` base with
  stable `code`/`status_code`; `NotFoundError`, `ConflictError`, `ValidationFailure`;
  envelope responses; 500 sanitized (stack logged, never returned). Registered handlers for
  `AppError`, `RequestValidationError`, Starlette `HTTPException`, and `Exception`.
- **API versioning**: `/api/v1` prefix; `GET /api/v1/health` returns the envelope contract.
- **Database foundation** (`app/db/base.py`, `app/db/session.py`): `Base` with naming
  convention, async `engine` + `SessionFactory`, `get_db` dependency, `dispose_engine`.
  Transaction boundary: one `AsyncSession` per request via the dependency.
- **Alembic**: `alembic.ini` + `app/db/migrations/` (env.py sync engine, `Base.metadata`
  target); baseline revision `98d0662cb87f` applied; `alembic upgrade head` verified.
- **Docker dev env**: `docker compose up -d postgres` → `postgres:16-alpine`, named volume,
  port 5432, env-driven credentials, healthcheck (verified healthy).
- **Testing** (`tests/`): app factory, health contract, config loading, DB infrastructure
  (real `phantom_test` PG), exception behavior. `pytest` 17 passed.
- **Linting/typing**: `ruff` (E,F,I,UP,B,S) and `mypy --strict` (pydantic plugin) pass.

### Future provider boundaries (documented now, not implemented)

- **DetectionProvider** — runs a detector model, returns normalized predictions
  (task, label, confidence, model name/version, limitations, `is_simulation` flag).
- **XAIProvider** — produces real explainability artifacts (e.g., Grad-CAM) + summaries;
  never synthesized heatmaps.
- **ForensicProvider** — computes visual forensic signals; returns evidence records
  (module, category, strength, evidence_type, location, limitations).
- **AttributionProvider** — returns attribution class + confidence + method from a
  validated evidence source; never claims exact generator without evidence.

All four are consumed through stable backend/domain schemas (`app/schemas/`), never
model-specific internal objects, so frontend contracts stay stable across model swaps.

### Report architecture rule (documented)

Database/domain data → **Report assembler** → canonical `ForensicReport` DTO → **Renderer**
→ PDF. The PDF renderer must depend only on the canonical DTO, never directly on database
models. Implemented in the reports milestone.

### Evidence architecture rule (documented)

Future evidence records must preserve: source, category, result, strength, evidence type,
reliability, explanation, limitations, method/version, timestamp, and where applicable
location/region. They must distinguish `VERIFIED_EVIDENCE`, `MODEL_INFERENCE`,
`HEURISTIC_EVIDENCE`, `UNKNOWN`. Not yet implemented.

---

## 2b. Phase 2 — Core Domain Persistence (implementation status 2026-08-15)

First real vertical slice: domain models → DB → Alembic migration → repository →
service → schema → API → tests. Establishes the persistent forensic case record.
Pipeline results/evidence/assessment tables are NOT created yet (later milestones).

### Entity responsibilities

| Entity | Responsibility |
| --- | --- |
| `ModelVersion` | Registered AI/ML model version (name, version, task, framework, status, JSONB configuration). Multiple versions of one model name coexist; `(name, version)` unique. No accuracy claims stored. |
| `Media` | Metadata record for uploaded media (filename, media type, MIME, size, SHA-256, dimensions, storage reference, deletion state). Binary never in PG. `original_filename` recorded but never trusted. |
| `Scan` | Central forensic case record: one analysis request against one Media. Orchestration only — pipeline results live in later tables. Owns lifecycle status + failure info + timestamps. |
| `ScanStage` | Per-pipeline-stage row (name, status, sequence, timestamps, duration_ms, error, optional result_ref). Rows, not schema → new stages addable without migration. |

### Relationships

```text
Media
  ↓ 1:N  (scans.media_id FK RESTRICT)
Scan
  ↓ 1:N  (scan_stages.scan_id FK CASCADE, delete-orphan)
ScanStage

ModelVersion  (independent registry — no FK from core tables yet)
```

`Scan.media` unidirectional from Scan side. `Scan.stages` ordered by `sequence`
(`cascade=all, delete-orphan`). No unnecessary bidirectional relationships.

### Schema (migration `0dfc71182341`, on `Base.metadata`)

- `model_versions`: id uuid pk, name(128), version(64), task(64), framework(64)?
  status enum `model_version_status`(ACTIVE/DEPRECATED/ARCHIVED), configuration JSONB,
  created_at, UNIQUE(name, version).
- `media`: id uuid pk, original_filename(255), media_type enum `media_type`
  (IMAGE/VIDEO/UNKNOWN), mime_type(127)?, size_bytes?, sha256(64) INDEXED?,
  width?, height?, storage_path(512), is_deleted bool default false, deleted_at?,
  created_at.
- `scans`: id uuid pk, media_id FK `media.id` RESTRICT, status enum `scan_status`
  (CREATED/VALIDATING/QUEUED/PROCESSING/COMPLETED/FAILED), started_at?,
  completed_at?, error_message(500)?, created_at, updated_at.
- `scan_stages`: id uuid pk, scan_id FK `scans.id` CASCADE, name(64), status enum
  `stage_status` (PENDING/RUNNING/COMPLETED/FAILED/SKIPPED), sequence int,
  started_at?, completed_at?, duration_ms?, error_message(500)?, result_ref(255)?,
  created_at, UNIQUE(scan_id, name).

Conventions preserved: UUID PKs generated app-side, `timestamptz` (timezone-aware
UTC via `DateTime(timezone=True)`), `server_default now()`, native PG enums,
Alembic-owned schema, sync engine for migrations.

### Scan state machine (`app/domain/scan.py`, single source of truth)

```text
CREATED ──► VALIDATING ──► QUEUED ──► PROCESSING ──► COMPLETED
              │                       │
              └───► FAILED ───────────┘   (terminal, no retry yet)
```

- Allowed: CREATED→VALIDATING; VALIDATING→{QUEUED, FAILED}; QUEUED→PROCESSING;
  PROCESSING→{COMPLETED, FAILED}. COMPLETED and FAILED are terminal.
- Retry policy: NOT supported yet — `FAILED` has no outgoing transitions.
  Documented decision; retries are a future milestone.
- Enforced in the service layer (`ScanService.transition`), never in API routes.
  Invalid transitions raise `ConflictError` → 409 `CONFLICT`.

### Pipeline stage order (`STAGE_ORDER`)

`validate, fingerprint, metadata, detect, forensics, xai, evidence, confidence,
risk, verdict, report` — created as PENDING rows at scan creation. Adding a stage
later = editing one tuple; no migration.

### Migration

- `0dfc71182341 add core domain persistence (model_versions, media, scans, scan_stages)`.
- Baseline untouched (`98d0662cb87f`). `env.py` now imports all models so
  autogenerate diffs the real schema.
- Verified from a clean database state: scratch DB → `alembic upgrade head` →
  all 4 tables + enums present → dropped.

### Repository design (`app/repositories/`)

- Tiny generic `Repository[T]` base (create, get) — shared by concrete repos.
- Concrete: `ModelVersionRepository` (list_all, list_active, get_by_name_version),
  `MediaRepository` (list_all paginated), `ScanRepository` (get with eager
  media+stages, paginated list + count, add_stage, set_stage_status, set_status).
- Persistence only; no business rules. Eager loading (`joinedload`/`selectinload`)
  used in async paths to avoid lazy-load `MissingGreenlet`.

### Service design (`app/services/scans.py`)

`ScanService`: create_scan (validates media exists → 404, builds case + 11 pending
stages), get_scan (404 if missing), list_scans (paginated, optional status filter),
transition (state machine + timestamp/error bookkeeping), mark_stage (stage
status updates; unknown stage → 404; FAILED stage requires error message → 409).
API routes call service then commit; never set status directly.

### API design (`/api/v1`)

- `POST /api/v1/media` — minimal record creation (no upload). `storage_path` accepted
  on input, never on output. Replaced by secure upload milestone later.
- `POST /api/v1/scans` — create case record (201, full detail incl. media + stages).
- `GET /api/v1/scans/{id}` — detail. 404 `NOT_FOUND` if missing.
- `GET /api/v1/scans?page&page_size&status` — paginated list, `meta.pagination`.
- All responses wrapped in `Envelope[T]`; errors enveloped with stable codes.

### Pydantic schemas (`app/schemas/`)

`ModelVersionCreate/Read`, `MediaCreate/Read` (no storage_path on read),
`ScanCreate`, `ScanRead`, `ScanDetail` (media + stages), `ScanStageRead`, plus
`Pagination` in `common.py`. ORM models never exposed directly.

### Testing

Real PostgreSQL (`phantom_test`). 51 tests pass (17 Phase 1 + 34 new):
- Models: creation, relationships, cascade delete, unique `(name, version)`.
- Migrations: tables, enums and columns exist after upgrade.
- Repositories: create/get/list/update for all three repos.
- Service: valid path CREATED→…→COMPLETED, failure transition, paramatised
  invalid transitions, terminal FAILED (no retry), same-status rejection,
  stage lifecycle, unknown stage, fail-without-error.
- API: create media, create scan (201 + 11 stages), get detail, list pagination +
  status filter, 404 media/scan, 422 validation (bad uuid, bad sha256).
- Test DB isolated via session migration fixture; schema restored after
  `create_all/drop_all` round-trip test.

### Decisions

- `(name, version)` unique on model_versions; task is a string (open registry,
  no enum churn), status is a native enum.
- Stages as rows keyed by unique `(scan_id, name)` — extensible without migrations.
- `FAILED` terminal: no retry invented; documented as limitation.
- Native PG enums via SQLAlchemy `Enum`; `StrEnum` for domain taxonomy.
- `updated_at` on Scan only (the mutable aggregate); static entities carry
  `created_at` only.

### Limitations (this milestone)

- No file upload, no SHA-256/fingerprint computation from real files.
- No AI inference, no result/evidence/assessment tables.
- No auth; endpoints open (auth is a separate milestone).
- `FAILED` scans cannot retry.
- Media `list_all` returns count via separate COUNT query (fine at this scale).

### Completed work (files)

`app/domain/taxonomy.py`, `app/domain/scan.py`, `app/db/base.py` (mixins),
`app/db/models/{__init__,model_version,media,scan}.py`, `app/repositories/{base,
model_version,media,scan}.py`, `app/services/scans.py`, `app/schemas/{model_version,
media,scan}.py`, `app/api/v1/endpoints/{media,scans}.py`, migration `0dfc71182341`,
tests `test_{models,migrations,repositories,scan_service,api_scans}.py`, docs.

---

## 2c. Phase 3 — Secure Media Ingestion & Fingerprinting (implementation status 2026-08-16)

Replaces the Phase 2 temporary JSON media-creation endpoint with a real upload
workflow. Scope: safe ingestion + byte-level fingerprinting only. No AI analysis,
no metadata intelligence, no attribution, no forensics.

### Upload architecture

```
Client
  ↓ multipart POST /api/v1/media/upload
API route (thin, app/api/v1/endpoints/media.py)
  ↓
MediaService.create_from_upload()        (app/services/media.py)
  ↓ validate filename
  ↓ stream to temp file + size limit + SHA-256 (one pass)
  ↓ detect content: magic bytes + Pillow safe parse (threaded)
  ↓ reject extension/content mismatch
  ↓ persist to storage under generated name (threaded)
  ↓ insert Media row + commit
  ↓ on commit failure: best-effort delete stored file
StorageProvider (app/media/storage.py)
  ↓
LocalStorageProvider (filesystem)        ← future: S3/object storage provider
```

The route only wires an `UploadFile` into the service; all business logic lives in
`MediaService`. The service owns its own short transaction (no request-scoped
session), so cleanup semantics stay self-contained.

### StorageProvider abstraction

- `StorageProvider` protocol: `persist(source: Path, *, name: str) -> str`,
  `delete(ref: str) -> None`. Returns an internal storage reference string.
- `LocalStorageProvider` initial implementation:
  - files written under the configured `media_storage_root`;
  - `persist` rejects any name that is not a single safe path component
    (`name == Path(name).name`), preventing traversal even from generated names;
  - `os.replace` (atomic move) from the temp dir into storage.
- Storage is never inside the source package (`storage/` is root-anchored
  gitignored). Cloud/object storage deliberately deferred; swapping providers
  requires no media-domain changes.

### Validation strategy (ordering)

1. Filename: non-empty, single path component (no `/`, `\`), ≤ 255 UTF-8 bytes.
   Stored as metadata only — never used to build a filesystem path.
2. Size: streamed in 64 KB chunks against `max_upload_size_bytes`; the stream is
   cut off the moment the limit is exceeded (never fully buffered).
3. Content detection (authoritative, server-side): magic-byte signature, then
   Pillow `Image.open(...)` + `verify()` for safe parse; dimensions from the
   decoded image header. Parser exceptions are converted to a sanitized
   `INVALID_CONTENT` error — internals never leak.
4. Extension match: filename suffix must be in the detected format's allowlist
   (e.g. `PNG → {.png}`). Mismatch → `INVALID_CONTENT`.
5. The client `Content-Type` is never trusted: detected MIME type is what is
   stored, regardless of the client header. A client MIME that conflicts with
   actual content does not fail the upload on its own — the detected type and the
   extension rule are the enforcement point.

### Supported media formats (explicit allowlist)

| Format | MIME | Extensions | Media type |
| --- | --- | --- | --- |
| JPEG | `image/jpeg` | `.jpg` `.jpeg` `.jpe` | IMAGE |
| PNG | `image/png` | `.png` | IMAGE |
| WebP | `image/webp` | `.webp` | IMAGE |

Video is NOT supported at this milestone: there is no real video pipeline in the
system yet, so MP4 is rejected rather than silently accepted. Accepting a format
the pipeline cannot process would be dishonest ingestion.

### Size policy

- Config: `MAX_UPLOAD_SIZE_MB` (default 50 MB dev-conservative), exposed as
  `max_upload_size_bytes`. Not hard-coded in the route.
- Oversized uploads → 400 `FILE_TOO_LARGE`.

### SHA-256 fingerprint

- Computed over the raw uploaded bytes (streamed, chunked — never loaded whole),
  one pass while writing the temp file. Independent of filename/MIME/metadata/pixels.
- Populates `Media.sha256` (existing indexed column).
- **Meaning:** equal SHA-256 = identical file bytes. It does NOT mean identical
  visual content and must never be claimed as such.

### Duplicate policy

**Allow duplicates; each upload creates a separate Media record.** Chosen because
(1) simplest and least surprising, (2) preserves auditability (each upload is an
independent event with its own provenance), (3) near-duplicate/visual-matching is
a later forensics concern, not ingestion. Documented — no silent dedup semantics.

### Image dimensions

`width`/`height` come from server-side decode. Client-supplied dimensions do not
exist in the API at all (nothing to trust). Video dimensions deferred until a
real video ingestion path exists.

### Temp files

- Temp files live under `<media_storage_root>/tmp/` with `mkstemp`-generated
  `upload-*` names (never user filenames).
- Always removed in a `finally`; on success the file was already atomically moved
  into storage, so the unlink is a no-op.
- No partially-uploaded file is ever treated as completed media.

### Transaction / failure semantics (honest)

Ordering: validate → fingerprint → write file → insert row → commit.

| Failure | Behavior |
| --- | --- |
| Validation/detection fails | temp file removed; nothing permanent written |
| Storage fails | no DB insert happens (no committed record); temp removed |
| DB commit fails after storage | stored file is deleted best-effort; error re-raised |

Filesystem + PostgreSQL are NOT atomically consistent: if the process dies in the
window between `persist` and `commit`, an orphan file can remain. This is an
acknowledged limitation; all handled failure paths clean up, an orphan-sweep job
is future work.

### Security controls

- Untrusted-input posture: size limit, magic-byte + safe parse, generated storage
  names (UUID hex + detected extension), path-traversal rejection, no arbitrary
  paths, no executable storage semantics (media root is data-only).
- Sanitized errors: `MediaUploadError` maps to stable codes; parser internals and
  server paths never reach the client.
- `storage_path` is internal only — never returned in `MediaRead`.
- No file contents or absolute paths in logs.

### API surface

`POST /api/v1/media/upload` (multipart) — see `docs/API_CONTRACTS.md` §2.2c. The
temporary `POST /api/v1/media` was removed; there is exactly one way to create a
Media record and the client cannot supply `storage_path`, `sha256`, or dimensions.

### Error codes (upload)

`EMPTY_FILE`, `FILE_TOO_LARGE`, `UNSUPPORTED_TYPE`, `INVALID_CONTENT`,
`INVALID_FILENAME` (all 400 `VALIDATION_FAILURE` family, via `MediaUploadError`).

### Object-storage migration path

Implement a second `StorageProvider` (S3-compatible). `persist` returns an object
key instead of a relative path; `Media.storage_path` already stores an opaque
internal reference, so no media-domain or API changes are needed. Local temp-file
flow stays identical.

### Completed work (files)

`app/media/{storage,detection,hashing}.py`, `app/services/media.py`,
`app/api/v1/endpoints/media.py` (upload route), `app/schemas/media.py`
(`MediaRead` only), `app/core/config.py` (storage/size/allowlist settings),
`app/domain/exceptions.py` (`MediaUploadError`), `.env.example`,
tests `test_{media_upload,api_scans,config}.py`, `tests/conftest.py`, docs.

---

## 2d. Phase 4 — Analysis Worker, Pipeline Runner, Fingerprint Stage (implementation status 2026-08-16)

Moves the scan lifecycle from creation (`CREATED`) through a real execution path:
`CREATED → VALIDATING → QUEUED → PROCESSING → COMPLETED/FAILED`. Implements the
in-process worker, the stage registry/pipeline runner, and the `validate` +
`fingerprint` stages with real behavior. No AI detection, forensics, metadata
intelligence, or XAI in this milestone — those stages are `SKIPPED` with an
explicit reason, never faked.

### Flow

```
POST /api/v1/media/upload ──> Media row (Phase 3)
POST /api/v1/scans        ──> Scan CREATED + 11 PENDING ScanStage rows
[manual/queue trigger]    ──> ScanService.transition → VALIDATING → QUEUED
AnalysisWorker.run_once   ──> claim oldest QUEUED scan (FOR UPDATE SKIP LOCKED)
                                 └─> transition → PROCESSING (committed atomically)
ScanExecutionService      ──> load PROCESSING scan, run pipeline, finalize
PipelineRunner            ──> iterate STAGE_ORDER; run registered, SKIP the rest
  validate   ──> media_type check, storage resolve, file exists, sha256 match
  fingerprint──> re-hash stored file, dHash (64-bit), size → result_ref JSON
ScanExecutionService      ──> COMPLETED (or FAILED with client-safe message)
```

### Worker design (`app/workers/queue.py`)

- `AnalysisWorker` (v1): in-process scheduling loop, replaceable by Celery later
  (AGENTS rule). Methods: `run_once` (claim + execute one scan, returns 0/1),
  `run_until_idle` (test/tooling helper), `run_forever` (poll loop for the app
  task, catches and logs per-iteration exceptions).
- **Claiming is race-safe**: `SELECT ... WHERE status = 'QUEUED' ORDER BY
  created_at LIMIT 1 FOR UPDATE OF scans SKIP LOCKED` (with `joinedload(media)` +
  `selectinload(stages)`). Locking only `scans` (not the joined side — PostgreSQL
  rejects `FOR UPDATE` on the nullable side of an outer join), so even multiple
  worker processes could never claim the same scan. The claim then transitions
  `QUEUED → PROCESSING` and commits before handing off.
- `ScanExecutionService` (`app/services/execution.py`) owns one transaction per
  scan: loads the claimed scan, requires `PROCESSING` (raises `ConflictError`
  otherwise), runs the pipeline, then finalizes `COMPLETED` or `FAILED`
  (`PipelineFailure` → client-safe message; unexpected exceptions → generic
  "unexpected pipeline failure"). Both paths commit.
- Opt-in via `ANALYSIS_WORKER_ENABLED` (default `false`) so the API never
  auto-processes by surprise; poll interval `ANALYSIS_WORKER_POLL_INTERVAL_SECONDS`
  (default 1.0s). Enabled in `app/main.py` lifespan as a cancelled-on-shutdown
  `asyncio` task.

### Stage contract (`app/workers/stages/base.py`)

- `Stage` protocol: `name: str` + `async run(ctx: StageContext) -> StageResult | None`.
- `StageContext`: scan, media, storage (`StorageProvider`), settings.
- `StageError`: a stage-local failure; message is client-safe. The runner
  translates it into a `FAILED` stage row with `error_message` set.
- `StageResult(result_ref)`: optional JSON pointer stored on the stage row.
- New stages register through `StageRegistry.register(stage)` (rejects duplicate
  names) and `build_default_registry()` composes the active set. A stage in
  `STAGE_ORDER` with no registered implementation is marked `SKIPPED` with
  `"'<name>' stage not implemented in this build"` — explicit, never fabricated.

### Implemented stages (real behavior)

- **validate** (`app/workers/stages/validate.py`): media must be `IMAGE`
  (videos unsupported this milestone); storage ref resolves inside the storage
  root (traversal rejected); the stored file exists; `sha256_of_file` matches
  `Media.sha256` exactly.
- **fingerprint** (`app/workers/stages/fingerprint.py`): re-hashes the stored
  file chunked (SHA-256), computes a 64-bit dHash
  (`app/media/perceptual.py`, pure Pillow: grayscale → 9×8 LANCZOS → adjacent-pixel
  comparison → 16-hex-char string), records `size_bytes`. Result written as
  `result_ref` JSON `{"sha256", "d_hash", "size_bytes"}`.
- dHash is structural similarity only — never proof of identical provenance, and
  never presented as forensic truth (scientific-honesty rule).

### Failure semantics (honest)

- Missing stored file → `validate` fails → scan `FAILED` with
  `"stored media file is missing"`; the failed stage carries the message.
- Stored-file SHA-256 mismatch vs the media record → scan `FAILED` with
  `"stored media sha256 mismatch"` (defensive integrity check, covered by test).
- Failure is terminal (state machine has no retry path in v1). An unexpected
  exception mid-pipeline leaves `PROCESSING` un-finalized only if the process
  crashes before the finalizer; the row stays `PROCESSING` (orphan) and the next
  worker will not re-claim it — documented limitation for the in-process worker.

### Testing (95 tests total)

- `tests/test_worker.py`: registry contents/duplicate rejection; pipeline order;
  claim → COMPLETED with validate+fingerprint COMPLETED and other stages SKIPPED
  (with explicit reason); fingerprint `result_ref` is real JSON; idle returns 0;
  non-`QUEUED` scans ignored; each scan processed exactly once (incl. two
  concurrent workers via `asyncio.gather` — SKIP LOCKED guarantees no double
  claim); `PROCESSING` scans never re-claimed; missing-file and sha256-mismatch
  → FAILED; `execute` on non-PROCESSING raises `ConflictError`; full API path
  (upload → create scan → transition → worker → GET COMPLETED).
- `tests/test_perceptual.py`: determinism, 16-hex format, different images →
  different hashes (gradients, since solid fills hash identically).
- `ScanRepository.get` is authoritative (`populate_existing`) — reloads reflect
  worker mutations even within one long-lived session.

### Completed work (files)

`app/workers/{queue,runner,registry}.py`, `app/workers/stages/{base,validate,fingerprint}.py`,
`app/services/execution.py`, `app/media/perceptual.py`,
`app/repositories/scan.py` (`result_ref` + authoritative get),
`app/services/scans.py` (`mark_stage(..., result_ref)`), `app/main.py`
(opt-in worker task), `app/core/config.py` (worker settings), `.env.example`,
tests `test_{worker,perceptual,config}.py`, docs.

---

## 2e. Phase 5 — Metadata Intelligence Stage (implementation status 2026-08-16)

Implements the `metadata` pipeline stage: real, normalized metadata extraction
(EXIF / XMP / GPS / ICC, dimensions, format) from the stored file, plus a small
set of defensible consistency checks. The stage writes a structured, deterministic
JSON payload to `ScanStage.result_ref`. Metadata is **evidence, not a verdict** —
the stage never decides REAL/FAKE/AI-GENERATED/MANIPULATED.

### Scope (explicit)

- **In scope:** metadata extraction, normalization, presence/absence reporting,
  evidence-classified consistency findings, provenance unavailability, result
  contract.
- **Out of scope this milestone (never fabricated):** C2PA/manifest provenance
  parsing (reported as `provenance.status: "UNAVAILABLE"` with an explicit note),
  AI detection, attribution, visual forensics, XAI, risk, verdict, reports.
- No new API endpoint and no new database table — the result flows through the
  existing scan/stage endpoints via `result_ref`.

### Extraction (`app/metadata/extractor.py`)

- Wraps **Pillow only** (`PIL.Image`, `ExifTags`, `getxmp`). `defusedxml` was
  added so `getxmp()` can parse XMP safely (Pillow refuses otherwise): pure-Python,
  secure XML with no entity expansion. No other metadata libraries.
- `extract_image_metadata(path) -> ExtractedMetadata`:
  `format`, `mode`, `width`, `height`, `icc_profile_present`, normalized
  `ExifMetadata`, `XmpMetadata`, `GpsMetadata`, and `extractor_errors`.
- EXIF: stable canonical tag ids (make, model, orientation, software, date-time,
  date-time-original, exposure time, f-number, ISO, flash, focal length, copyright,
  image description, artist, lens make/model, white balance). GPS via the GPSInfo
  IFD (`deg/min/sec` rationals → signed decimal degrees; altitude in metres;
  date stamp).
- XMP: Pillow's `getxmp()` result drilled into the RDF `Description` —
  `CreatorTool`, `CreateDate`, `ModifyDate`, `MetadataDate`, `creator`, `rights`,
  `title`, `description`, `format`, `Software`. A malformed/hostile XMP packet is
  caught and recorded as an `extractor_error` — it never crashes the stage
  (verified by test with a deliberately broken packet).
- Timestamps are normalized `YYYY:MM:DD HH:MM:SS` → naive ISO 8601
  (`2023-05-04T10:11:12`). EXIF carries no timezone, so the output has no offset
  and never assumes UTC. Malformed timestamps → `null` + `extractor_error`.
- Bounds: text truncated at 1000 chars, lists capped at 10 entries.
  `DecompressionBombError` (Pillow's pixel-bomb guard) is caught and surfaced as
  a client-safe error.
- Extraction is strictly read-only (no modification, no thumbnail writes).

### Consistency analysis (`app/metadata/analyzer.py`)

`analyze_metadata(extracted, recorded_mime=...) -> tuple[Finding, ...]`, findings
sorted by code. Every finding is evidence-classified via the `EvidenceType` enum
(`app/domain/taxonomy.py`: `VERIFIED`, `INFERENCE`, `HEURISTIC`, `UNKNOWN`):

| Code | Evidence | Meaning |
| --- | --- | --- |
| `exif_orientation_out_of_range` | VERIFIED | EXIF orientation outside the valid 1–8 range |
| `capture_later_than_modification` | HEURISTIC | capture timestamp later than the modification timestamp; contradictory, but not manipulation on its own |
| `gps_present` | VERIFIED | GPS coordinates present (privacy-sensitive) |
| `editing_software_metadata` | VERIFIED | known editor string in EXIF/XMP software; the message explicitly states this does not establish AI generation |
| `format_mime_mismatch` | VERIFIED | detected image format disagrees with the recorded mime type |

Consistency checks only ever combine values actually parsed from the file — no
invented cross-checks, no thresholds that claim forensic truth.

### Result contract (`app/metadata/result.py`, `result_ref` JSON)

Stable shape (documented in `docs/API_CONTRACTS.md` §2e):
`format`, `mode`, `dimensions {width, height}`, `exif` (each field `null` when
absent), `gps`, `xmp`, `icc`, `presence {exif, xmp, icc, gps}`,
`software` (EXIF+XMP merged, deduplicated, capped), `consistency {findings, count}`,
`provenance {status: "UNAVAILABLE", note}`, `extractor {library, errors}`.
Serialized with `sort_keys=True` — output is deterministic for identical input
(covered by test). Absent metadata yields `null`/empty values, never placeholders.

### Stage + pipeline integration

- `app/workers/stages/metadata.py` (`MetadataStage`, `name = "metadata"`):
  guards `MediaType.IMAGE` (`StageError` otherwise); resolves the storage ref
  (traversal rejected); missing file → `StageError("stored media file is missing")`;
  runs extraction off the event loop (`asyncio.to_thread`); `MetadataExtractionError`
  → client-safe `StageError` (no paths/tracebacks); analyzes + builds payload →
  `StageResult(result_ref=json.dumps(payload, sort_keys=True))`.
- Registered in `build_default_registry()` after `fingerprint`. Order within
  `STAGE_ORDER` is preserved: `validate → fingerprint → metadata` (test-asserted).
- `ScanStage.result_ref` widened `VARCHAR(255) → TEXT` (migration
  `ba9f064f0acf`); the `metadata` payload would not fit in 255 chars.

### Security / privacy

- Metadata is read-only; `defusedxml` bounds XML parsing; `DecompressionBombError`
  caught; text/list bounds cap hostile payloads.
- GPS presence is explicitly flagged (`gps_present` finding) as privacy-sensitive.
- Storage refs stay internal; client-supplied Content-Type is never trusted for
  parsing (server-side content detection is authoritative).

### Testing (Phase 5: +28 tests, total 123)

`tests/test_metadata.py` (fixtures crafted from raw bytes, incl. `tests/_exif_builder.py`
which builds TIFF-format EXIF/GPSIFD bytes Pillow cannot write): registry +
ordering; JPEG EXIF values; JPEG without EXIF; PNG extraction; GPS values
(signed decimal degrees, altitude, date stamp); timestamp normalization to naive
ISO; XMP extraction; software merge/dedupe; ICC presence flag; editing-software
VERIFIED finding; capture-vs-modification HEURISTIC finding; orientation range;
GPS presence; clean file → zero findings; format/mime mismatch; missing file;
corrupt image; client-safe error text; non-image media rejected; malformed
metadata non-fatal (recorded in `extractor.errors`); malformed XMP non-fatal;
result structure + provenance `UNAVAILABLE`; no fabricated fields; evidence-type
set; determinism; worker e2e (metadata COMPLETED with real payload); corrupt-file
worker failure.

### Completed work (files)

`app/metadata/{extractor,analyzer,result}.py`, `app/workers/stages/metadata.py`,
`app/domain/taxonomy.py` (`EvidenceType`), `app/db/models/scan.py` (`result_ref`
→ `TEXT`), migration `ba9f064f0acf`, `pyproject.toml` (`defusedxml`),
tests `test_{metadata,_exif_builder}.py`, docs.

---

## 2f. Phase 6 — Detection Intelligence (implementation status 2026-08-16)

### Objective

Production-grade detector abstraction: a stable `Detector` contract, an
ordered `DetectorRegistry`, a structured `DetectionResult` payload, model
identity/version tracking, and a `detect` pipeline stage that runs after
`metadata`. Honest UNAVAILABLE state when no model exists — the pipeline never
fabricates a prediction.

### Reality check (Phase 1 docs ≠ shipped code)

Phase 0 documented a `Prediction`/`Detector` protocol and an EfficientNet-B4
image detector. At Phase 6 start: `app/inference/__init__.py` was empty, no
torch/torchvision/numpy in `pyproject.toml`, and no checkpoints/weights existed
anywhere in the repo. Therefore this phase implements the abstraction plus an
explicit `UnavailableDetector`; a real model is NOT integrated and is NOT
claimed to be.

### Detector contract (`app/inference/base.py`)

- `DETECTOR_CONTRACT_VERSION = "1"` — version of the contract, not the model.
- `DetectorError(message)` — client-safe inference error (message returned as-is
  in `StageError`; internal tracebacks go to logs only).
- `DetectorIdentity` — `name`, `detector_version` (defaults to contract version),
  optional `model_name`, `model_version`, `checkpoint_sha256`,
  `preprocessing_version`. Identity is never invented: optional fields are
  `None` unless a real detector supplies them.
- `DetectionPrediction` — `label` (min length 1), `score` (0..1),
  `score_semantics` (required, e.g. `"sigmoid probability"` — raw logits are not
  a probability and are never reported as one), optional `class_list`.
- `InferenceSummary` — `status` (`AVAILABLE`/`UNAVAILABLE`), `reason`, `device`,
  `duration_ms`.
- `DetectionResult` — `detector` (identity), `media_type`, `prediction | None`,
  `inference`, `evidence_type` (`INFERENCE` only when a real prediction exists;
  `None` for UNAVAILABLE).
- `Detector` protocol — `name`, `media_type`, `identity` property, sync
  `detect(path, *, device) -> DetectionResult` raising `DetectorError`.
  Inference runs off the event loop via `asyncio.to_thread`; a detector must
  never block the API event loop.

### Registry (`app/inference/registry.py`)

`DetectorRegistry` mirrors `StageRegistry`: `register` (duplicate name →
`ValueError`), `get`, `find(media_type)` (first detector serving the type),
`names`, `__contains__`, `__len__`. No global mutable registry — composed per
pipeline.

### Detectors (`app/inference/detectors/`)

- `unavailable.py` — `UnavailableDetector`: name `"unavailable"`, media_type
  IMAGE, always returns `status=UNAVAILABLE`, `prediction=None`,
  `evidence_type=None`, reason `"no image detector is registered in this build"`,
  model fields `None`. Honest placeholder, never a fabricated result.
- `__init__.py` — `build_default_detector_registry()` registers only the
  UnavailableDetector in this build. Future real detectors register here.

### Detection stage (`app/workers/stages/detect.py`)

- `DetectionStage(name="detect")`; runs after `metadata` per `STAGE_ORDER`.
- IMAGE-only guard (validate rejects non-IMAGE earlier); storage path resolved
  and existence-checked (mirrors metadata stage).
- `detector = detectors.find(media_type)`; `None` → `StageError` (cannot happen
  with default registry since UnavailableDetector is always registered).
- Inference via `asyncio.to_thread(detector.detect, path, device=device)`;
  `device` from `Settings.detection_device` (`"cpu"` MVP; `cuda:N` honored only
  by detectors that support it).
- `DetectorError` → `StageError` → stage FAILED / scan FAILED. Unexpected
  exceptions logged, client-safe message returned.
- Result serialized to `result_ref` via existing TEXT column — **no new table,
  no migration** (consistent with metadata stage).

### Decision: no torch dependency

No checkpoint exists to load, so adding torch (~800 MB) was rejected as an
unjustified dependency. When a real model lands, the dependency is added with
the model files and the registry gains the real detector.

### Settings

`Settings.detection_device: str = "cpu"` (env `DETECTION_DEVICE`), documented
in `.env.example`.

### Testing (Phase 6: +20 tests, total 143)

`tests/test_detection.py` with `StubDetector`/`FailingDetector` test doubles:
contract shape; `DetectionPrediction`/`DetectionResult` validation (empty label,
score out of range, empty score_semantics rejected); registry register/lookup/
duplicate/find-by-media-type/unsupported-type; default registry resolves
UnavailableDetector; unavailable detector never fabricates prediction; stage
registered after metadata + pipeline order; stage with default registry →
UNAVAILABLE payload; stage with stub → AVAILABLE prediction; client-safe
inference failure; video rejected; missing file; CPU device passed through;
exact `result_ref` structure + determinism; worker e2e (unavailable payload,
stub prediction, detection error → scan FAILED). `tests/test_worker.py` +
`tests/test_metadata.py` updated: `detect` is COMPLETED (was SKIPPED).

### Completed work (files)

`app/inference/base.py`, `app/inference/registry.py`,
`app/inference/detectors/{__init__,unavailable}.py`,
`app/workers/stages/detect.py`, `app/workers/stages/__init__.py`,
`app/core/config.py`, `.env.example`, tests `test_detection.py` +
`test_{worker,metadata}.py` updates, docs.

### Limitations (honest)

- No real detector/model in this build; all detection output is UNAVAILABLE.
- `evidence_type=INFERENCE` marks model inference only — never treated as
  verified truth (AGENTS.md scientific-honesty rules).
- No score calibration, no accuracy claims, no generator/checkpoint recovery.
- Device selection is per-settings; no auto GPU detection yet.

---

## 2g. Phase 7 — Visual Forensics Engine (implementation status 2026-08-16)

Implements the `forensics` pipeline stage: measurable, deterministic
image-level forensic observations from three analyzers (ELA, noise residual,
frequency domain). The engine produces **measurements, never verdicts** — no
REAL/FAKE/AI-GENERATED probability, no authenticity score, no "manipulated"
label. Findings are evidence-classified; interpretations are always
`HEURISTIC` supporting signals. The stage runs independently of `detect`: a
UNAVAILABLE detector does not block forensics.

### Scientific warning (mandatory context)

Previous experimentation showed generic signals (ELA, noise, frequency) produce
false positives on normal photos. Therefore no analyzer converts a measurement
into an authenticity probability. ELA error, noise residuals, and spectral
shape vary substantially with normal camera processing, JPEG compression,
resizing, denoising, content, post-processing, and social-media transforms.
**Measurement ≠ verdict.**

### Architecture

```
app/forensics/
    base.py       ForensicError, ForensicAnalyzer Protocol (name, media_type, version, analyze)
    registry.py   ForensicAnalyzerRegistry (register/get/for_media_type/names, dup rejected)
    result.py     ForensicFinding (code, evidence_type, message), AnalyzerResult,
                  build_forensic_payload
    image.py      bounded grayscale loading: validate_image_size + load_grayscale
    analyzers/
        __init__.py   build_default_forensic_analyzer_registry() (ela, noise, frequency)
        ela.py        ErrorLevelAnalyzer
        noise.py      NoiseResidualAnalyzer
        frequency.py  FrequencyAnalyzer
app/workers/stages/forensics.py   VisualForensicsStage
```

New analyzers register in `app/forensics/analyzers/__init__.py` without touching
the pipeline.

### Analyzer contract

- `name` (stable, registered once), `media_type`, `version`.
- `analyze(path, *, settings) -> AnalyzerResult`; raises `ForensicError`
  (client-safe message) on failure.
- Never writes to the database; deterministic for identical bytes + settings.
- `AnalyzerResult`: `analyzer`, `version`, `status` (`COMPLETED`/`FAILED`),
  `measurements`, `parameters`, `findings`, `error`.

### Analyzer algorithms and parameters

1. **ELA** (`ela`, version 1). Two-pass recompression probe: bounded grayscale
   decode → JPEG encode at `quality` → decode → JPEG encode again → decode →
   `abs(pass1 - pass2)`. Measurements: `mean_abs_error`, `max_error`,
   `p95_error`, `p99_error`, `error_ratio`. Parameter: `ela_jpeg_quality`
   (default 80). A uniform image yields exactly zero error; JPEG inputs retain
   their own compression history. ELA depends on compression history and
   content — high ELA is NOT proof of manipulation.
2. **Noise residual** (`noise`, version 1). Grayscale − Gaussian blur
   (`noise_blur_radius`, default 1.0). Measurements: `residual_mean`,
   `residual_std`, `residual_energy` (mean of squares), `p99_abs_residual`,
   `nonzero_ratio`. A uniform image yields exactly zero residual. Noise depends
   on sensor, ISO, compression, denoising, resizing, content, editing history —
   high/low residual is NOT proof of AI generation.
3. **Frequency** (`frequency`, version 1). 2D FFT (mean-subtracted grayscale),
   shifted spectrum, radial energy bands: low < 0.1·min_dim, mid to 0.3·min_dim,
   high beyond (module constants `_LOW_FRACTION`/`_MID_FRACTION`), plus
   normalized spectral entropy (256 power-histogram bins, `_ENTROPY_BINS`).
   Measurements: `low_energy_ratio`, `mid_energy_ratio`, `high_energy_ratio`,
   `spectral_entropy`. No frequency signature proves AI generation.

### Stage behavior

- IMAGE-only guard; storage path resolved/existence-checked (mirrors metadata).
- Image-level failure (unreadable / decompression bomb / over pixel cap) →
  `StageError` → stage FAILED / scan FAILED.
- Per-analyzer failure is isolated: that analyzer records `status=FAILED` +
  `error`; the others still run; the stage COMPLETES (e.g. ELA COMPLETED,
  noise FAILED, frequency COMPLETED). Unexpected exceptions are logged and
  recorded as `unexpected analyzer failure`.
- Empty analyzer registry → `StageError` (misconfiguration, not silent success).
- Result written to the stage's `ScanStage.result_ref` (existing TEXT column) —
  **no new table, no migration**.

### Result payload (see API_CONTRACTS §2.3c for full shape)

```json
{
  "image": { "format": "PNG", "width": 64, "height": 64, "mode": "L" },
  "summary": { "analyzers": 3, "completed": 3, "failed": 0 },
  "analyzers": {
    "ela": {
      "analyzer": "ela", "version": "1", "status": "COMPLETED", "error": null,
      "parameters": { "quality": 80 },
      "measurements": { "mean_abs_error": 0.0, "max_error": 0, "p95_error": 0.0,
                        "p99_error": 0.0, "error_ratio": 0.0 },
      "findings": [
        { "code": "ela_measured", "evidence_type": "VERIFIED", "message": "..." },
        { "code": "ela_interpretation", "evidence_type": "HEURISTIC", "message": "..." }
      ]
    }
  }
}
```

Float values are rounded to 6 decimal places. Every analyzer emits one VERIFIED
measurement finding and one HEURISTIC interpretation finding (supporting
signal only — never an authenticity claim).

### Image safety / resource bounds

- Images are untrusted: decode is capped at `forensics_max_pixels`
  (default 8 000 000) via `validate_image_size` BEFORE decoding, in addition to
  Pillow's built-in `MAX_IMAGE_PIXELS` decompression-bomb guard.
- Only grayscale (`L`) decoding is exposed; the cap guarantees the FFT input
  (float64) and its complex spectrum stay bounded (~64 MB and ~128 MB
  respectively at the default cap).
- No full-size intermediate images are persisted; only compact scalar summaries
  go into `result_ref`. No temp files (ELA uses in-memory `BytesIO`).

### Determinism

Identical input bytes + identical settings → identical payload (verified by
tests). Analyzer parameters are explicit (no hidden knobs): ELA quality,
noise blur radius, frequency band fractions/entropy bins, pixel cap.

### Settings

`forensics_max_pixels` (int, 8 000 000), `ela_jpeg_quality` (int, 80),
`noise_blur_radius` (float, 1.0) — all in `Settings` and `.env.example`
(`FORENSICS_MAX_PIXELS`, `ELA_JPEG_QUALITY`, `NOISE_BLUR_RADIUS`).

### Dependencies

Added `numpy>=2.0,<3.0`. Genuinely required for the 2D FFT and array
statistics — no stdlib FFT exists. OpenCV/scipy/scikit-image were deliberately
not added. Pillow was already present and is reused for decoding/filtering.

### Testing (Phase 7: +36 tests, total 179)

`tests/test_forensics.py` with deterministic synthetic images (uniform gray,
gradient, checkerboard, seeded noise, JPEG-compressed variants). Covers:
analyzer contract; registry register/lookup/duplicate/media-type; default
registry; per-analyzer determinism; uniform images → zero ELA error and zero
noise residual; noisy image → higher residual energy; gradient → low-freq
dominated, checkerboard → high-freq dominated; measurement bounds (ratios sum
to 1, entropy in [0,1], ELA bounds); invalid/garbage images → `ForensicError`;
pixel-cap enforcement (analyzer + stage); missing file; video rejection; stage
registered after detection + pipeline order; result_ref structure; stage
determinism; isolated analyzer failure (FAILED + others COMPLETED); unexpected
exception isolation; all-fail completes with structured errors; empty registry
fails; forensics runs when detection is UNAVAILABLE (worker e2e); worker e2e
with a failing analyzer still COMPLETES. `tests/test_worker.py`,
`tests/test_detection.py`, `tests/test_metadata.py` updated for the new stage.

### Completed work (files)

`app/forensics/{base,registry,result,image}.py`,
`app/forensics/analyzers/{__init__,ela,noise,frequency}.py`,
`app/workers/stages/forensics.py`, `app/workers/stages/__init__.py`,
`app/core/config.py`, `.env.example`, `pyproject.toml` (numpy),
tests `test_forensics.py` + `test_{worker,detection,metadata}.py` updates, docs.

### Limitations (honest)

- Measurements only; no authenticity/verdict interpretation in this phase.
- ELA/noise/frequency are content- and history-dependent — false-positive
  signals on natural images are expected and documented.
- Frequency bands and entropy bins are module constants (documented, not yet
  settings); only pixel cap, ELA quality, and blur radius are configurable.
- No video forensics; no evidence aggregation (Phase 9).

---

## 2h. Phase 8 — Explainable AI / XAI Engine (implementation status 2026-08-16)

Implements the `xai` pipeline stage: explainability for a *genuine* detector
inference. The XAI layer answers, once a real model exists, "which regions of
this image influenced the detector's prediction". Because NO detector model
exists in this build, every XAI result is honestly `UNAVAILABLE` with an
explicit reason — the pipeline never fabricates a heatmap.

### Scientific rule (critical)

A heatmap is only valid if it comes from an actual model execution. The XAI
layer never generates random or visually pleasing placeholder heatmaps, never
derives "activation maps" from ELA/frequency analysis or arbitrary regions, and
never claims a region influenced a prediction no model produced. If no
compatible model exists, XAI status MUST be `UNAVAILABLE` with a clear reason —
an honest system state, not an error.

### Architecture

```
app/xai/
    base.py        XAIError, ExplainerIdentity, XAIModelIdentity, XAIHeatmap,
                   XAIInterpretation, XAIResult, XAIExplanationContext,
                   XAIExplainer Protocol
    registry.py    XAIExplainerRegistry (register/get/find by media_type +
                   model_type, dup rejected)
    explainers/
        __init__.py      build_default_xai_explainer_registry()
        unavailable.py   UnavailableExplainer (honest UNAVAILABLE fallback)
app/workers/stages/xai.py   XAIStage
```

### Explainer contract

- `name`, `version`, `technique` (e.g. `grad-cam`), `media_type`,
  `model_type` (`None` = any/unavailable fallback).
- `explain(path, *, context: XAIExplanationContext, settings) -> XAIResult`;
  raises `XAIError` (client-safe) on failure.
- Never writes to the database; the stage owns persistence to `result_ref`.

### Same-inference guarantee (critical)

`XAIExplanationContext` carries the exact `DetectionResult` the pipeline
produced PLUS the exact detector instance that produced it. The stage reads the
`detect` stage's persisted result from the scan, re-resolves the detector from
the SAME `DetectorRegistry` by name, and passes that instance to the explainer.
An explainer never independently loads a checkpoint that differs from the
detector's real model. Future model-specific adapters (Detector A →
GradCAMAdapterA, Detector B → GradCAMAdapterB) pull their target layers from the
detector instance; generic XAI code hard-codes no model internals.

### XAI result contract (see API_CONTRACTS §2.3d for full shape)

```json
{
  "status": "UNAVAILABLE",
  "reason": "no detector model produced a prediction; XAI requires a real model
             inference to explain (detection: no image detector is registered
             in this build)",
  "explainer": { "name": "unavailable", "version": "1",
                 "technique": "none", "model_type": null },
  "model": { "name": null, "version": null, "checkpoint_sha256": null },
  "heatmap": null,
  "interpretation": null
}
```

`COMPLETED` results (future) carry the explainer identity, the model identity
mirrored from the detection result, `heatmap` (available, format, width,
height, reference — a real artifact), and `interpretation` (target label, real
score with `score_semantics`, summary, limitation). No fake values are ever
included: an `UNAVAILABLE` result has no heatmap and no numerical
interpretation.

### Stage behavior

- IMAGE-only guard; storage path resolved/existence-checked (mirrors detect).
- Reads the detect stage's result_ref; missing/unparseable detection → honest
  `UNAVAILABLE` (never a stage failure).
- Re-resolves the detector by name; detector missing → `UNAVAILABLE`.
- Resolves an explainer via `find(media_type, model_name)`: exact
  `model_type` match wins, else the `model_type=None` unavailable fallback.
- UnavailableExplainer returns `UNAVAILABLE` with a reason derived from the
  actual detection state — never a fabricated heatmap/score.
- Real explainer failure → `StageError` (client-safe), same as detection.

### Grad-CAM status (honest)

Genuine Grad-CAM requires a differentiable model, a target convolutional/
feature layer, forward activation + gradients for a target score, gradient-
weighted activation, normalization, and resize to input dimensions. The current
detector is `UNAVAILABLE` and no model framework (PyTorch/TF) is installed, so
Grad-CAM is NOT implemented in this build and no fake abstraction pretends to
perform it. The explainer contract + per-detector adapter pattern is in place;
the Grad-CAM adapter ships only with a real, compatible detector model.

### Testing (Phase 8: +23 tests, total 203)

`tests/test_xai.py`: XAI result schema validation (status literal, score
bounds); registry register/lookup/duplicate/find (exact model_type wins, None
fallback, media type); UnavailableExplainer never fabricates (no heatmap/
interpretation/score for both unavailable detection and a real stub prediction);
stage registered after forensics; default stage → COMPLETED with UNAVAILABLE
payload; no-compatible-explainer UNAVAILABLE mentioning the model; missing/
unparseable detection → UNAVAILABLE; compatible stub explainer COMPLETED with
heatmap + same-detector-instance verification; video rejected; missing file;
explainer failure → client-safe StageError; result_ref structure; determinism;
worker e2e (default → xai COMPLETED/UNAVAILABLE; stub explainer → COMPLETED
with heatmap). `tests/test_worker.py`, `tests/test_detection.py`,
`tests/test_metadata.py` updated for the new stage.

### Completed work (files)

`app/xai/{base,registry}.py`, `app/xai/explainers/{__init__,unavailable}.py`,
`app/workers/stages/xai.py`, `app/workers/stages/__init__.py`,
tests `test_xai.py` + `test_{worker,detection,metadata}.py` updates, docs.

### Limitations (honest)

- No real explainer/heatmap in this build; all XAI output is UNAVAILABLE.
- Grad-CAM requires a real differentiable detector model (future phase).
- Heatmap artifact persistence/reference mechanics are designed but unexercised
  until a real explainer exists.
- `target_score` is only meaningful when the detector reports a real score.

---

## 2i. Phase 9 — Evidence Aggregation & Confidence Engine (implementation status 2026-08-16)

Implements the `evidence` pipeline stage: a normalized evidence layer that
consumes the persisted outputs of the fingerprint, metadata, detection, visual
forensics, and XAI stages and produces ONE deterministic evidence result. The
engine reuses the shared `EvidenceType` taxonomy (VERIFIED / INFERENCE /
HEURISTIC / UNKNOWN) — it never defines a competing classification — and it
never invents evidence, never treats UNAVAILABLE as a negative signal, and never
emits a numeric confidence it cannot defend.

### Phase 9 design note (written before implementation)

1. **Available evidence in this build**: fingerprint (SHA-256 + dHash + size),
   metadata (EXIF/XMP/ICC/GPS presence + consistency findings + software list),
   and visual forensics (ELA, noise residual, frequency measurements + findings).
2. **Unavailable evidence in this build**: detection (no image detector
   registered → UNAVAILABLE), XAI (no model inference to explain → UNAVAILABLE),
   and C2PA provenance (no parser → UNAVAILABLE). All three are recorded
   explicitly in the `availability` map with a reason — they are NOT evidence
   and they are NOT treated as negative evidence.
3. **Evidence types produced**: VERIFIED (fingerprint, metadata presence and
   measured findings, forensic measurements), HEURISTIC (dHash, timestamp
   inconsistency, forensic interpretations), INFERENCE (only when a real
   detector prediction or real XAI explanation exists — none in this build),
   UNKNOWN (reserved).
4. **Independence**: fingerprint, metadata, and visual forensics are treated as
   independent evidence streams for counting.
5. **Correlation (never double-count)**: ELA and frequency are both influenced
   by JPEG compression → `visual-compression` group. XAI explains the same
   detector inference → `model-inference` group with detection. Within a group
   only the FIRST item counts toward `independent_count`.
6. **What confidence can legitimately mean**: "the strength and consistency of
   available evidence supporting an assessment" — never "the probability that
   the media is fake".
7. **Is numeric confidence defensible? NO.** No validated probability model,
   no detector, no calibration data exist in this build. A numeric value would
   be fabricated, not computed. Therefore the aggregator ALWAYS emits
   `confidence.status = INSUFFICIENT_EVIDENCE`, `confidence.value = null`, with
   explicit reasons. `SUFFICIENT_EVIDENCE` exists as a status but is reserved
   for a future validated methodology and is never emitted by this build.

### Architecture

```
app/evidence/
    domain.py      EvidenceSource, EvidenceCategory, EvidenceDirection,
                   EvidenceAvailability, ConfidenceStatus, EvidenceItem,
                   EvidenceSummary, CorrelationNote, ConfidenceAssessment,
                   EvidenceMethodology, EvidenceResult
    normalizer.py  per-source normalize_source() -> NormalizedSource
    aggregator.py  aggregate_evidence(sources) -> EvidenceResult (deterministic)
app/workers/stages/evidence.py   EvidenceAggregationStage
```

### Normalization rules (honesty-critical)

- **Fingerprint** → `FILE_INTEGRITY`: SHA-256 = VERIFIED/NEUTRAL ("identifies
  file bytes; never authenticity"); dHash = HEURISTIC/NEUTRAL (near-duplicate
  support only).
- **Metadata** → `PROVENANCE` + `METADATA_CONSISTENCY`: presence AND absence
  are VERIFIED/NEUTRAL observations; absence wording explicitly states "not
  evidence of AI generation or manipulation". GPS presence is NEUTRAL (privacy
  observation, never authenticity). Software presence is NEUTRAL. Consistency
  findings keep the analyzer's `evidence_type`; editing-software and timestamp
  inconsistencies map to `SUPPORTING_EDITING_HISTORY` (heuristic — never
  manipulation); format/mime mismatch stays NEUTRAL. C2PA unavailable →
  limitation only, source still AVAILABLE.
- **Detection** → one INFERENCE item only when the detector itself marked the
  result `evidence_type = INFERENCE` AND a real prediction exists. Label FAKE →
  `SYNTHETIC_GENERATION`/`SUPPORTING_SYNTHETIC`, REAL →
  `AUTHENTICITY`/`SUPPORTING_AUTHENTICITY`; unknown labels stay NEUTRAL
  `MODEL_BEHAVIOR`. Details carry the full model identity (name, version,
  checkpoint, preprocessing) + score + `score_semantics` + device. Otherwise
  UNAVAILABLE — never a negative signal.
- **Forensics** → one VERIFIED/NEUTRAL item per COMPLETED analyzer
  (`VISUAL_ANOMALY`), reusing the analyzer's HEURISTIC interpretation finding as
  the item interpretation. Per-analyzer failures are recorded; a partial run is
  AVAILABLE, an all-failed run is FAILED — never fabricated as success.
- **XAI** → COMPLETED explanations become `MODEL_BEHAVIOR`/INFERENCE/NEUTRAL
  with technique + model identity + heatmap availability ("model behavior, not
  ground-truth manipulation evidence"). UNAVAILABLE → no items.

### Aggregation rules

- Consumes only persisted `result_ref` JSON from `Scan.stages` (never the
  stored file, never client input); a missing/unparseable/failed source is
  recorded as UNAVAILABLE/FAILED and the engine still COMPLETES.
- Deterministic: sources in pipeline order, items sorted by (source, code),
  counts sorted by key; identical inputs → identical result_ref.
- Correlation groups dedupe as in the design note; `independent_count` counts
  only non-duplicated items.
- `confidence` ALWAYS `INSUFFICIENT_EVIDENCE` / `value = null` with reasons
  (base reasons + unavailable sources). No numeric confidence, ever.

### Stage behavior

- IMAGE-only guard (mirrors detect/forensics/xai).
- Reads fingerprint/metadata/detect/forensics/xai `result_ref` from
  `ctx.scan.stages`; no storage path resolution (aggregation is pure
  consumption of persisted structured results).
- Never raises because one source was unavailable or failed.

### Testing (Phase 9: +49 tests, total 252)

`tests/test_evidence.py`: enum/domain validation (shared EvidenceType, no
MANIPULATION category); aggregation availability + confidence honesty (empty →
all UNAVAILABLE + INSUFFICIENT; still INSUFFICIENT even with all evidence
available; reasons list unavailable sources; availability map completeness;
UNAVAILABLE detection is not negative evidence; determinism; summary counts);
fingerprint/metadata/detection/forensics/xai normalization (including
metadata-absence-is-not-AI, GPS neutral, timestamp heuristic not manipulation,
detection model-identity propagation, per-analyzer failure, all-failed source);
correlation dedupe (visual-compression, model-inference); stage behavior
(COMPLETED with honest availability, no image file needed, missing/failed/
unparseable source isolation, real-prediction still no fabricated confidence,
determinism, video rejected, registered after xai); worker e2e (default pipeline
→ honest UNAVAILABLE detection/xai; stub detector → detection INFERENCE evidence
present yet confidence still INSUFFICIENT).

### Completed work (files)

`app/evidence/{__init__,domain,normalizer,aggregator}.py`,
`app/workers/stages/evidence.py`, `app/workers/stages/__init__.py` (evidence
registered after xai, 7 stages), tests `test_evidence.py` +
`test_{worker,detection,metadata,xai}.py` updates, docs.

### Limitations (honest)

- No numeric confidence and no SUFFICIENT_EVIDENCE in this build (see design
  note §7). `confidence` is descriptive only.
- Only categories backed by an implemented source exist; there is NO
  MANIPULATION category and no manipulation assessment anywhere.
- Detection/XAI evidence paths are implemented and tested via stub detectors but
  unexercised with a real model in this build.
- No evidence persistence beyond the stage `result_ref` (no new table).

---

## 3. Technology Stack

| Layer | Choice | Rationale |
| --- | --- | --- |
| Language | Python 3.14 | Available on dev machine |
| Web framework | FastAPI | Async, typed, OpenAPI out of the box |
| Validation | Pydantic v2 | API contracts as schemas |
| ORM | SQLAlchemy 2.x (declarative, typed) | Portable across PG providers |
| Migrations | Alembic | Versioned schema |
| Database | PostgreSQL 16 (Docker) | Production-appropriate |
| Auth | OAuth2 + JWT (PyJWT), Argon2id password hashing (pwdlib) | Standard, auditable |
| Media parsing | Pillow, NumPy, `python-multipart` | Image inspection/fingerprinting |
| Hashing | `hashlib` (SHA-256), image hashes (dHash/aHash) via pure-Python or `imagehash` | Integrity + near-duplicate detection |
| Metadata | Pillow EXIF; custom minimal XMP parser (or `defusedxml`) | No heavy runtime deps |
| Background work | FastAPI `BackgroundTasks` + in-process async worker (queue of `ScanJob`) | Simple, replaceable by Celery later |
| Testing | pytest, pytest-asyncio, httpx | Real behavior verification |
| PDF reports | ReportLab (pure Python) | Deterministic report generation |
| Server | uvicorn | Standard ASGI |

Dependencies are pinned in `pyproject.toml` (exact + lockfile). No Celery/Redis in Phase 2 v1.

---

## 4. Folder Structure (target)

```
Backend/
├── AGENTS.md
├── pyproject.toml
├── uv.lock
├── .env.example
├── .gitignore
├── docker-compose.yml
├── Dockerfile
├── README.md
├── docs/
│   ├── BACKEND_IMPLEMENTATION.md
│   └── API_CONTRACTS.md
├── alembic.ini
├── app/
│   ├── main.py                # FastAPI app factory, router mounting, startup/shutdown
│   ├── core/
│   │   ├── config.py          # pydantic-settings, env-driven
│   │   ├── security.py        # password hashing, JWT encode/decode
│   │   └── logging.py         # structured logging setup
│   ├── db/
│   │   ├── base.py            # DeclarativeBase + shared mixins
│   │   ├── session.py         # engine + session factory + get_db dependency
│   │   ├── models/            # SQLAlchemy models (one file per aggregate)
│   │   └── migrations/        # Alembic environment + versions/
│   ├── api/
│   │   ├── deps.py            # dependencies: get_current_user, get_db, role guards
│   │   └── v1/
│   │       ├── router.py      # versioned router aggregation
│   │       └── endpoints/
│   │           ├── auth.py
│   │           ├── users.py
│   │           ├── media.py
│   │           ├── scans.py
│   │           ├── results.py
│   │           ├── reports.py
│   │           └── admin.py
│   ├── schemas/               # Pydantic API contracts (mirrors API_CONTRACTS.md)
│   ├── repositories/          # data-access layer (per aggregate)
│   ├── services/              # orchestration + business logic
│   ├── domain/
│   │   ├── evidence.py        # evidence record + strength model
│   │   ├── confidence.py      # confidence aggregation engine
│   │   ├── risk.py            # risk engine
│   │   ├── verdict.py         # verdict engine
│   │   └── taxonomy.py        # enums: evidence types, risk levels, verdicts, statuses
│   ├── media/
│   │   ├── validation.py      # size/MIME/extension/content validation
│   │   ├── storage.py         # secure storage, temp files, cleanup, retention
│   │   └── fingerprint.py     # sha256, perceptual hash, dimensions
│   ├── metadata/
│   │   ├── exif.py            # EXIF extraction
│   │   ├── xmp.py             # XMP extraction (minimal, best-effort)
│   │   └── analyzer.py        # inconsistency detection
│   ├── inference/
│   │   ├── base.py            # Detector interface
│   │   ├── registry.py        # detector registry + model version tracking
│   │   └── detectors/         # concrete detectors (EfficientNet-B4 etc. later)
│   ├── forensics/             # visual forensic modules (each independent)
│   │   ├── registry.py        # module registry
│   │   ├── base.py            # ForensicModule interface
│   │   ├── ela.py             # error-level analysis
│   │   ├── noise.py           # noise residual analysis
│   │   ├── frequency.py       # frequency-domain analysis
│   │   └── quality.py         # quality/compression characteristics
│   ├── xai/
│   │   ├── base.py            # XAI provider interface
│   │   └── gradcam.py         # Grad-CAM integration (when real model available)
│   ├── reports/
│   │   ├── builder.py         # assemble report data from results
│   │   └── pdf.py             # ReportLab PDF generation
│   ├── audit/
│   │   └── logger.py          # audit log writer
│   └── workers/
│       ├── queue.py           # in-process ScanJob queue
│       └── runner.py          # pipeline orchestration per scan
└── tests/
    ├── unit/
    ├── service/
    ├── api/
    ├── database/
    ├── security/
    ├── pipeline/
    └── reports/
```

---

## 5. Database Architecture

### 5.1 Conventions

- PostgreSQL, schema default `public`, `uuid` PKs (`gen_random_uuid()`), `timestamptz` timestamps.
- All tables carry `created_at`; mutable aggregates carry `updated_at`.
- JSONB columns for flexible structured payloads (evidence details, model metadata).
- Enums stored as native PG enums via SQLAlchemy `Enum(..., native_enum=True)`.
- Alembic owns all schema changes; no manual DDL.
- No FK cascade hard-deletes without review — retain audit trail.

### 5.2 Domain model (target tables)

| Table | Purpose |
| --- | --- |
| `users` | id, email, password_hash, role (`user`/`admin`), is_active, created_at |
| `model_versions` | name, version, task (image_detection/video_detection/attribution/xai), architecture, status (`active`/`deprecated`/`archived`), notes, created_at |
| `media` | id, sha256, perceptual_hash, original_name, stored_path, size_bytes, mime_type, extension, width, height, duration_seconds (video), format, is_valid, created_at |
| `scans` | id, user_id FK, media_id FK, status, scan_type, error_message, started_at, completed_at, created_at, updated_at |
| `scan_stages` | id, scan_id FK, stage (validate/fingerprint/metadata/detect/forensics/xai/evidence/risk/verdict/report), status, started_at, completed_at, error, details |
| `detection_results` | id, scan_id FK, model_version_id FK, task, prediction, confidence (0..1), label, input_type, model_metadata JSONB, created_at |
| `metadata_results` | id, scan_id FK, source (exif/xmp/icc/container), status (present/absent/partial), data JSONB, findings JSONB, created_at |
| `forensic_evidence` | id, scan_id FK, module, evidence_type, evidence_category, strength, severity, location, details JSONB, model_version_id NULL, created_at |
| `attribution_results` | id, scan_id FK, attribution_class (sd/flux/midjourney/dalle/gan/ps-genfill/other/unknown), confidence, method, model_version_id FK, created_at |
| `xai_results` | id, scan_id FK, model_version_id FK, kind (gradcam/heatmap/attention), artifact_path, summary JSONB, created_at |
| `risk_assessments` | id, scan_id FK, level, score (0..1), components JSONB, rationale, created_at |
| `verdicts` | id, scan_id FK, verdict, confidence (0..1), basis JSONB, created_at |
| `reports` | id, scan_id FK, format (json/pdf), status, content JSONB, file_path, generated_at, created_at |
| `audit_logs` | id, user_id FK NULL, action, entity_type, entity_id, ip, details JSONB, created_at |

> Only tables actually needed by implemented features are created via migrations. Table set above is the target; as of Phase 2 only `model_versions`, `media`, `scans`, `scan_stages` exist (migration `0dfc71182341`, see §2b). `users`, results, evidence, assessment, reports, audit tables arrive in later milestones.

---

## 6. Evidence Model

Every forensic finding is recorded as evidence with enough structure to answer:
WHAT / WHERE / HOW / WHAT TYPE / HOW STRONG / WHICH MODULE / WHICH MODEL-VERSION / WHEN / LIMITATIONS.

```json
{
  "id": "...",
  "scan_id": "...",
  "module": "forensics.ela",
  "evidence_type": "model_inference | verified | heuristic | unknown",
  "evidence_category": "compression_artifact | noise_residual | metadata_inconsistency | ...",
  "strength": 0.0 .. 1.0,
  "severity": "low | medium | high | critical",
  "location": {"region": "face", "bbox": [..], "frame": 42},
  "details": { ...module-specific... },
  "model_version_id": null | "...",
  "limitations": "ELA produces false positives on heavily compressed legitimate media",
  "created_at": "..."
}
```

- `detection_results` and `metadata_results` are evidence sources that are ALSO exposed
  as first-class results; `forensic_evidence` carries generic/composable evidence.
- Raw individual evidence is always preserved alongside any aggregate score.

---

## 7. Confidence Engine

- Inputs: detector confidence, metadata findings, forensic module strengths, attribution
  confidence, XAI coverage — each mapped to normalized per-signal strength.
- Aggregation: deterministic weighted model. Weights are **documented and constant**,
  defined in `app/domain/confidence.py` with justification. No hidden/ad-hoc weights.
- Output: `confidence` (0..1) + `components` breakdown (per-signal contribution).
- The output is labeled `model_inference`/`heuristic` aggregate, NEVER "verified probability".
- Methodology is published in this doc (see §17) and code.

## 8. Risk Engine

- Deterministic rule table mapping evidence profile → `LOW | MEDIUM | HIGH | CRITICAL`.
- Inputs: evidence counts by severity, aggregated confidence bands, presence of
  verified vs inference evidence.
- `risk != classifier confidence`. Risk reflects strength and coherence of evidence,
  not a single model's prediction.
- Rule table documented in `app/domain/risk.py` and §17.

## 9. Verdict Engine

Verdict taxonomy (designed in Phase 0; exact strings frozen at implementation):

| Verdict | Meaning |
| --- | --- |
| `LIKELY_AUTHENTIC` | Consistent verified/heuristic evidence, no strong manipulation signal |
| `INCONCLUSIVE` | Conflicting or insufficient evidence |
| `LIKELY_MANIPULATED` | Coherent medium-strength evidence of manipulation |
| `STRONG_EVIDENCE_OF_MANIPULATION` | Coherent high-strength evidence from independent modules |
| `UNKNOWN` | No defensible signal |

- Verdict always derived from evidence + confidence + risk. Never fabricated.
- `verdicts` row stores verdict, aggregate confidence, and `basis` (evidence IDs).

---

## 10. Scan Lifecycle

Statuses:

```
CREATED → VALIDATING → QUEUED → PROCESSING → COMPLETED
                                  ↘ FAILED
```

- `CREATED`: scan row + media row persisted.
- `VALIDATING`: media validation (size/MIME/extension/content). Failure → `FAILED`.
- `QUEUED`: validation passed; job enqueued.
- `PROCESSING`: pipeline runs; per-stage progress in `scan_stages`.
- `COMPLETED`: all enabled stages finished, report built (JSON; PDF on demand).
- `FAILED`: any stage error; `error_message` + failed stage recorded.

Background processing: in-process worker consuming a `ScanJob` queue (asyncio + threading
guard for non-async libs). Interface `app/workers/queue.py` is replaceable by Celery/Redis
later without touching services. No Celery/Redis in v1.

---

## 11. Analysis Pipeline Orchestration

`workers/runner.py` executes pipeline stages in order. Each stage is an independent,
registered unit (`detectors` and `forensic_modules` register themselves). The runner
is declarative — adding a module means registering it, not rewriting the pipeline:

```
1. validate      (media/validation.py)
2. fingerprint   (media/fingerprint.py)
3. metadata      (metadata/exif.py, xmp.py, analyzer.py)
4. detect        (inference/registry.py → detectors)
5. forensics     (forensics/registry.py → modules)
6. xai           (xai/ → gradcam, if a real model + artifact storage available)
7. evidence      (domain/evidence.py aggregation)
8. confidence    (domain/confidence.py)
9. risk          (domain/risk.py)
10. verdict      (domain/verdict.py)
11. report       (reports/builder.py; pdf.py on demand)
```

Stages record into `scan_stages`. Errors fail the stage and the scan.

### AI integration boundary

- `inference/base.py` defines `Detector` interface: `detect(input, context) → Prediction`.
- `inference/registry.py` maps task → detector + active `model_version_id`.
- Detectors are hot-swappable; services depend on the interface only.
- Every result records model name, version, task, input type, prediction, confidence,
  timestamp, metadata, limitations.
- Phase 2 v1 ships with a clearly-labeled **baseline/dummy detector** used only to
  exercise the pipeline end-to-end (returns a synthetic-but-labeled result) OR a real
  detector if Shreyas provides one. If a dummy is used, every output is explicitly
  labeled `SIMULATION` in docs and API — never presented as real detection.

### XAI boundary

- `xai/base.py` defines `XAIProvider`. Artifacts (heatmaps) are stored under a
  non-committed directory. Heatmaps are only created by real model backprop/visualization.
  No fake heatmaps. If no real provider exists, stage records `status=skipped`.

---

## 12. Media Ingestion & Fingerprinting

- Validation never trusts filename, extension, or client MIME alone.
- Checks: declared extension vs detected MIME; magic-byte content inspection;
  size limits (env-configurable); safe filename generation; path-traversal guard.
- Storage: hashed server-side paths under a non-committed directory; temp-file flow;
  cleanup + retention policy on scan completion/failure.
- Fingerprint: SHA-256 (integrity/duplicate), perceptual hash (near-duplicate),
  dimensions, format, duration (video).

## 13. Metadata Intelligence

- EXIF: Pillow extraction (camera, timestamps, software, GPS, color profile).
- XMP: minimal best-effort parser (safe XML via `defusedxml`); C2PA recognized as
  out-of-scope for v1 unless practical.
- Analyzer reports: available keys, missing/suspicious keys, editing-software list,
  timestamp inconsistencies, possible metadata removal signals — labeled heuristic.

## 14. Visual Forensics (v1 subset, honestly computed)

Only modules with a defensible implementation ship. Candidates for v1:

- **ELA** (Error Level Analysis) — computed; labeled heuristic; known false positives on
  legitimate heavy compression documented.
- **Noise residual** — local noise variance consistency; heuristic.
- **Frequency domain** — spectral characteristics (e.g., FFT statistics); heuristic.
- **Quality/compression artifacts** — JPEG quality estimation, artifact metrics.

Each module: pure function `analyze(image, context) → list[ForensicEvidence]` + registry
entry. Unimplemented techniques are documented as future work, never stubbed as real.

## 15. Reports

- `reports/builder.py` assembles structured report JSON from persisted results
  (never from guesswork).
- Report sections: case info, executive summary, media info, file fingerprint,
  authenticity/manipulation/AI-generation assessment, attribution, metadata findings,
  visual-forensics findings, explainability, evidence summary, confidence, risk,
  verdict, recommendations, timestamps, model/version info.
- `reports/pdf.py` renders PDF via ReportLab; PDF generated on demand.
- Every displayed value = actual computation OR explicit inference OR verified metadata.

## 16. Authentication & Authorization

- OAuth2 password flow; JWT access tokens (short-lived) via PyJWT.
- Passwords: Argon2id via `pwdlib`.
- Roles: `user`, `admin`. Admin-only endpoints guarded by dependency.
- Audit logging on auth-sensitive and admin actions.

## 17. Documented Confidence/Risk Rules (v1)

> Placeholder for the exact, code-mirrored tables. Final numbers frozen at implementation
> time and kept identical in `app/domain/*` and here. Never change weights silently.

**Confidence** = Σ(signal_strength × weight) over signals, normalized; weights sum to 1.
Signals: detection (0.40), metadata (0.20), visual forensics (0.25), attribution (0.10),
XAI coverage (0.05). Heuristic signals capped at a max contribution; verified metadata can
raise, never raise beyond evidence ceiling. Exact banding documented with code.

**Risk** rule sketch:
- ≥2 CRITICAL-severity evidence, or 1 critical + ≥2 high → `CRITICAL`
- ≥2 HIGH or 1 HIGH + ≥3 MEDIUM → `HIGH`
- ≥2 MEDIUM or 1 HIGH → `MEDIUM`
- otherwise → `LOW`
Severity derives from strength + evidence_type (verified/inference/heuristic ceiling).

## 18. Security Approach

- Secrets only via env; `.env.example` committed, `.env` never committed.
- Argon2id password hashing; JWT with env secret; token expiry.
- SQL injection safe via SQLAlchemy parameterization; Pydantic validation at the edge.
- Upload validation (size/type/content), safe filenames, path-traversal protection.
- CORS restricted to configured frontend origin(s).
- Rate limiting on auth endpoints (simple in-process limiter v1).
- Audit logs for sensitive actions; no secrets/PII in logs; error responses sanitized.
- Security-focused tests (injection, traversal, MIME spoofing, auth bypass).

## 19. Testing Architecture

- `pytest` + `pytest-asyncio` + httpx `AsyncClient`/`TestClient`.
- Layers: unit (validators, engines, extractors), service, API (end-to-end against app),
  database (real PG container, migrations applied), security, pipeline, reports.
- CI-style check command documented in README/pyproject. Tests must pass before commit.

## 20. Docker & Deployment

- `docker-compose.yml`: `db` (postgres:16-alpine, named volume, healthcheck) + `api`
  (uv-based image; entrypoint runs `alembic upgrade head` then uvicorn).
- `Dockerfile`: `python:3.14-slim` + uv, non-root user, `.dockerignore`.
- Dev/test DB isolated (different DB names) — no shared data.
- No Kubernetes/Celery/Redis in v1.

## 21. Environment Variables (`env.example` — to be created at implementation)

```
DATABASE_URL=postgresql+psycopg://phantom:phantom@localhost:5432/phantom
SECRET_KEY=change-me
ACCESS_TOKEN_EXPIRE_MINUTES=60
MAX_UPLOAD_SIZE_MB=100
ALLOWED_MEDIA_TYPES=image/jpeg,image/png,image/webp,video/mp4,...
STORAGE_DIR=./storage
RATE_LIMIT_AUTH_MIN=...
CORS_ORIGINS=...
LOG_LEVEL=INFO
```

## 22. Development Milestones (two-week Phase 2)

Order = critical path. Each milestone = tests + docs + commit + push to `main`.

0. ✅ **chore(backend) [PHASE 1 COMPLETE]**: uv project, config, logging, app factory,
   health endpoint, exception model, async SQLAlchemy + Alembic foundation, Docker Compose
   PostgreSQL, test/lint/typecheck foundation.
1. **chore(db)**: SQLAlchemy models `users` + `model_versions` + migrations.
2. **feat(auth)**: register/login/me, JWT, password hashing, role guards.
3. **feat(db)**: `media`, `scans`, `scan_stages`, `metadata_results`, `detection_results`, `forensic_evidence`, `attribution_results`, `xai_results`, `risk_assessments`, `verdicts`, `reports`, `audit_logs` + migrations.
4. **feat(media)**: upload validation + storage + fingerprinting + API.
5. **feat(metadata)**: EXIF/XMP extraction + analyzer.
6. **feat(scan)**: scan lifecycle + worker queue + runner skeleton.
7. **feat(inference)**: detector interface + registry + baseline detector (clearly labeled).
8. **feat(forensics)**: ELA + noise + frequency modules with honest labeling.
9. **feat(evidence)**: evidence aggregation + confidence engine.
10. **feat(risk/verdict)**: risk + verdict engines.
11. **feat(report)**: report builder + PDF.
12. **feat(admin)**: admin APIs (users, scans, models, stats).
13. **test**: full suite pass (unit/service/api/db/security/pipeline/reports).
14. **chore(docker)**: Dockerfile + compose + entrypoint + README runbook.
15. **docs**: freeze API_CONTRACTS, finalize BACKEND_IMPLEMENTATION.

## 23. Dependencies (initial)

Runtime (installed, Phase 1): `fastapi`, `uvicorn[standard]`, `pydantic-settings`,
`sqlalchemy[asyncio]`, `psycopg[binary]`, `alembic`.
Planned future milestones: `python-multipart`, `pillow`, `numpy`, `pwdlib[argon2]`, `pyjwt`,
`defusedxml`, `reportlab`, `httpx`.
Dev (installed): `pytest`, `pytest-asyncio`, `httpx`, `ruff`, `mypy`, `pre-commit` (optional).

> Some optional libs (imagehash) need 3.14 wheels — verify before adding.

## 24. Risks

- **Python 3.14 wheel availability** — mitigated: empirically verified for current + planned
  dependency set (incl. torch 2.13.0, numpy 2.5.2, pillow 12.3.0); lockfile pins versions.
- **No host PostgreSQL** — mitigation: Docker Compose dev DB; CI uses same container.
- **Scientific-honesty drift** — mitigation: AGENTS.md rules, evidence model enforced in code,
  code review by team lead.
- **Baseline detector fake-results risk** — mitigation: explicit `SIMULATION` labeling, never
  surfaced as verified.
- **Heuristic false positives (ELA/noise)** — mitigation: documented limitations in every
  evidence record; verdict rules weight verified vs heuristic separately.
- **Starlette/FastAPI 1.6 API churn** — mitigation: pinned via lockfile; exception handling
  behavior verified against live server + tests.
- **Scope creep (attribution, advanced forensics)** — mitigation: milestone gating; advanced
  features only after core pipeline works.

## 25. Open Questions

- ~~Sync vs async SQLAlchemy engine for v1~~ — **decided: async** (see §2a).
- Whether Shreyas provides a real detector within Phase 2 or the baseline/simulated path ships first.
- Final confidence/risk weight tables (frozen at implementation, then documented here).
- XAI artifact storage layout (decided with frontend heatmap needs).
- Video analysis depth in v1 (frame sampling policy).
- C2PA support scope (recognized as likely out of v1).

## 26. Change History

| Date | Change |
| --- | --- |
| 2026-08-15 | Phase 0 baseline: architecture blueprint, repo/environment inspection, AGENTS.md, API_CONTRACTS.md |
| 2026-08-15 | Phase 1 foundation: uv project, config, logging, exceptions, app factory, health API, async SQLAlchemy + Alembic baseline, Docker Compose PostgreSQL, pytest/ruff/mypy green. Runtime locked to Python 3.14. |
| 2026-08-16 | Phase 3 secure media ingestion: upload endpoint, server-side detection, streaming SHA-256, storage provider, size/format/extension policy (see §2c). |
| 2026-08-16 | Phase 4 analysis worker + pipeline: in-process worker with `FOR UPDATE SKIP LOCKED` claiming, stage registry/runner, `validate` + `fingerprint` stages (dHash), lifecycle to COMPLETED/FAILED, opt-in worker in app lifespan, 95 tests green (see §2d). |
| 2026-08-16 | Phase 5 metadata intelligence: EXIF/XMP extraction, analysis payload, metadata stage, EvidenceType, 123 tests green (see §2e). |
| 2026-08-16 | Phase 6 detection intelligence: Detector contract + registry + UnavailableDetector + detect stage, 143 tests green, pushed to `origin/backend` (see §2f). |
| 2026-08-16 | Phase 7 visual forensics engine: ForensicAnalyzer contract + registry, ELA/noise/frequency analyzers, forensics stage after detection, numpy dep, 179 tests green (see §2g). |
| 2026-08-16 | Phase 8 XAI engine: XAIExplainer contract + registry, UnavailableExplainer (honest UNAVAILABLE, no fabricated heatmaps), xai stage after forensics reusing the same detector instance as detection, 203 tests green (see §2h). |
| 2026-08-16 | Phase 9 evidence aggregation & confidence engine: app/evidence package, evidence stage after xai, honest INSUFFICIENT_EVIDENCE confidence (never fabricated numeric), correlation dedupe, 252 tests green, pushed to `origin/backend` (see §2i). |
