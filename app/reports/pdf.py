"""PDF report renderer.

Formats a ``ReportDocument`` into deterministic PDF bytes using ReportLab.
Contains no business logic — everything it renders comes from the document.

Determinism: ``SimpleDocTemplate(invariant=1)`` makes ReportLab emit no random
file ID and no composition timestamp, so identical documents produce
byte-identical PDFs.
"""

from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

from app.reports.domain import ReportDocument


class PDFRenderer:
    """Renders a ``ReportDocument`` to PDF bytes."""

    def render(self, document: ReportDocument) -> bytes:
        buffer = BytesIO()
        styles = getSampleStyleSheet()
        body = ParagraphStyle(
            "body",
            parent=styles["BodyText"],
            fontSize=9,
            leading=12,
            spaceAfter=3,
        )
        section_heading = ParagraphStyle(
            "section",
            parent=styles["Heading2"],
            fontSize=11,
            leading=14,
            spaceBefore=10,
            spaceAfter=4,
            textColor=colors.HexColor("#1a1a1a"),
        )
        title_style = ParagraphStyle(
            "title",
            parent=styles["Title"],
            fontSize=16,
            leading=20,
            spaceAfter=2,
        )
        meta_style = ParagraphStyle(
            "meta",
            parent=styles["BodyText"],
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#444444"),
        )
        statement_style = ParagraphStyle(
            "statement",
            parent=body,
            leftIndent=6,
            textColor=colors.HexColor("#333333"),
        )

        story: list[object] = [
            Paragraph("PHANTOM PHOENIX — Forensic Analysis Report", title_style),
            Paragraph(f"Report Version: {document.report_version}", meta_style),
            Paragraph(f"Case ID: {document.case_id}", meta_style),
            Paragraph(f"Media ID: {document.media_id}", meta_style),
            Paragraph(f"Created At: {document.created_at or 'UNAVAILABLE'}", meta_style),
            Paragraph(
                f"Analyzed At: {document.analyzed_at or 'NOT IMPLEMENTED'}", meta_style
            ),
            Paragraph(f"Media Type: {document.media_type}", meta_style),
            Paragraph(f"Original Filename: {escape(document.original_filename)}", meta_style),
            Paragraph(
                "File Size (bytes): "
                + (
                    str(document.size_bytes)
                    if document.size_bytes is not None
                    else "UNAVAILABLE"
                ),
                meta_style,
            ),
            Paragraph(f"MIME Type: {document.mime_type or 'UNAVAILABLE'}", meta_style),
            Paragraph(f"Pipeline Status: {document.pipeline_status}", meta_style),
            Spacer(1, 4 * mm),
            Paragraph("EXECUTIVE SUMMARY", section_heading),
            Paragraph(escape(document.summary), body),
        ]
        for section in document.sections:
            story.append(Spacer(1, 2 * mm))
            story.append(Paragraph(escape(section.title.upper()), section_heading))
            for row in section.rows:
                evidence = (
                    f" [{row.evidence_type.value}]"
                    if row.evidence_type is not None
                    else ""
                )
                note = f" — {row.note}" if row.note else ""
                story.append(
                    Paragraph(
                        f"<b>{escape(row.label)}:</b> {escape(row.value)}"
                        f"{escape(evidence)}{escape(note)}",
                        body,
                    )
                )
            for statement in section.statements:
                story.append(Paragraph(f"• {escape(statement)}", statement_style))
        story.append(PageBreak())
        story.append(Paragraph("METHODOLOGY & VERSIONS", section_heading))
        for key, value in document.methodology.items():
            story.append(
                Paragraph(f"<b>{escape(key)}:</b> {escape(value)}", body)
            )
        story.append(Paragraph("LIMITATIONS", section_heading))
        for limitation in document.limitations:
            story.append(Paragraph(f"• {escape(limitation)}", body))

        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=18 * mm,
            rightMargin=18 * mm,
            topMargin=16 * mm,
            bottomMargin=16 * mm,
            title="PHANTOM PHOENIX — Forensic Analysis Report",
            author="Phantom Phoenix Backend",
            subject=f"Case {document.case_id}",
            invariant=1,
        )
        doc.build(story)
        return buffer.getvalue()


def render_report_pdf(document: ReportDocument) -> bytes:
    """Render a report document to PDF bytes (convenience wrapper)."""
    return PDFRenderer().render(document)
