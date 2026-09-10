"""OpenHull — agent-orchestrated parametric ship preliminary design.

From a task book (ship type, deadweight, service speed, trading range)
to principal dimensions, hydrostatics, a lines plan, performance
estimates, and drawing outputs — with every quantity validated against
published benchmark ships (see AGENTS.md for the binding conventions).
"""

from importlib.metadata import PackageNotFoundError, version

from .main_dimensions import (
    DEFAULT_ALGORITHM,
    MAIN_DIMENSION_ALGORITHMS,
    AlgorithmInfo,
    RatioParameters,
    estimate_main_dimensions,
)
from .spec import (
    SEAWATER_DENSITY,
    Hydrostatics,
    HydrostaticsTable,
    ShipSpec,
    SpecValidationError,
    knots_to_ms,
    ms_to_knots,
)
from .weight_balance import (
    BULK_CARRIER_STEEL_EXPONENTS,
    DEFAULT_WEIGHT_ALGORITHM,
    WEIGHT_ALGORITHMS,
    BalanceStep,
    ComponentWeightParameters,
    LightweightBreakdown,
    WeightAlgorithmInfo,
    WeightBalanceResult,
    bulkcarrier_deadweight_ratio_statistics,
    outfit_area_coefficient_from_parent,
    solve_weight_balance,
    steel_cubic_coefficient_from_parent,
    steel_exponent_coefficient_from_parent,
)

try:
    __version__ = version("openhull")
except PackageNotFoundError:  # running from a source tree without install
    __version__ = "0.0.0.dev0"

__all__ = [
    "__version__",
    "SEAWATER_DENSITY",
    "DEFAULT_ALGORITHM",
    "MAIN_DIMENSION_ALGORITHMS",
    "AlgorithmInfo",
    "DEFAULT_WEIGHT_ALGORITHM",
    "WEIGHT_ALGORITHMS",
    "BalanceStep",
    "ComponentWeightParameters",
    "Hydrostatics",
    "HydrostaticsTable",
    "LightweightBreakdown",
    "RatioParameters",
    "ShipSpec",
    "SpecValidationError",
    "WeightAlgorithmInfo",
    "WeightBalanceResult",
    "BULK_CARRIER_STEEL_EXPONENTS",
    "bulkcarrier_deadweight_ratio_statistics",
    "estimate_main_dimensions",
    "knots_to_ms",
    "ms_to_knots",
    "outfit_area_coefficient_from_parent",
    "solve_weight_balance",
    "steel_cubic_coefficient_from_parent",
    "steel_exponent_coefficient_from_parent",
]
