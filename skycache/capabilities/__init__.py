"""Legal capability registry for SkyCache / Skybrary worldwide deployment."""

from skycache.capabilities.matrix import CapabilityMatrix, build_capability_matrix
from skycache.capabilities.modes import (
    LegalRfMode,
    satellite_receive_only_ok,
    validate_legal_rf_mode,
)

__all__ = [
    "CapabilityMatrix",
    "LegalRfMode",
    "build_capability_matrix",
    "satellite_receive_only_ok",
    "validate_legal_rf_mode",
]
