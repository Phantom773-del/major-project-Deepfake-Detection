"""``report`` pipeline stage: compose and persist the forensic case report.

The report is a faithful presentation of the analysis actually performed. It
consumes ONLY the persisted ``ScanStage.result_ref`` outputs of the prior stages
— it never re-runs detection, metadata extraction, forensics, XAI, or any
confidence/risk/verdict calculation, and it never reopens the image for
analysis.

Failures:
- A PDF render failure or storage persist failure raises ``StageError``
  (client-safe), so the scan FAILS — a missing report is never silently
  accepted.
- A missing/unreadable upstream result is reported as unavailable (an honest
  state), never inferred.
"""

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

from app.assessment import ConfidenceResult, RiskResult, VerdictResult
from app.domain.taxonomy import MediaType
from app.evidence.domain import EvidenceResult
from app.inference.base import DetectionResult
from app.media.storage import LocalStorageProvider
from app.reports.composer import ReportInputs, compose_report
from app.reports.domain import (
    ReportArtifact,
    ReportDocument,
    ReportFormat,
    ReportResult,
)
from app.reports.pdf import PDFRenderer
from app.workers.stages._read import read_stage_json
from app.workers.stages.base import StageContext, StageError, StageResult
from app.xai.base import XAIResult

logger = logging.getLogger(__name__)


class ReportStage:
    """Composes the deterministic forensic report and persists its artifact."""

    name = "report"

    async def run(self, ctx: StageContext) -> StageResult | None:
        if ctx.media.media_type is not MediaType.IMAGE:
            raise StageError(
                f"media type {ctx.media.media_type.value} is not supported by the "
                "report stage"
            )
        document = compose_report(self._inputs(ctx))
        artifact = self._render_and_store(document, ctx)
        result = ReportResult(
            status="COMPLETED",
            reference=artifact.reference,
            artifact=artifact,
            document=document,
            summary=document.summary,
            limitations=document.limitations,
        )
        return StageResult(
            result_ref=json.dumps(result.model_dump(mode="json"), sort_keys=True)
        )

    def _render_and_store(
        self, document: ReportDocument, ctx: StageContext
    ) -> ReportArtifact:
        """Render PDF bytes and persist them under a safe storage reference.

        Any render/persist failure raises ``StageError`` (client-safe).
        """
        try:
            pdf_bytes = PDFRenderer().render(document)
        except Exception:
            logger.exception("report PDF render failed for scan %s", ctx.scan.id)
            raise StageError("report could not be rendered") from None
        storage = LocalStorageProvider(Path(ctx.settings.storage_dir) / "reports")
        name = f"{ctx.scan.id}.pdf"
        tmp_root = Path(ctx.settings.storage_dir) / "reports" / "tmp"
        tmp_path: Path | None = None
        try:
            tmp_root.mkdir(parents=True, exist_ok=True)
            fd, tmp_name = tempfile.mkstemp(prefix="report-", dir=tmp_root)
            os.close(fd)
            tmp_path = Path(tmp_name)
            tmp_path.write_bytes(pdf_bytes)
            reference = storage.persist(tmp_path, name=name)
        except Exception:
            logger.exception("report persist failed for scan %s", ctx.scan.id)
            raise StageError("report could not be stored") from None
        finally:
            if tmp_path is not None:
                tmp_path.unlink(missing_ok=True)
        return ReportArtifact(
            format=ReportFormat.PDF,
            reference=reference,
            size_bytes=len(pdf_bytes),
            available=True,
        )

    def _inputs(self, ctx: StageContext) -> ReportInputs:
        """Gather persisted upstream results (fail-safe to unavailable)."""
        return ReportInputs(
            scan_id=str(ctx.scan.id),
            media_id=str(ctx.media.id),
            created_at=self._iso(ctx.media.created_at),
            analyzed_at=self._iso(ctx.scan.completed_at),
            pipeline_status=(
                ctx.scan.status.value if ctx.scan.status is not None else "UNKNOWN"
            ),
            media_type=ctx.media.media_type.value,
            original_filename=ctx.media.original_filename,
            size_bytes=ctx.media.size_bytes,
            mime_type=ctx.media.mime_type,
            stage_statuses={s.name: s.status.value for s in ctx.scan.stages},
            fingerprint=read_stage_json(ctx, "fingerprint"),
            metadata=read_stage_json(ctx, "metadata"),
            detection=self._parse(DetectionResult, "detect", ctx),
            forensics=read_stage_json(ctx, "forensics"),
            xai=self._parse(XAIResult, "xai", ctx),
            evidence=self._parse(EvidenceResult, "evidence", ctx),
            confidence=self._parse(ConfidenceResult, "confidence", ctx),
            risk=self._parse(RiskResult, "risk", ctx),
            verdict=self._parse(VerdictResult, "verdict", ctx),
        )

    @staticmethod
    def _iso(value: object) -> str | None:
        if value is None:
            return None
        try:
            iso = value.isoformat  # type: ignore[attr-defined]
            return iso() if callable(iso) else str(value)
        except Exception:  # noqa: BLE001 - never fail composition on a timestamp
            return None

    @staticmethod
    def _parse(model: type[Any], name: str, ctx: StageContext) -> Any | None:
        """Parse a typed upstream model, fail-safe to ``None`` on any problem."""
        payload = read_stage_json(ctx, name)
        if payload is None:
            return None
        try:
            return model.model_validate(payload)
        except Exception:
            logger.warning("could not parse %s result for scan %s", name, ctx.scan.id)
            return None
