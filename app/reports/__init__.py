"""Reports package: deterministic forensic report composition and rendering.

The report layer consumes the persisted pipeline results (``ScanStage.result_ref``)
and produces a human-readable report document and a PDF artifact. It never
re-runs analysis and never changes evidence, confidence, risk or verdict.
"""

from app.reports.composer import ReportInputs, compose_report
from app.reports.domain import (
    ReportArtifact,
    ReportDocument,
    ReportFormat,
    ReportResult,
    ReportStatus,
    Section,
    SectionRow,
)
from app.reports.pdf import PDFRenderer, render_report_pdf
from app.reports.renderer import render_report_text

__all__ = [
    "PDFRenderer",
    "ReportArtifact",
    "ReportDocument",
    "ReportFormat",
    "ReportInputs",
    "ReportResult",
    "ReportStatus",
    "Section",
    "SectionRow",
    "compose_report",
    "render_report_pdf",
    "render_report_text",
]
