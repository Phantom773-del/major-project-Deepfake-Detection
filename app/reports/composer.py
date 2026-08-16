"""Report composer: builds a deterministic ``ReportDocument`` from persisted
pipeline results.

The composer is pure presentation/composition. It never re-runs detection,
metadata extraction, forensics, XAI, or any confidence/risk/verdict calculation.
It never modifies upstream results and never invents evidence. If an upstream
result is unavailable, the report says so — it never infers a result.

Determinism: all ordering is explicit (pipeline ``STAGE_ORDER``, sorted source
and item keys). Timestamps come only from persisted scan/media records. No
current time, random values, or unordered iteration is used.
"""

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from app.assessment import ConfidenceResult, RiskResult, VerdictResult
from app.assessment.domain import RiskLevel, VerdictStatus
from app.domain.taxonomy import EvidenceType
from app.evidence.domain import (
    ConfidenceStatus,
    EvidenceAvailability,
    EvidenceResult,
)
from app.inference.base import DetectionResult
from app.reports.domain import ReportDocument, Section, SectionRow
from app.xai.base import XAIResult


@dataclass(frozen=True)
class ReportInputs:
    """Everything the composer needs — already persisted values, never re-run."""

    scan_id: str
    media_id: str
    created_at: str | None
    analyzed_at: str | None
    pipeline_status: str
    media_type: str
    original_filename: str
    size_bytes: int | None
    mime_type: str | None
    stage_statuses: Mapping[str, str]
    fingerprint: Mapping[str, Any] | None
    metadata: Mapping[str, Any] | None
    detection: DetectionResult | None
    forensics: Mapping[str, Any] | None
    xai: XAIResult | None
    evidence: EvidenceResult | None
    confidence: ConfidenceResult | None
    risk: RiskResult | None
    verdict: VerdictResult | None


_STAGE_ORDER = (
    "validate",
    "fingerprint",
    "metadata",
    "detect",
    "forensics",
    "xai",
    "evidence",
    "confidence",
    "risk",
    "verdict",
    "report",
)

_NOT_QUANTIFIED = "NOT QUANTIFIED"
_UNAVAILABLE = "UNAVAILABLE"
_NOT_IMPLEMENTED = "NOT IMPLEMENTED"


def _evidence_type(value: object) -> EvidenceType | None:
    try:
        return EvidenceType(str(value))
    except ValueError:
        return None


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True)


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def compose_report(inputs: ReportInputs) -> ReportDocument:
    """Compose a deterministic report document from persisted pipeline results."""
    limitations = _limitations(inputs)
    return ReportDocument(
        report_version="1",
        case_id=inputs.scan_id,
        media_id=inputs.media_id,
        created_at=inputs.created_at,
        analyzed_at=inputs.analyzed_at,
        media_type=inputs.media_type,
        original_filename=inputs.original_filename,
        size_bytes=inputs.size_bytes,
        mime_type=inputs.mime_type,
        pipeline_status=inputs.pipeline_status,
        summary=_executive_summary(inputs),
        sections=_sections(inputs),
        limitations=limitations,
        methodology=_methodology(inputs),
    )


def _executive_summary(inputs: ReportInputs) -> str:
    parts: list[str] = []
    if inputs.verdict is not None:
        if inputs.verdict.verdict is VerdictStatus.INSUFFICIENT_EVIDENCE:
            parts.append(
                "The available analysis produced insufficient evidence for a "
                "stronger authenticity or manipulation conclusion."
            )
        else:
            parts.append(f"The analysis produced the verdict: {inputs.verdict.verdict.value}.")
    if (
        inputs.confidence is not None
        and inputs.confidence.confidence_status is ConfidenceStatus.INSUFFICIENT_EVIDENCE
    ):
        parts.append(
            "Confidence is not quantified: no validated, calibrated methodology "
            "is registered in this build."
        )
    if inputs.risk is not None and inputs.risk.risk_level is RiskLevel.UNDETERMINED:
        parts.append(
            "Risk could not be determined because no directional assessment was "
            "established."
        )
    if inputs.detection is not None and inputs.detection.inference.status == "UNAVAILABLE":
        parts.append(
            "No detector model was available, so model-based synthetic-generation "
            "analysis was not performed."
        )
    if inputs.xai is not None and inputs.xai.status == "UNAVAILABLE":
        parts.append(
            "No explainability heatmap was generated because no compatible "
            "detector/explainer was available."
        )
    if not parts:
        parts.append(
            "The analysis was completed and the resulting findings are presented "
            "below."
        )
    return " ".join(parts)


