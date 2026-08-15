# PHANTOM PHOENIX — Backend Implementation Record & Architecture Blueprint

> Phase 0 document. Engineering record — updated continuously as implementation progresses.
> Last updated: 2026-08-15 (Phase 0 baseline)

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
