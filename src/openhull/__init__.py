"""OpenHull — agent-orchestrated parametric ship preliminary design.

From a task book (ship type, deadweight, service speed, trading range)
to principal dimensions, hydrostatics, a lines plan, performance
estimates, and drawing outputs — with every quantity validated against
published benchmark ships (see AGENTS.md for the binding conventions).
"""

from importlib.metadata import PackageNotFoundError, version

from .drawing import (
    draw_lines_plan,
    save_offsets_csv,
)
from .fairness import (
    FairnessIssue,
    FairnessReport,
    check_fairness,
)
from .geometry import (
    JBC_KM_TARGET_M,
    OffsetsTable,
    jbc_parent_offsets,
    load_offsets_csv,
)
from .linesplan import (
    LackenbyReport,
    TRANSFORM_ALGORITHMS,
    area_curve,
    lackenby_transform,
)
from .freeboard import (
    FreeboardResult,
    TABLE_3_9_BASIC_FREEBOARD,
    minimum_freeboard,
    tabular_basic_freeboard,
)
from .hydrostatics import (
    bonjean_areas,
    hydrostatics_at,
    hydrostatics_table,
    simpson,
    trapezoid,
    waterplane,
)
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
from .stability import (
    BUOYANCY_TOLERANCE,
    LCG_TOLERANCE,
    FloatingPosition,
    InitialStability,
    Tank,
    TrimStep,
    floating_position,
    free_surface_correction,
    initial_stability,
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
    "BUOYANCY_TOLERANCE",
    "JBC_KM_TARGET_M",
    "FloatingPosition",
    "FreeboardResult",
    "FairnessIssue",
    "FairnessReport",
    "InitialStability",
    "LCG_TOLERANCE",
    "LackenbyReport",
    "OffsetsTable",
    "TABLE_3_9_BASIC_FREEBOARD",
    "Tank",
    "TRANSFORM_ALGORITHMS",
    "TrimStep",
    "bulkcarrier_deadweight_ratio_statistics",
    "bonjean_areas",
    "estimate_main_dimensions",
    "check_fairness",
    "floating_position",
    "free_surface_correction",
    "hydrostatics_at",
    "hydrostatics_table",
    "initial_stability",
    "jbc_parent_offsets",
    "knots_to_ms",
    "lackenby_transform",
    "area_curve",
    "draw_lines_plan",
    "load_offsets_csv",
    "minimum_freeboard",
    "ms_to_knots",
    "outfit_area_coefficient_from_parent",
    "save_offsets_csv",
    "simpson",
    "solve_weight_balance",
    "steel_cubic_coefficient_from_parent",
    "steel_exponent_coefficient_from_parent",
    "tabular_basic_freeboard",
    "trapezoid",
    "waterplane",
]
