"""Plain-text report renderer.

Deterministic, dependency-free rendering of a ``ReportDocument`` to a single
UTF-8 string. Used for tests, console previews, and as the format reference the
PDF renderer mirrors. Contains no business logic.
"""

from app.reports.domain import ReportDocument


def render_report_text(document: ReportDocument) -> str:
    """Render a report document to deterministic plain text."""
    lines: list[str] = [
        "PHANTOM PHOENIX — Forensic Analysis Report",
        f"Report Version: {document.report_version}",
        f"Case ID: {document.case_id}",
        f"Media ID: {document.media_id}",
        f"Created At: {document.created_at or 'UNAVAILABLE'}",
        f"Analyzed At: {document.analyzed_at or 'NOT IMPLEMENTED'}",
        f"Media Type: {document.media_type}",
        f"Original Filename: {document.original_filename}",
        "File Size (bytes): "
        + (
            str(document.size_bytes)
            if document.size_bytes is not None
            else "UNAVAILABLE"
        ),
        f"MIME Type: {document.mime_type or 'UNAVAILABLE'}",
        f"Pipeline Status: {document.pipeline_status}",
        "",
        "EXECUTIVE SUMMARY",
        document.summary,
        "",
    ]
    for section in document.sections:
        lines.append(section.title.upper())
        for row in section.rows:
            evidence = (
                f" [{row.evidence_type.value}]" if row.evidence_type is not None else ""
            )
            note = f" — {row.note}" if row.note else ""
            lines.append(f"  {row.label}: {row.value}{evidence}{note}")
        for statement in section.statements:
            lines.append(f"  * {statement}")
        lines.append("")
    lines.append("METHODOLOGY & VERSIONS")
    for key, value in document.methodology.items():
        lines.append(f"  {key}: {value}")
    lines.append("")
    lines.append("LIMITATIONS")
    for limitation in document.limitations:
        lines.append(f"  - {limitation}")
    return "\n".join(lines).rstrip() + "\n"