def _sections(inputs: ReportInputs) -> list[Section]:
    return [
        _case_information(inputs),
        _executive_summary_section(inputs),
        _pipeline_status(inputs),
        _fingerprint_section(inputs),
        _metadata_section(inputs),
        _detection_section(inputs),
        _forensics_section(inputs),
        _xai_section(inputs),
        _evidence_section(inputs),
        _confidence_section(inputs),
        _risk_section(inputs),
        _verdict_section(inputs),
    ]


def _case_information(inputs: ReportInputs) -> Section:
    return Section(
        title="Case Information",
        rows=[
            SectionRow(label="Case ID", value=inputs.scan_id),
            SectionRow(label="Media ID", value=inputs.media_id),
            SectionRow(label="Created At", value=inputs.created_at or _UNAVAILABLE),
            SectionRow(label="Analyzed At", value=inputs.analyzed_at or _NOT_IMPLEMENTED),
            SectionRow(label="Media Type", value=inputs.media_type),
            SectionRow(label="Original Filename", value=inputs.original_filename),
            SectionRow(
                label="File Size",
                value=str(inputs.size_bytes) if inputs.size_bytes is not None else _UNAVAILABLE,
            ),
            SectionRow(label="MIME Type", value=inputs.mime_type or _UNAVAILABLE),
            SectionRow(label="Pipeline Status", value=inputs.pipeline_status),
        ],
    )


def _executive_summary_section(inputs: ReportInputs) -> Section:
    return Section(
        title="Executive Summary",
        statements=[_executive_summary(inputs)],
    )


def _pipeline_status(inputs: ReportInputs) -> Section:
    rows = [
        SectionRow(label=name, value=inputs.stage_statuses.get(name, "PENDING"))
        for name in _STAGE_ORDER
    ]
    return Section(title="Pipeline Status", rows=rows)


def _fingerprint_section(inputs: ReportInputs) -> Section:
    payload = inputs.fingerprint or {}
    return Section(
        title="Fingerprint",
        rows=[
            SectionRow(
                label="SHA-256",
                value=str(payload.get("sha256", _UNAVAILABLE)),
                note="byte-level file identity; verifies integrity, never authenticity",
            ),
            SectionRow(
                label="dHash",
                value=str(payload.get("d_hash", _UNAVAILABLE)),
                note="structural similarity fingerprint; not provenance, not AI "
                "detection, not manipulation proof",
            ),
            SectionRow(
                label="Size (bytes)",
                value=str(payload.get("size_bytes", _UNAVAILABLE)),
            ),
        ],
        statements=[
            "The fingerprint identifies the stored file bytes; it is not "
            "authenticity or manipulation proof."
        ],
    )


