"""Scan lifecycle: state machine and pipeline stage ordering.

The scan state machine is the single source of truth for valid transitions.
Status changes are enforced here, never in API routes directly.
"""

from collections.abc import Mapping

from app.domain.exceptions import ConflictError
from app.domain.taxonomy import ScanStatus

# Pipeline stages created (as pending rows) when a scan is created.
# Adding a future stage = add a name here; no schema change required.
STAGE_ORDER: tuple[str, ...] = (
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

# Allowed transitions. FAILED is terminal: retries are not supported yet.
SCAN_TRANSITIONS: Mapping[ScanStatus, frozenset[ScanStatus]] = {
    ScanStatus.CREATED: frozenset({ScanStatus.VALIDATING}),
    ScanStatus.VALIDATING: frozenset({ScanStatus.QUEUED, ScanStatus.FAILED}),
    ScanStatus.QUEUED: frozenset({ScanStatus.PROCESSING}),
    ScanStatus.PROCESSING: frozenset({ScanStatus.COMPLETED, ScanStatus.FAILED}),
    ScanStatus.COMPLETED: frozenset(),
    ScanStatus.FAILED: frozenset(),
}


def can_transition(current: ScanStatus, target: ScanStatus) -> bool:
    """Return whether ``target`` is a legal successor of ``current``."""
    return target in SCAN_TRANSITIONS[current]


def assert_transition(current: ScanStatus, target: ScanStatus) -> None:
    """Raise ConflictError if the transition is not allowed."""
    if current == target:
        raise ConflictError(f"scan is already in state {target.value}")
    if not can_transition(current, target):
        raise ConflictError(
            f"invalid scan transition {current.value} -> {target.value}; "
            f"allowed: {sorted(s.value for s in SCAN_TRANSITIONS[current])}"
        )
