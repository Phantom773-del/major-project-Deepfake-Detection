"""Detection contract: detector abstraction, identities, and results.

A detector performs model inference over stored media and returns a structured,
evidence-classified result. Detectors never touch the database — persistence is
the pipeline/stage layer's job (``ScanStage.result_ref``).

Scientific honesty rules baked into this module:
- A detector result is MODEL INFERENCE, never ground truth and never a verdict.
- ``score`` carries an explicit ``score_semantics`` string declaring the value's
  mathematical meaning (e.g. "sigmoid probability"); raw logits are not called
  probabilities.
- A missing/unavailable model yields an explicit ``UNAVAILABLE`` result with no
  prediction — never a fabricated one.
"""

from pathlib import Path
from typing import Literal, Protocol

from pydantic import BaseModel, Field

from app.domain.taxonomy import EvidenceType, MediaType

# Version of this detector contract/abstraction. Adapters report their own
# adapter version separately from any underlying model version.
DETECTOR_CONTRACT_VERSION = "1"


class DetectorError(Exception):
    """Client-safe failure raised by a detector.

    ``message`` must not contain filesystem paths, stack traces, model internals,
    or secrets.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class DetectorIdentity(BaseModel):
    """Everything needed to identify which code/model produced a result.

    ``model_*`` fields refer to the underlying inference model; ``checkpoint_sha256``
    is set only when an actual checkpoint hash is known (never invented).
    """

    name: str
    detector_version: str = DETECTOR_CONTRACT_VERSION
    model_name: str | None = None
    model_version: str | None = None
    checkpoint_sha256: str | None = None
    preprocessing_version: str | None = None


class DetectionPrediction(BaseModel):
    """A single model inference output.

    ``score`` is a value in [0, 1]; its meaning is declared by ``score_semantics``
    (e.g. "sigmoid probability", "softmax probability"). It is a model score, not
    a probability that the media is fake.
    """

    label: str = Field(min_length=1)
    score: float = Field(ge=0.0, le=1.0)
    score_semantics: str = Field(min_length=1)
    class_list: tuple[str, ...] | None = None


class InferenceSummary(BaseModel):
    """Execution metadata around one detection run."""

    status: Literal["AVAILABLE", "UNAVAILABLE"]
    reason: str | None = None
    device: str | None = None
    duration_ms: int | None = None


class DetectionResult(BaseModel):
    """Stable structured output of one detection run (persisted to result_ref).

    ``evidence_type`` is set to ``INFERENCE`` only when a real prediction exists;
    an unavailable result carries no evidence at all.
    """

    detector: DetectorIdentity
    media_type: MediaType
    prediction: DetectionPrediction | None = None
    inference: InferenceSummary
    evidence_type: EvidenceType | None = None


class Detector(Protocol):
    """Stable detector contract.

    ``media_type`` declares which media category this detector serves. ``detect``
    is synchronous (heavy inference) — the pipeline executes it off the event loop.
    """

    name: str
    media_type: MediaType

    @property
    def identity(self) -> DetectorIdentity:
        """Identity of this detector adapter and its underlying model."""
        ...

    def detect(self, path: Path, *, device: str) -> DetectionResult:
        """Run inference over ``path``. Raise ``DetectorError`` on failure."""
        ...