def _metadata_section(inputs: ReportInputs) -> Section:
    payload = inputs.metadata or {}
    presence = payload.get("presence") or {}
    rows: list[SectionRow] = [
        SectionRow(label="Format", value=str(payload.get("format", _UNAVAILABLE))),
        SectionRow(label="Mode", value=str(payload.get("mode", _UNAVAILABLE))),
        SectionRow(
            label="Dimensions",
            value=str(payload.get("dimensions", _UNAVAILABLE)),
        ),
        SectionRow(
            label="EXIF",
            value=_present(presence.get("exif")),
            note="presence/absence is an observation, never AI-generation evidence",
        ),
        SectionRow(
            label="GPS",
            value=_present(presence.get("gps")),
            note="privacy-sensitive; reported as presence only",
        ),
        SectionRow(
            label="XMP",
            value=_present(presence.get("xmp")),
            note="presence/absence is an observation, never AI-generation evidence",
        ),
        SectionRow(
            label="ICC",
            value=_present(presence.get("icc")),
            note="presence/absence is an observation, never AI-generation evidence",
        ),
        SectionRow(
            label="Software",
            value=_join(payload.get("software")) or "none",
        ),
    ]
    provenance = payload.get("provenance") or {}
    rows.append(
        SectionRow(
            label="Provenance Status",
            value=str(provenance.get("status", _UNAVAILABLE)),
            note=str(provenance.get("note") or "") or None,
        )
    )
    consistency = payload.get("consistency") or {}
    for finding in consistency.get("findings", []):
        if not isinstance(finding, dict):
            continue
        rows.append(
            SectionRow(
                label=str(finding.get("code", "finding")),
                value=str(finding.get("message", "")),
                evidence_type=_evidence_type(finding.get("evidence_type")),
            )
        )
    return Section(
        title="Metadata",
        rows=rows,
        statements=[
            "Metadata presence or absence describes the file container and is "
            "never proof of AI generation; editing software is never proof of AI "
            "generation."
        ],
    )


def _detection_section(inputs: ReportInputs) -> Section:
    detection = inputs.detection
    if detection is None:
        return Section(
            title="Detection",
            rows=[SectionRow(label="Status", value=_UNAVAILABLE)],
            statements=["Detection unavailable: no detector result was produced."],
        )
    rows: list[SectionRow] = [SectionRow(label="Status", value=detection.inference.status)]
    if detection.inference.status == "UNAVAILABLE":
        rows.append(
            SectionRow(
                label="Reason",
                value=detection.inference.reason or "no detector model produced a prediction",
            )
        )
        rows.append(SectionRow(label="Detector", value=detection.detector.name))
        return Section(
            title="Detection",
            rows=rows,
            statements=[
                "No detector model was available; no prediction, score, "
                "probability or model identity is reported."
            ],
        )
    identity = detection.detector
    rows.extend(
        [
            SectionRow(label="Detector", value=identity.name),
            SectionRow(label="Detector Version", value=identity.detector_version),
            SectionRow(label="Model", value=identity.model_name or _UNAVAILABLE),
            SectionRow(label="Model Version", value=identity.model_version or _UNAVAILABLE),
            SectionRow(
                label="Checkpoint SHA-256",
                value=identity.checkpoint_sha256 or _UNAVAILABLE,
            ),
            SectionRow(
                label="Preprocessing Version",
                value=identity.preprocessing_version or _UNAVAILABLE,
            ),
        ]
    )
    if detection.prediction is not None:
        prediction = detection.prediction
        rows.extend(
            [
                SectionRow(label="Prediction Label", value=prediction.label),
                SectionRow(label="Prediction Score", value=str(prediction.score)),
                SectionRow(label="Score Semantics", value=prediction.score_semantics),
                SectionRow(
                    label="Class List",
                    value=", ".join(prediction.class_list or ()),
                ),
            ]
        )
    if detection.evidence_type is not None:
        rows.append(
            SectionRow(label="Evidence Type", value=detection.evidence_type.value)
        )
    return Section(
        title="Detection",
        rows=rows,
        statements=[
            "A detector score is a model output with its own score semantics — "
            "it is never a probability that the media is fake."
        ],
    )


def _forensics_section(inputs: ReportInputs) -> Section:
    payload = inputs.forensics or {}
    rows: list[SectionRow] = []
    image = payload.get("image") or {}
    if image:
        rows.append(SectionRow(label="Image", value=_json(image)))
    summary = payload.get("summary") or {}
    if summary:
        rows.append(SectionRow(label="Summary", value=_json(summary)))
    analyzers = payload.get("analyzers") or {}
    for name in sorted(analyzers):
        analyzer = analyzers[name]
        if not isinstance(analyzer, dict):
            continue
        rows.append(
            SectionRow(
                label=f"Analyzer: {name}",
                value=f"version={analyzer.get('version', '?')} "
                f"status={analyzer.get('status', '?')}",
            )
        )
        if analyzer.get("measurements"):
            rows.append(
                SectionRow(
                    label=f"{name} measurements",
                    value=_json(analyzer["measurements"]),
                )
            )
        if analyzer.get("error"):
            rows.append(SectionRow(label=f"{name} error", value=str(analyzer["error"])))
        for finding in analyzer.get("findings", []):
            if not isinstance(finding, dict):
                continue
            rows.append(
                SectionRow(
                    label=str(finding.get("code", "finding")),
                    value=str(finding.get("message", "")),
                    evidence_type=_evidence_type(finding.get("evidence_type")),
                )
            )
    return Section(
        title="Visual Forensics",
        rows=rows,
        statements=[
            "Visual forensic measurements are observations and can be affected "
            "by compression, resizing, denoising, editing history and natural "
            "image content; they are never an authenticity or fake probability."
        ],
    )


