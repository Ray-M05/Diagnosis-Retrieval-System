"""Clinical positioning module.

Transforms reranked retrieval chunks into positioned clinical conditions.
"""

from sri_dx.modules.positioning.config import PositioningConfig
from sri_dx.modules.positioning.models import (
    ClinicalGroup,
    PositionedClinicalResult,
    PositioningCandidate,
    PositioningEvidence,
)
from sri_dx.modules.positioning.service import ClinicalPositioningService

__all__ = [
    "ClinicalGroup",
    "ClinicalPositioningService",
    "PositionedClinicalResult",
    "PositioningCandidate",
    "PositioningConfig",
    "PositioningEvidence",
]
