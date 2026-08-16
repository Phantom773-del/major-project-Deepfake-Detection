# AGENTS.md — PHANTOM PHOENIX Backend

Persistent engineering instructions for coding sessions on this repository.

## Project

PHANTOM PHOENIX — Digital Media Authenticity & AI Forensic Intelligence Platform.
Backend: FastAPI + PostgreSQL (async SQLAlchemy 2.x + Alembic; sync engine for migrations).
Python 3.14 managed with `uv`. Quality gates: `pytest`, `ruff`, `mypy --strict` must pass.

## Git rules

- Work on branch `main` until the team leader says otherwise. Do NOT switch to `backend`.
- Never force-push. Never rewrite published history.
- Commit meaningful milestones, conventional style: `type(scope): description` (`feat`, `chore`, `fix`, `docs`, `test`, `refactor`).
- Before committing: run relevant tests, inspect `git diff`, review changed files, update docs, verify no secrets.
- Never commit `.env`, credentials, keys, model weights, uploaded media, or generated reports.

## Scientific honesty (critical)

- Classifier confidence is NOT forensic truth. Keep separate: `verified evidence`, `model inference`, `heuristic evidence`, `unknown`.
- Never fabricate evidence, heatmaps, accuracy values, datasets, or results.
- Pipeline stages must never fabricate results. An unimplemented stage is marked `SKIPPED` with an explicit reason ("not implemented in this build") — never a placeholder that looks like real output. A stage may only write `result_ref` with data it actually computed.
- Label uncertain output: "likely", "possible", "strong/weak evidence", "insufficient evidence", "unknown".
- Never claim exact generator/checkpoint/seed/prompt recovery without a real evidence source.
- Placeholder analysis that looks like real evidence is forbidden. If a module does not compute real output, say so.
- Preserve raw individual evidence alongside any aggregate score.
- Metadata is evidence, never a verdict. Every metadata finding is classified (`VERIFIED`/`INFERENCE`/`HEURISTIC`/`UNKNOWN`); presence/absence or editor strings never establish AI generation; unparsed provenance (e.g. C2PA) is reported `UNAVAILABLE`, never invented or implied.
- Forensic measurements are observations, never verdicts. Analyzers (ELA, noise, frequency, etc.) return measurable statistics, never an authenticity probability (`forensic_confidence`, `manipulation_probability`, `AI_probability` are forbidden). A measurement statement is `VERIFIED`; any interpretation is `HEURISTIC` supporting evidence with the limitation stated. Generic signals vary with compression, content, resizing, and denoising — measurement ≠ verdict. Per-analyzer failures are recorded per-analyzer and never fabricated as success.
- Evidence aggregation (the `evidence` stage) is normalization of real pipeline outputs, never invention. Reuse the shared `EvidenceType` taxonomy; do not define a competing one. `UNAVAILABLE`/`FAILED` sources are honest states recorded in an availability map — never negative evidence, and absence of metadata is never evidence of AI generation. Correlated signals (e.g. ELA+frequency, detection+XAI) are never counted as fully independent. No manipulation verdict category exists in this build.
- Confidence is never fabricated. A numeric confidence/probability may only be emitted by a validated, calibrated methodology; otherwise `confidence.status` is `INSUFFICIENT_EVIDENCE` with `value = null` and explicit reasons. "Confidence" means strength/consistency of available evidence supporting an assessment, never "probability the media is fake".
- A detector model score is a model output with its own `score_semantics` — it is never a calibrated probability and never automatically becomes a confidence value or a verdict.
- Confidence ≠ risk ≠ verdict. Confidence is evidence strength; risk is how concerning an *established* assessment is for a reviewer; verdict is the final defensible conclusion. Never compute `risk = confidence`, `risk = detector score`, or `verdict = confidence > X`. An arbitrary weight/score formula for risk or verdict is forbidden — it fabricates results.
- `INSUFFICIENT_EVIDENCE`, `UNDETERMINED`, and `INCONCLUSIVE` are valid, honest outcomes — never force a HIGH risk or a definitive verdict to "be useful". Unavailable evidence (no detector, no XAI, no C2PA) never elevates risk and never reduces confidence.
- Manipulation and synthetic generation are distinct assessments; editing history never implies synthetic generation, and a detector score alone never produces a verdict.
- Reports (the `report` stage) are presentation of real persisted pipeline outputs — never a re-run of analysis, never a new analysis, never a verdict generator. A report composes from the ten upstream `result_ref` payloads and may only fail on render/persist errors (`COMPLETED`/`FAILED`); it never reopens the image, never recomputes confidence/risk/verdict, and never fabricates heatmaps, confidence charts, risk gauges, model identity, or attribution graphs. `null` confidence renders as `NOT QUANTIFIED` (never `0`/percentage); `UNAVAILABLE` detector/XAI/provenance states render unavailable with their real reason; a detector score appears with its `score_semantics` and is never called confidence/probability; GPS is presence-only; no filesystem/server paths, secrets, or legal/admissibility claims ("court-admissible", "certified", "forensically conclusive") ever appear. Report determinism: identical persisted results ⇒ identical document and byte-identical PDF.

## Architecture rules

- Modular `app/` package: `api/`, `schemas/`, `services/`, `repositories/`, `domain/`, `inference/`, `media/`, `metadata/`, `forensics/`, `xai/`, `reports/`, `audit/`, `core/`, `db/`.
- No giant routes or single-function pipeline. New forensic modules must be addable without rewriting the system.
- Expose Pydantic schemas as API contracts — never internal DB models directly.
- AI/ML behind a detector interface (registry + model version tracking). No tight coupling to one model.
- No Celery/Redis initially. Use a simple controlled background worker; keep it replaceable.

## Verification requirements

- Every implemented feature needs real tests (unit/service/API/database/security). Never claim tests pass unless executed.
- PostgreSQL for dev runs via Docker Compose (`postgres:16-alpine`). Host PG is not running.
- `app/db/migrations/env.py` imports every model (via `app/db/models`) so `alembic revision --autogenerate` diffs the real schema; after adding a model, import it there too.
- Tests apply migrations to `phantom_test` automatically (session fixture in `tests/conftest.py`); never add tables to test DB by hand.
- Domain status changes (e.g. scan lifecycle) go through the state machine in `app/domain/scan.py` and the service layer — never set status directly in API routes.
- Media ingestion: client Content-Type/filename are never trusted; server-side content detection is authoritative; storage refs are internal only (`storage_path` never returned); SHA-256 means identical bytes, never identical visual content.

## Documentation

- `docs/BACKEND_IMPLEMENTATION.md` — continuously updated engineering record.
- `docs/API_CONTRACTS.md` — stable interfaces (backend ↔ frontend ↔ AI/ML ↔ reports).
- Update both whenever architecture or public behavior changes. Never document unbuilt features as real.

## When uncertain

Stop and inspect. Do not guess. Document ambiguity. Propose a smaller defensible alternative over a larger fictional one.