def _xai_section(inputs: ReportInputs) -> Section:
    xai = inputs.xai
    if xai is None:
        return Section(
            title="XAI",
            rows=[SectionRow(label="Status", value=_UNAVAILABLE)],
            statements=[
                "No explainability heatmap was generated in this build because a "
                "compatible detector/explainer was unavailable."
            ],
        )
    rows: list[SectionRow] = [SectionRow(label="Status", value=xai.status)]
    if xai.status == "UNAVAILABLE":
        rows.append(SectionRow(label="Reason", value=xai.reason or _UNAVAILABLE))
        return Section(
            title="XAI",
            rows=rows,
            statements=[
                "No explainability heatmap was generated in this build because a "
                "compatible detector/explainer was unavailable."
            ],
        )
    explainer = xai.explainer
    model = xai.model
    rows.extend(
        [
            SectionRow(
                label="Explainer",
                value=explainer.name if explainer is not None else _UNAVAILABLE,
            ),
            SectionRow(
                label="Technique",
                value=explainer.technique if explainer is not None else _UNAVAILABLE,
            ),
            SectionRow(
                label="Explainer Version",
                value=explainer.version if explainer is not None else _UNAVAILABLE,
            ),
            SectionRow(
                label="Model",
                value=model.name if model is not None else _UNAVAILABLE,
            ),
            SectionRow(
                label="Model Version",
                value=model.version if model is not None else _UNAVAILABLE,
            ),
            SectionRow(
                label="Model Checkpoint",
                value=(
                    model.checkpoint_sha256 if model is not None else _UNAVAILABLE
                ),
            ),
        ]
    )
    if xai.heatmap is not None:
        rows.append(
            SectionRow(
                label="Heatmap",
                value="AVAILABLE"
                if xai.heatmap.available
                else _UNAVAILABLE,
                note=(
                    f"reference={xai.heatmap.reference}; actual model output, "
                    "not a fabricated region"
                    if xai.heatmap.available
                    else None
                ),
            )
        )
    if xai.interpretation is not None:
        interpretation = xai.interpretation
        rows.extend(
            [
                SectionRow(label="Target Label", value=interpretation.target_label),
                SectionRow(label="Target Score", value=str(interpretation.target_score)),
                SectionRow(
                    label="Score Semantics", value=interpretation.score_semantics
                ),
                SectionRow(label="Summary", value=interpretation.summary),
            ]
        )
        if interpretation.limitation:
            rows.append(SectionRow(label="Limitation", value=interpretation.limitation))
    return Section(title="XAI", rows=rows)


