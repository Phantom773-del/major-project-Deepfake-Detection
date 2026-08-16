"""Normalize each source's persisted ``result_ref`` payload into evidence items.

Every normalizer only reads keys the source stage actually persists (never
client input), keeps the shared ``EvidenceType`` from the payload, and treats a
missing/absent signal as an honest UNAVAILABLE — never as negative evidence.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.domain.taxonomy import EvidenceType
from app.evidence.domain import (
    EvidenceAvailability,
    EvidenceCategory,
    EvidenceDirection,
    EvidenceItem,
    EvidenceSource,
)

logger = logging.getLogger(__name__)

# Correlated signal groups. Within one group only the first item counts toward
# the independent evidence count (see aggregator).
CORRELATION_VISUAL_COMPRESSION = "visual-compression"
CORRELATION_MODEL_INFERENCE = "model-inference"

CORRELATION_NOTE = (
    "ELA and frequency analyzers are both influenced by JPEG compression and "
    "form the visual-compression group; XAI explains the same detector inference "
    "and forms the model-inference group. Within a group only the first item "
    "counts toward independent_count, so correlated signals are never treated as "
    "fully independent."
)

_SOURCE_LABEL = {
    EvidenceSource.FINGERPRINT: "fingerprint",
    EvidenceSource.METADATA: "metadata",
    EvidenceSource.DETECTION: "detection",
    EvidenceSource.VISUAL_FORENSICS: "visual forensics",
    EvidenceSource.XAI: "xai",
}

# Detection label -> (category, direction). Unknown labels fall back to a
# neutral model-behavior observation (no over-claiming).
_DETECTION_LABEL_META: dict[str, tuple[EvidenceCategory, EvidenceDirection]] = {
    "FAKE": (EvidenceCategory.SYNTHETIC_GENERATION, EvidenceDirection.SUPPORTING_SYNTHETIC),
    "REAL": (EvidenceCategory.AUTHENTICITY, EvidenceDirection.SUPPORTING_AUTHENTICITY),
}

# Metadata finding code -> (category, direction). Unknown codes stay neutral.
_METADATA_FINDING_META: dict[str, tuple[EvidenceCategory, EvidenceDirection]] = {
    "gps_present": (EvidenceCategory.PROVENANCE, EvidenceDirection.NEUTRAL),
    "editing_software_metadata": (
        EvidenceCategory.PROVENANCE,
        EvidenceDirection.SUPPORTING_EDITING_HISTORY,
    ),
    "capture_later_than_modification": (
        EvidenceCategory.METADATA_CONSISTENCY,
        EvidenceDirection.SUPPORTING_EDITING_HISTORY,
    ),
    "exif_orientation_out_of_range": (
        EvidenceCategory.METADATA_CONSISTENCY,
        EvidenceDirection.SUPPORTING_EDITING_HISTORY,
    ),
    "implausible_iso": (
        EvidenceCategory.METADATA_CONSISTENCY,
        EvidenceDirection.SUPPORTING_EDITING_HISTORY,
    ),
    "implausible_exposure_time": (
        EvidenceCategory.METADATA_CONSISTENCY,
        EvidenceDirection.SUPPORTING_EDITING_HISTORY,
    ),
    "format_mime_mismatch": (
        EvidenceCategory.METADATA_CONSISTENCY,
        EvidenceDirection.NEUTRAL,
    ),
}

# Forensics analyzers whose measurements are compression-influenced.
_VISUAL_COMPRESSION_ANALYZERS = ("ela", "frequency")


@dataclass(frozen=True)
class NormalizedSource:
    """Normalized output for one source payload."""

    items: tuple[EvidenceItem, ...]
    availability: EvidenceAvailability
    limitations: tuple[str, ...]

    def __iter__(self) -> Any:
        """Unpack as ``(items, availability, limitations)``."""
        yield self.items
        yield self.availability
        yield self.limitations


def normalize_source(
    source: EvidenceSource, payload: dict[str, Any]
) -> NormalizedSource:
    """Normalize one source payload into evidence items."""
    normalizer = _NORMALIZERS.get(source)
    if normalizer is None:
        return NormalizedSource(
            (), EvidenceAvailability.UNAVAILABLE, (f"{_SOURCE_LABEL[source]} is not supported",)
        )
    return normalizer(payload)


def _normalize_fingerprint(payload: dict[str, Any]) -> NormalizedSource:
    items: list[EvidenceItem] = []
    sha256 = payload.get("sha256")
    if isinstance(sha256, str) and sha256:
        items.append(
            EvidenceItem(
                code="fingerprint.sha256",
                source=EvidenceSource.FINGERPRINT,
                category=EvidenceCategory.FILE_INTEGRITY,
                evidence_type=EvidenceType.VERIFIED,
                observation="Byte-level SHA-256 fingerprint was computed for the stored file",
                interpretation=(
                    "SHA-256 uniquely identifies the file bytes; it verifies file "
                    "integrity, never authenticity"
                ),
                direction=EvidenceDirection.NEUTRAL,
                details={
                    "sha256": sha256,
                    "size_bytes": payload.get("size_bytes"),
                },
            )
        )
    d_hash = payload.get("d_hash")
    if isinstance(d_hash, str) and d_hash:
        items.append(
            EvidenceItem(
                code="fingerprint.dhash",
                source=EvidenceSource.FINGERPRINT,
                category=EvidenceCategory.FILE_INTEGRITY,
                evidence_type=EvidenceType.HEURISTIC,
                observation="Perceptual dHash fingerprint was computed for the stored image",
                interpretation=(
                    "A dHash supports near-duplicate detection; it is a heuristic "
                    "signal, not proof of authenticity"
                ),
                direction=EvidenceDirection.NEUTRAL,
                details={"d_hash": d_hash},
            )
        )
    if not items:
        return NormalizedSource(
            (),
            EvidenceAvailability.UNAVAILABLE,
            ("fingerprint result carried no usable fingerprint",),
        )
    return NormalizedSource(tuple(items), EvidenceAvailability.AVAILABLE, ())


def _normalize_metadata(payload: dict[str, Any]) -> NormalizedSource:
    items: list[EvidenceItem] = []
    presence = payload.get("presence")
    if isinstance(presence, dict):
        for key in ("exif", "xmp", "icc", "gps"):
            is_present = presence.get(key)
            if is_present is True:
                items.append(
                    EvidenceItem(
                        code=f"metadata.{key}_present",
                        source=EvidenceSource.METADATA,
                        category=EvidenceCategory.PROVENANCE,
                        evidence_type=EvidenceType.VERIFIED,
                        observation=f"{key.upper()} metadata is present in the file",
                        interpretation=(
                            "Presence of metadata is an observation, not an "
                            "authenticity or manipulation signal"
                        ),
                        direction=EvidenceDirection.NEUTRAL,
                    )
                )
            elif is_present is False:
                items.append(
                    EvidenceItem(
                        code=f"metadata.{key}_absent",
                        source=EvidenceSource.METADATA,
                        category=EvidenceCategory.PROVENANCE,
                        evidence_type=EvidenceType.VERIFIED,
                        observation=f"No {key.upper()} metadata is present in the file",
                        interpretation=(
                            f"Absence of {key.upper()} metadata is not evidence of "
                            "AI generation or manipulation"
                        ),
                        direction=EvidenceDirection.NEUTRAL,
                    )
                )
    software = payload.get("software")
    if isinstance(software, list) and software:
        listed = ", ".join(str(value) for value in software[:10])
        items.append(
            EvidenceItem(
                code="metadata.software_present",
                source=EvidenceSource.METADATA,
                category=EvidenceCategory.PROVENANCE,
                evidence_type=EvidenceType.VERIFIED,
                observation=f"File records software processing metadata: {listed}",
                interpretation=(
                    "Software metadata indicates the file was processed by "
                    "software; processing is not evidence of AI generation"
                ),
                direction=EvidenceDirection.NEUTRAL,
            )
        )
    consistency = payload.get("consistency")
    if isinstance(consistency, dict):
        findings = consistency.get("findings")
        if isinstance(findings, list):
            for finding in findings:
                if isinstance(finding, dict):
                    item = _metadata_finding_item(finding)
                    if item is not None:
                        items.append(item)
    if not items:
        return NormalizedSource(
            (),
            EvidenceAvailability.UNAVAILABLE,
            ("metadata result carried no usable evidence",),
        )
    limitations: list[str] = []
    provenance = payload.get("provenance")
    if isinstance(provenance, dict) and provenance.get("status") == "UNAVAILABLE":
        limitations.append("C2PA provenance is unavailable: not implemented in this build")
    return NormalizedSource(tuple(items), EvidenceAvailability.AVAILABLE, tuple(limitations))


def _metadata_finding_item(finding: dict[str, Any]) -> EvidenceItem | None:
    code = finding.get("code")
    message = finding.get("message")
    if not isinstance(code, str) or not code:
        return None
    category, direction = _METADATA_FINDING_META.get(
        code, (EvidenceCategory.METADATA_CONSISTENCY, EvidenceDirection.NEUTRAL)
    )
    return EvidenceItem(
        code=f"metadata.{code}",
        source=EvidenceSource.METADATA,
        category=category,
        evidence_type=_parse_evidence_type(finding.get("evidence_type")),
        observation=message or f"metadata finding {code}",
        interpretation=_finding_interpretation(direction),
        direction=direction,
    )


def _finding_interpretation(direction: EvidenceDirection) -> str:
    if direction is EvidenceDirection.SUPPORTING_EDITING_HISTORY:
        return (
            "This inconsistency is heuristic evidence of metadata editing or "
            "corruption; it does not establish manipulation or AI generation "
            "on its own"
        )
    return (
        "The finding is an observation; it does not establish manipulation or "
        "AI generation on its own"
    )


def _normalize_detection(payload: dict[str, Any]) -> NormalizedSource:
    if not isinstance(payload.get("prediction"), dict):
        return NormalizedSource(
            (),
            EvidenceAvailability.UNAVAILABLE,
            ("detection produced no model prediction in this build",),
        )
    if payload.get("evidence_type") != EvidenceType.INFERENCE.value:
        return NormalizedSource(
            (),
            EvidenceAvailability.UNAVAILABLE,
            ("detection result is not classified as model inference evidence",),
        )
    inference = payload.get("inference")
    if not isinstance(inference, dict) or inference.get("status") != "AVAILABLE":
        return NormalizedSource(
            (),
            EvidenceAvailability.UNAVAILABLE,
            ("detection inference is not available",),
        )
    prediction = payload.get("prediction")
    if not isinstance(prediction, dict):
        return NormalizedSource(
            (),
            EvidenceAvailability.UNAVAILABLE,
            ("detection result carries no prediction",),
        )
    label = str(prediction.get("label"))
    category, direction = _DETECTION_LABEL_META.get(
        label.upper(), (EvidenceCategory.MODEL_BEHAVIOR, EvidenceDirection.NEUTRAL)
    )
    detector = payload.get("detector")
    detector_name = (
        detector.get("name") if isinstance(detector, dict) else "unknown detector"
    )
    model_name = detector.get("model_name") if isinstance(detector, dict) else None
    model_version = detector.get("model_version") if isinstance(detector, dict) else None
    checkpoint = (
        detector.get("checkpoint_sha256") if isinstance(detector, dict) else None
    )
    score = prediction.get("score")
    semantics = prediction.get("score_semantics")
    device = inference.get("device")
    item = EvidenceItem(
        code="detection.prediction",
        source=EvidenceSource.DETECTION,
        category=category,
        evidence_type=EvidenceType.INFERENCE,
        observation=(
            f"Detector {detector_name!r} inferred label {label!r} for the media"
        ),
        interpretation=(
            f"Model inference only: label {label!r} with score {score} "
            f"({semantics}); a model output is not forensic truth"
        ),
        direction=direction,
        correlation_group=CORRELATION_MODEL_INFERENCE,
        details={
            "label": label,
            "score": score,
            "score_semantics": semantics,
            "model_name": model_name,
            "model_version": model_version,
            "checkpoint_sha256": checkpoint,
            "device": device,
        },
    )
    return NormalizedSource((item,), EvidenceAvailability.AVAILABLE, ())


def _normalize_forensics(payload: dict[str, Any]) -> NormalizedSource:
    analyzers = payload.get("analyzers")
    if not isinstance(analyzers, dict) or not analyzers:
        return NormalizedSource(
            (),
            EvidenceAvailability.UNAVAILABLE,
            ("forensics result carried no analyzer output",),
        )
    items: list[EvidenceItem] = []
    failures: list[str] = []
    for name in sorted(analyzers):
        block = analyzers[name]
        if not isinstance(block, dict):
            continue
        if block.get("status") == "COMPLETED":
            items.append(_forensics_item(name, block))
        else:
            error = block.get("error")
            failures.append(
                f"analyzer {name} failed: {error if isinstance(error, str) else 'unknown error'}"
            )
    if not items:
        return NormalizedSource((), EvidenceAvailability.FAILED, tuple(failures))
    return NormalizedSource(tuple(items), EvidenceAvailability.AVAILABLE, tuple(failures))


def _forensics_item(name: str, block: dict[str, Any]) -> EvidenceItem:
    correlation = (
        CORRELATION_VISUAL_COMPRESSION
        if name in _VISUAL_COMPRESSION_ANALYZERS
        else None
    )
    return EvidenceItem(
        code=f"forensics.{name}",
        source=EvidenceSource.VISUAL_FORENSICS,
        category=EvidenceCategory.VISUAL_ANOMALY,
        evidence_type=EvidenceType.VERIFIED,
        observation=f"{name} analyzer produced measurements over the image",
        interpretation=_forensics_interpretation(name, block),
        direction=EvidenceDirection.NEUTRAL,
        correlation_group=correlation,
        details={
            "analyzer": name,
            "version": block.get("version"),
            "parameters": block.get("parameters"),
            "measurements": block.get("measurements"),
        },
    )


def _forensics_interpretation(name: str, block: dict[str, Any]) -> str:
    findings = block.get("findings")
    if isinstance(findings, list):
        for finding in findings:
            message = finding.get("message") if isinstance(finding, dict) else None
            if (
                isinstance(finding, dict)
                and finding.get("evidence_type") == EvidenceType.HEURISTIC.value
                and isinstance(message, str)
            ):
                return message
    return (
        f"{name} measurements are a visual signal; they are observations, "
        "not a manipulation or AI verdict"
    )


def _normalize_xai(payload: dict[str, Any]) -> NormalizedSource:
    if payload.get("status") != "COMPLETED":
        return NormalizedSource(
            (),
            EvidenceAvailability.UNAVAILABLE,
            ("xai produced no model explanation in this build",),
        )
    explainer = payload.get("explainer")
    model = payload.get("model")
    heatmap = payload.get("heatmap")
    technique = (
        explainer.get("technique") if isinstance(explainer, dict) else None
    )
    model_name = model.get("name") if isinstance(model, dict) else None
    heatmap_available = isinstance(heatmap, dict) and heatmap.get("available") is True
    heatmap_format: object = None
    if heatmap_available and isinstance(heatmap, dict):
        heatmap_format = heatmap.get("format")
    observation = "XAI explained the detector's inference"
    if isinstance(technique, str) and technique:
        observation = f"{observation} using technique {technique!r}"
    item = EvidenceItem(
        code="xai.explanation",
        source=EvidenceSource.XAI,
        category=EvidenceCategory.MODEL_BEHAVIOR,
        evidence_type=EvidenceType.INFERENCE,
        observation=observation,
        interpretation=(
            "An explanation reflects the model's behavior; it is not ground-truth "
            "evidence that highlighted regions were manipulated"
        ),
        direction=EvidenceDirection.NEUTRAL,
        correlation_group=CORRELATION_MODEL_INFERENCE,
        details={
            "technique": technique,
            "model_name": model_name,
            "heatmap_available": heatmap_available,
            "heatmap_format": heatmap_format,
        },
    )
    return NormalizedSource((item,), EvidenceAvailability.AVAILABLE, ())


def _parse_evidence_type(value: object) -> EvidenceType:
    try:
        return EvidenceType(str(value))
    except ValueError:
        return EvidenceType.UNKNOWN


_NORMALIZERS: dict[EvidenceSource, Callable[[dict[str, Any]], NormalizedSource]] = {
    EvidenceSource.FINGERPRINT: _normalize_fingerprint,
    EvidenceSource.METADATA: _normalize_metadata,
    EvidenceSource.DETECTION: _normalize_detection,
    EvidenceSource.VISUAL_FORENSICS: _normalize_forensics,
    EvidenceSource.XAI: _normalize_xai,
}
