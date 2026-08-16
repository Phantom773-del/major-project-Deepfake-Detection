"""Report domain: the deterministic forensic case report data model.

The report layer is presentation/composition only. It consumes the persisted
pipeline results (``ScanStage.result_ref``) and never re-runs analysis, never
modifies evidence/confidence/risk/verdict, and never invents a finding.

Separation of concerns (Phase 11):

- **ReportDocument** — pure, deterministic data model of the report content.
- **composer** — builds a ``ReportDocument`` from persisted pipeline results.
- **renderer / pdf** — format a ``ReportDocument`` (text / PDF bytes) with no
  business logic.

Scientific honesty rules encoded here:

- A report can be ``COMPLETED`` while the verdict is ``INSUFFICIENT_EVIDENCE``:
  report status is about composition success, never about analysis strength.
- ``null`` confidence stays unquantified ("NOT QUANTIFIED"); unavailable
  evidence stays unavailable; no fake heatmaps, probabilities, model identity
  or verdicts are ever rendered.
"""

import enum

from pydantic import BaseModel, Field

from app.domain.taxonomy import EvidenceType


class ReportStatus(enum.StrEnum):
    """Whether the report was successfully composed (never an analysis claim)."""

    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ReportFormat(enum.StrEnum):
    """Supported report document formats."""

    REPORT_DOCUMENT = "report-document"
    PDF = "pdf"


class SectionRow(BaseModel):
    """One labelled row in a report section.

    ``evidence_type`` preserves the shared evidence classification (VERIFIED /
    INFERENCE / HEURISTIC / UNKNOWN) where the row presents an evidence item.
    """

    label: str = Field(min_length=1)
    value: str
    evidence_type: EvidenceType | None = None
    note: str | None = None


class Section(BaseModel):
    """A titled report section with deterministic rows and statements."""

    title: str = Field(min_length=1)
    rows: list[SectionRow] = Field(default_factory=list)
    statements: list[str] = Field(default_factory=list)


class ReportDocument(BaseModel):
    """Deterministic content of one forensic analysis report.

    Timestamps come only from the persisted scan/media records — nothing in the
    report is time-stamped during composition. Identical persisted pipeline
    results produce an identical ``ReportDocument``.
    """

    report_version: str = "1"
    case_id: str = Field(min_length=1)
    media_id: str = Field(min_length=1)
    created_at: str | None = None
    analyzed_at: str | None = None
    media_type: str
    original_filename: str
    size_bytes: int | None = None
    mime_type: str | None = None
    pipeline_status: str
    summary: str
    sections: list[Section] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    methodology: dict[str, str] = Field(default_factory=dict)


class ReportArtifact(BaseModel):
    """Reference to a rendered artifact (e.g. PDF bytes) stored safely.

    ``reference`` is a server-generated safe storage reference (a plain
    filename inside the report storage root) — never a client-controlled path.
    """

    format: ReportFormat
    reference: str = Field(min_length=1)
    size_bytes: int | None = None
    available: bool


class ReportResult(BaseModel):
    """Structured output of the report stage (persisted to ``result_ref``).

    ``status`` reflects composition success only. ``document`` is the
    deterministic report content; ``artifact`` describes a rendered PDF when one
    was produced. ``summary``/``limitations`` mirror the document fields for
    convenience of API consumers.
    """

    status: str = "COMPLETED"
    format: str = "report-document"
    version: str = "1"
    reference: str | None = None
    artifact: ReportArtifact | None = None
    document: ReportDocument
    summary: str
    limitations: list[str] = Field(default_factory=list)