def _evidence_section(inputs: ReportInputs) -> Section:
    evidence = inputs.evidence
    if evidence is None:
        return Section(
            title="Evidence Aggregation",
            statements=["Evidence aggregation was unavailable at report time."],
        )
    rows: list[SectionRow] = []
    for source in sorted(evidence.availability, key=lambda s: s.value):
        availability = evidence.availability[source]
        rows.append(
            SectionRow(
                label=f"Source: {source.value}",
                value=availability.value,
                note=(
                    "unavailable is not negative evidence"
                    if availability is not EvidenceAvailability.AVAILABLE
                    else None
                ),
            )
        )
    summary = evidence.summary
    rows.extend(
        [
            SectionRow(label="Total Evidence Items", value=str(summary.total)),
            SectionRow(
                label="Independent Items", value=str(summary.independent_count)
            ),
            SectionRow(
                label="By Evidence Type", value=_json(summary.by_evidence_type)
            ),
            SectionRow(label="By Direction", value=_json(summary.by_direction)),
            SectionRow(label="By Category", value=_json(summary.by_category)),
        ]
    )
    if evidence.correlation.groups:
        rows.append(
            SectionRow(
                label="Correlation Groups",
                value=", ".join(sorted(evidence.correlation.groups)),
                note=evidence.correlation.note or None,
            )
        )
    for item in sorted(evidence.evidence, key=lambda item: item.code):
        rows.append(
            SectionRow(
                label=f"{item.code}",
                value=item.observation,
                evidence_type=item.evidence_type,
                note=(
                    f"source={item.source.value} category={item.category.value} "
                    f"direction={item.direction.value} "
                    f"interpretation={item.interpretation}"
                ),
            )
        )
    return Section(
        title="Evidence Aggregation",
        rows=rows,
        statements=[
            "Evidence items preserve the shared classification (VERIFIED / "
            "INFERENCE / HEURISTIC / UNKNOWN); correlated signals are not "
            "treated as independent."
        ],
    )


def _confidence_section(inputs: ReportInputs) -> Section:
    confidence = inputs.confidence
    if confidence is None:
        return Section(
            title="Confidence",
            rows=[SectionRow(label="Status", value=_UNAVAILABLE)],
            statements=[
                "No validated/calibrated methodology currently supports a "
                "numeric confidence probability."
            ],
        )
    return Section(
        title="Confidence",
        rows=[
            SectionRow(label="Status", value=confidence.confidence_status.value),
            SectionRow(
                label="Value",
                value=_NOT_QUANTIFIED if confidence.value is None else str(confidence.value),
            ),
            SectionRow(label="Semantics", value=confidence.semantics),
            SectionRow(
                label="Reasons", value="; ".join(confidence.reasons) or _UNAVAILABLE
            ),
            SectionRow(
                label="Methodology Version", value=confidence.methodology_version
            ),
        ],
        statements=[
            "No validated/calibrated methodology currently supports a numeric "
            "confidence probability; a null confidence is unquantified, never zero."
        ],
    )


def _risk_section(inputs: ReportInputs) -> Section:
    risk = inputs.risk
    if risk is None:
        return Section(
            title="Risk",
            rows=[SectionRow(label="Risk Level", value=_UNAVAILABLE)],
            statements=["Risk could not be determined from the available evidence."],
        )
    return Section(
        title="Risk",
        rows=[
            SectionRow(label="Risk Level", value=risk.risk_level.value),
            SectionRow(
                label="Value",
                value=_NOT_QUANTIFIED if risk.value is None else str(risk.value),
            ),
            SectionRow(label="Semantics", value=risk.semantics),
            SectionRow(label="Reasons", value="; ".join(risk.reasons) or _UNAVAILABLE),
            SectionRow(label="Methodology Version", value=risk.methodology_version),
        ],
        statements=[
            "Risk is not detector confidence and is not a probability."
        ],
    )


def _verdict_section(inputs: ReportInputs) -> Section:
    verdict = inputs.verdict
    if verdict is None:
        return Section(
            title="Verdict",
            rows=[SectionRow(label="Verdict", value=_UNAVAILABLE)],
            statements=[
                "The platform does not have sufficient validated evidence to "
                "conclude that the media is authentic, manipulated, or synthetic.",
                "Recommendation: require independent verification before treating "
                "the media as authentic or manipulated.",
            ],
        )
    return Section(
        title="Verdict",
        rows=[
            SectionRow(label="Verdict", value=verdict.verdict.value),
            SectionRow(label="Semantics", value=verdict.semantics),
            SectionRow(label="Reasons", value="; ".join(verdict.reasons) or _UNAVAILABLE),
            SectionRow(label="Methodology Version", value=verdict.methodology_version),
        ],
        statements=[
            "The platform does not have sufficient validated evidence to "
            "conclude that the media is authentic, manipulated, or synthetic.",
            "Recommendation: require independent verification before treating "
            "the media as authentic or manipulated.",
        ],
    )


