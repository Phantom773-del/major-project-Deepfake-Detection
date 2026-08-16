"""XAI contract: explainer abstraction, identities, results, and contexts.

Explainable AI produces an explanation for a *genuine* detector inference. A
heatmap is only valid if it comes from an actual model execution — the XAI layer
must never fabricate activation maps, never claim a region influenced a
prediction that no model produced, and never independently load a checkpoint
that differs from the detector's real model.

Scientific honesty rules baked into this module:
- An explainer receives the ``DetectionResult`` the pipeline actually produced
  plus the detector instance that produced it, so any explanation corresponds
  to the same inference — never a different model.
- With no compatible model, the result is ``UNAVAILABLE`` with a clear reason;
  ``UNAVAILABLE`` is an honest system state, not an error.
- ``UNAVAILABLE`` results carry no heatmap and no numerical interpretation.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

from pydantic import BaseModel, Field

from app.core.config import Settings
from app.domain.taxonomy import MediaType
from app.inference.base import DetectionResult, Detector

# Version of this XAI contract/abstraction. Explainers report their own
# explainer version separately from the detector/model contract version.
XAI_CONTRACT_VERSION = "1"


class XAIError(Exception):
    """Client-safe failure raised by an XAI explainer.

    ``message`` must not contain filesystem paths, stack traces, model
    internals, or secrets.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ExplainerIdentity(BaseModel):
    """Identity of the explainer implementation and technique used."""

    name: str
    version: str = XAI_CONTRACT_VERSION
    technique: str
    model_type: str | None = None


class XAIModelIdentity(BaseModel):
    """Which model the explanation refers to — the detector's model, never an
    independently loaded checkpoint.

    All fields come from the detection result's ``DetectorIdentity``; ``None``
    means the detection used no real model.
    """

    name: str | None = None
    version: str | None = None
    checkpoint_sha256: str | None = None


class XAIHeatmap(BaseModel):
    """Metadata of a real activation map produced by an actual model execution.

    ``reference`` points at the persisted artifact (internal storage reference);
    it is never fabricated. When ``available`` is ``True`` every field is set.
    """

    available: bool = False
    format: str | None = None
    width: int | None = None
    height: int | None = None
    reference: str | None = None


class XAIInterpretation(BaseModel):
    """Human-oriented explanation tied to the model's actual prediction.

    ``target_score`` is only present when the detector produced a real score and
    is always paired with ``score_semantics`` (same rule as detection).
    """

    target_label: str | None = None
    target_score: float | None = Field(default=None, ge=0.0, le=1.0)
    score_semantics: str | None = None
    summary: str | None = None
    limitation: str | None = None


class XAIResult(BaseModel):
    """Stable structured output of one explanation run (persisted to result_ref).

    ``status`` is ``COMPLETED`` only for a real explanation of a real
    prediction; otherwise it is ``UNAVAILABLE`` with an explicit ``reason`` and
    no heatmap/interpretation.
    """

    status: Literal["COMPLETED", "UNAVAILABLE"]
    reason: str | None = None
    explainer: ExplainerIdentity | None = None
    model: XAIModelIdentity | None = None
    heatmap: XAIHeatmap | None = None
    interpretation: XAIInterpretation | None = None


@dataclass(frozen=True)
class XAIExplanationContext:
    """Everything an explainer may use to explain the *same* detector inference.

    ``detector`` is the exact detector instance the pipeline used for detection
    (resolved from the same registry by name) — an explainer never loads its own
    arbitrary checkpoint. Model-specific adapters (e.g. Grad-CAM for a specific
    architecture) pull their target layers from ``detector``; generic XAI code
    must not hard-code model-specific internals.
    """

    detector: Detector
    detection: DetectionResult
    device: str


class XAIExplainer(Protocol):
    """Stable explainer contract.

    ``media_type`` declares which media category the explainer serves;
    ``model_type`` declares which detector model it can explain (``None`` means
    any/unavailable fallback). ``explain`` is synchronous (heavy model work) —
    the pipeline executes it off the event loop.
    """

    name: str
    version: str
    technique: str
    media_type: MediaType
    model_type: str | None

    def explain(
        self,
        path: Path,
        *,
        context: XAIExplanationContext,
        settings: Settings,
    ) -> XAIResult:
        """Explain the detection over ``path``. Raise ``XAIError`` on failure."""
        ...