def _methodology(inputs: ReportInputs) -> dict[str, str]:
    detection = inputs.detection
    xai = inputs.xai
    identity = None
    if detection is not None and detection.inference.status == "AVAILABLE":
        identity = detection.detector
    forensics = inputs.forensics or {}
    analyzer_versions = {
        name: str(analyzer.get("version", "?"))
        for name, analyzer in (forensics.get("analyzers") or {}).items()
        if isinstance(analyzer, dict)
    }
    explainer = xai.explainer if xai is not None else None
    methodology = {
        "detector": identity.name if identity is not None else _UNAVAILABLE,
        "detector_version": (
            identity.detector_version if identity is not None else _UNAVAILABLE
        ),
        "detector_model": (
            identity.model_name or _UNAVAILABLE if identity is not None else _UNAVAILABLE
        ),
        "detector_model_version": (
            identity.model_version or _UNAVAILABLE
            if identity is not None
            else _UNAVAILABLE
        ),
        "detector_checkpoint_sha256": (
            identity.checkpoint_sha256 or _UNAVAILABLE
            if identity is not None
            else _UNAVAILABLE
        ),
        "detector_preprocessing_version": (
            identity.preprocessing_version or _UNAVAILABLE
            if identity is not None
            else _UNAVAILABLE
        ),
        "xai_explainer": (
            explainer.name if explainer is not None else _NOT_IMPLEMENTED
        ),
        "xai_explainer_version": (
            explainer.version if explainer is not None else _NOT_IMPLEMENTED
        ),
        "xai_technique": (
            explainer.technique if explainer is not None else _NOT_IMPLEMENTED
        ),
        "forensic_analyzer_versions": _json(analyzer_versions)
        if analyzer_versions
        else _UNAVAILABLE,
        "confidence_methodology_version": (
            inputs.confidence.methodology_version
            if inputs.confidence is not None
            else _UNAVAILABLE
        ),
        "risk_methodology_version": (
            inputs.risk.methodology_version if inputs.risk is not None else _UNAVAILABLE
        ),
        "verdict_methodology_version": (
            inputs.verdict.methodology_version
            if inputs.verdict is not None
            else _UNAVAILABLE
        ),
        "report_version": "1",
    }
    return dict(sorted(methodology.items()))


def _limitations(inputs: ReportInputs) -> list[str]:
    limitations: list[str] = []
    if inputs.evidence is not None:
        limitations.extend(inputs.evidence.limitations)
    if inputs.confidence is not None:
        limitations.extend(inputs.confidence.limitations)
    if inputs.detection is not None and inputs.detection.inference.status == "UNAVAILABLE":
        limitations.append(
            "detector unavailable: "
            + (inputs.detection.inference.reason or "no detector model produced a prediction")
        )
    if inputs.xai is not None and inputs.xai.status == "UNAVAILABLE":
        limitations.append(
            "XAI unavailable: " + (inputs.xai.reason or "no compatible detector/explainer")
        )
    if inputs.confidence is None or (
        inputs.confidence.confidence_status is not ConfidenceStatus.SUFFICIENT_EVIDENCE
    ):
        limitations.append(
            "confidence not calibrated: no validated, calibrated methodology is "
            "registered in this build"
        )
    if inputs.risk is not None and inputs.risk.risk_level is RiskLevel.UNDETERMINED:
        limitations.append(
            "risk methodology cannot produce a supported level without an "
            "established directional assessment"
        )
    if inputs.verdict is not None and inputs.verdict.verdict is VerdictStatus.INSUFFICIENT_EVIDENCE:
        limitations.append(
            "verdict remains insufficient: not enough validated evidence for a "
            "stronger conclusion"
        )
    if inputs.forensics:
        limitations.append(
            "visual forensic measurements are observational and content-dependent"
        )
    limitations.append("no face/identity assessment was performed in this build")
    return _dedupe(limitations)


def _present(value: object) -> str:
    return "present" if bool(value) else "absent"


def _join(value: object) -> str:
    if not isinstance(value, list):
        return ""
    return ", ".join(str(item) for item in value if item)
