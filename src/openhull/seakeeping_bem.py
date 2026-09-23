"""Stage-2 seakeeping: rigid-body RAOs via capytaine (plan task 3.8, stage 2).

capytaine (Apache-2.0 BEM solver, potential flow) is an OPTIONAL
dependency — owner decision 2026-09-23 ("两个都往下推"): install with
`pip install openhull[seakeeping]`; this module imports it lazily and
refuses cleanly when absent.  The no-CFD red line (AGENTS.md section 7)
concerns viscous resistance simulation; linear potential-flow seakeeping
was planned as task 3.8 stage 2 from the roadmap onward and approved
by the owner on 2026-09-23.

Division of labour (this module's honest architecture):

- capytaine supplies the HYDRODYNAMICS only: added mass, radiation
  damping and wave excitation on a panel mesh built from the SAME
  offsets table every other module reads (no new geometry).
- the mass/inertia/hydrostatic-stiffness matrices of the RAO
  equation of motion come from the whitelisted chain, NOT from the
  panel mesh: displacement from the task 1.4 table, roll inertia
  from the Duell form Ixx' = D/(12g)(B^2 + 4zg^2) (Ship Theory
  vol. 2 Eq. 3-39, p.389), pitch inertia from KYY = 0.25*L
  (ibid. p.428), heave stiffness rho*g*Aw and roll/pitch stiffness
  rho*grad*GM from the task 1.4 hydrostatics and the task-book KG.

Mesh: the tabulated half-breadths are lofted into a quad surface.
Rows run over the tabulated waterlines up to the first table waterline
ABOVE the design draft (that row closes the hull as the deck; a face
exactly AT the waterline would be treated as a removable lid by
capytaine and silently drops the bottom-face contribution of the
Froude-Krylov integral — verified against the analytic rho*g*Aw value,
2026-09-23).  Declared approximations: the dry strip between the
design draft and the deck carries Airy-decayed pressure (preliminary
level); surge/sway/yaw are suppressed from the RAO (motions about the
mean position); zero forward speed (head/beam distinction by wave
direction only, beta = 0 head in the Nemoh convention — at zero
speed beta = 0 and beta = pi give identical magnitudes by symmetry);
roll/pitch hydrostatic coupling neglected (diagonal matrices).
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any

from .seakeeping import (
    DEFAULT_ROLL_MU,
    GRAVITY_M_S2,
    roll_period_regulation,
)
from .spec import SpecValidationError

__all__ = [
    "CapytaineUnavailable",
    "require_capytaine",
    "build_hull_body",
    "RaoPoint",
    "RaoResult",
    "compute_rigid_rao",
]

_CITATION_MESH = (
    "OpenHull offsets table lofted to panels (task 2.6 hull); deck at "
    "the first table waterline above the design draft"
)
_CITATION_MASS = (
    "Ship Theory vol. 2: displacement/task 1.4; roll inertia Eq.(3-39) "
    "p.389; pitch inertia radius KYY = 0.25*L p.428"
)
_CITATION_STIFFNESS = (
    "hydrostatic stiffness rho*g*Aw / rho*grad*GM from the task 1.4 "
    "table and the task-book KG"
)


class CapytaineUnavailable(ImportError):
    """Raised when capytaine is not installed in the environment."""


def require_capytaine():
    """Import and return the capytaine module or raise with guidance."""
    try:
        import capytaine as cpt
    except ImportError as error:  # pragma: no cover - environment-dependent
        raise CapytaineUnavailable(
            "capytaine is not installed; stage-2 seakeeping needs the "
            "optional dependency: pip install 'openhull[seakeeping]' "
            "(or pip install capytaine)"
        ) from error
    cpt.set_logging("ERROR")
    return cpt


def _require(condition: bool, field: str, value: Any, constraint: str,
             reason: str) -> None:
    if not condition:
        raise SpecValidationError(field, value, constraint, reason)


def build_hull_body(table, draft: float, deck_z: float | None = None):
    """Loft the offsets table into a closed capytaine body.

    Args:
        table: OffsetsTable (task 2.6 hull, real offsets).
        draft: design draft, m.
        deck_z: optional explicit deck height, m.  Default: the first
            tabulated waterline strictly above the draft, or 1.15 x
            draft wall-sided when the table stops at the draft.  The
            volume-vs-table cross-check passes deck_z=draft so the
            enclosed volume corresponds exactly to the displacement
            volume.
            Breadths at the deck row are the top tabulated waterline's
            (wall-sided, the task 3.4 declared approximation) unless
            the deck row is a real table waterline.

    Returns:
        (body, info) where body is a merged capytaine FloatingBody
        with Heave/Roll/Pitch dofs about (midship, 0, T/2), and info
        carries the mesh audit (volume, faces, deck height).
    """
    cpt = require_capytaine()
    import numpy as np

    _require(math.isfinite(draft) and draft > 0.0,
             "draft", draft, "finite T > 0", "draft must be positive")
    waterlines = [float(z) for z in table.waterlines]
    above = [z for z in waterlines if z > draft * (1.0 + 1e-9)]
    wet_rows = [z for z in waterlines if z <= draft * (1.0 + 1e-9)]
    _require(bool(wet_rows),
             "draft", draft, "table waterlines at or below the draft",
             "the offsets table carries no waterline at or below the "
             f"design draft {draft:.3f} m")
    if deck_z is not None:
        _require(math.isfinite(deck_z) and deck_z >= draft * (1.0 - 1e-9),
                 "deck_z", deck_z, "deck_z >= draft",
                 "the deck must close the hull at or above the waterline")
        wall_sided = True
    elif above:
        deck_z = min(above)
        wall_sided = False
    else:
        # same declared approximation as the task 3.4 GZ module:
        # sections run wall-sided above the top tabulated waterline
        deck_z = 1.15 * draft
        wall_sided = True
    rows = wet_rows + [deck_z]
    xs = [float(x) for x in table.stations]
    y = table.half_breadths
    j_deck = waterlines.index(deck_z) if not wall_sided \
        else waterlines.index(wet_rows[-1])
    j_of = {**{z: waterlines.index(z) for z in wet_rows}, deck_z: j_deck}

    # capytaine convention: the free surface is z = 0 and the body
    # lies BELOW it, so table heights above keel are shifted by -draft
    def zc(z: float) -> float:
        return z - draft

    verts: list[tuple[float, float, float]] = []
    vindex: dict[tuple[float, float, float], int] = {}

    def vid(x: float, yy: float, z: float) -> int:
        key = (round(x, 6), round(yy, 6), round(z, 6))
        if key not in vindex:
            vindex[key] = len(verts)
            verts.append(key)
        return vindex[key]

    faces: list[tuple[int, int, int, int]] = []
    # Winding is chosen so every face normal points OUTWARD of the
    # +y half hull (right-hand rule on the quad vertices); the mirror
    # then fixes the -y side automatically.
    for i in range(len(xs) - 1):
        for j in range(len(rows) - 1):
            z0, z1 = rows[j], rows[j + 1]
            a = (xs[i], float(y[i, j_of[z0]]), zc(z0))
            b = (xs[i + 1], float(y[i + 1, j_of[z0]]), zc(z0))
            c = (xs[i + 1], float(y[i + 1, j_of[z1]]), zc(z1))
            d = (xs[i], float(y[i, j_of[z1]]), zc(z1))
            faces.append((vid(*d), vid(*c), vid(*b), vid(*a)))
        # deck strip: deck-row breadths closed to the centreline
        if float(y[i, j_deck]) > 0.0 or float(y[i + 1, j_deck]) > 0.0:
            faces.append((vid(*a),
                          vid(xs[i], 0.0, zc(deck_z)),
                          vid(xs[i + 1], 0.0, zc(deck_z)),
                          vid(*b)))
        # bottom strip: the lowest table row is the baseline-tangent
        # row whose breadths are the FLAT-KEEL width, not zero — close
        # it to the centreline (the mirror completes the plate)
        j_keel = j_of[rows[0]]
        zk = zc(rows[0])
        if float(y[i, j_keel]) > 0.0 or float(y[i + 1, j_keel]) > 0.0:
            faces.append((vid(xs[i], float(y[i, j_keel]), zk),
                          vid(xs[i + 1], float(y[i + 1, j_keel]), zk),
                          vid(xs[i + 1], 0.0, zk),
                          vid(xs[i], 0.0, zk)))
    # transom/stem caps at the perpendiculars: one cap band per pair
    # of rows where the end station carries breadth
    for i_end in (0, len(xs) - 1):
        for j in range(len(rows) - 1):
            z0, z1 = rows[j], rows[j + 1]
            b0 = float(y[i_end, j_of[z0]])
            b1 = float(y[i_end, j_of[z1]])
            if b0 > 1e-9 or b1 > 1e-9:
                cap = (vid(xs[i_end], b0, zc(z0)),
                       vid(xs[i_end], 0.0, zc(z0)),
                       vid(xs[i_end], 0.0, zc(z1)),
                       vid(xs[i_end], b1, zc(z1)))
                faces.append(cap if i_end == 0
                             else (cap[3], cap[2], cap[1], cap[0]))

    vertices = np.asarray(verts, dtype=float)
    half = cpt.Mesh(
        vertices=vertices,
        faces=[list(f) for f in faces],
        name="half_hull",
    )
    if half.volume < 0.0:  # enforce outward normals
        half = cpt.Mesh(
            vertices=vertices,
            faces=[list((f[0], f[3], f[2], f[1])) for f in faces],
            name="half_hull",
        )
    full = cpt.ReflectionSymmetricMesh(half, plane="xOz",
                                       name="hull_full").merged()
    rotation_center = ((xs[0] + xs[-1]) / 2.0, 0.0, 0.0)
    body = cpt.FloatingBody(
        mesh=full,
        dofs=cpt.rigid_body_dofs(
            only=("Heave", "Roll", "Pitch"),
            rotation_center=rotation_center),
        name="openhull_ship",
    )
    info = {
        "n_faces": int(full.nb_faces),
        "mesh_volume_m3": float(full.volume),
        "deck_z_m": deck_z,
        "deck_wall_sided": wall_sided,
        "rotation_center_m": list(rotation_center),
    }
    return body, info


@dataclass(frozen=True)
class RaoPoint:
    """RAO of one motion at one wave period (head or beam seas)."""

    motion: str
    seas: str
    period_s: float
    rao_abs: float
    rao_phase_deg: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RaoResult:
    """Rigid-body RAO sweep over wave periods."""

    periods_s: tuple[float, ...]
    points: tuple[RaoPoint, ...]
    mesh_info: dict[str, Any]
    notes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "periods_s": list(self.periods_s),
            "points": [p.to_dict() for p in self.points],
            "mesh_info": self.mesh_info,
            "notes": list(self.notes),
        }


def compute_rigid_rao(
    table,
    draft: float,
    displacement_t: float,
    kg_m: float,
    km_m: float,
    bml_m: float,
    waterplane_area_m2: float,
    periods_s,
    density: float = 1.025,
    roll_mu: float = DEFAULT_ROLL_MU,
) -> RaoResult:
    """Zero-speed heave/roll/pitch RAOs of the task-2.6 hull.

    displacement_t enters as MASS (tonnes, consistent with rho in
    t/m^3); kg_m and km_m give the roll stiffness GM_T = km - kg;
    bml_m approximates the pitch stiffness GM_L (task 1.4 declares
    BML as the longitudinal metacentric radius); waterplane_area_m2
    gives the heave stiffness rho*g*Aw.  roll_mu (book range
    0.055-0.07 with bilge keels, p.394) calibrates an equivalent
    linear viscous damping injected on the roll DOF:
    B_extra = 2*mu*I_roll*omega_phi at the stage-1 roll period
    lengthened by sqrt(1.25) (the Duell added-inertia share).
    capytaine's radiation damping adds on top, so the total roll
    damping is AT LEAST the book value — declared conservative.
    """
    import numpy as np

    cpt = require_capytaine()
    body, info = build_hull_body(table, draft)
    disp_mass = float(displacement_t) * 1.0  # t; rho in t/m^3 keeps units
    beam = float(table.beam)
    lpp = float(table.lpp)
    # whitelisted inertia forms (AGENTS.md section 5, seakeeping block)
    kxx2 = (beam**2 + 4.0 * kg_m**2) / 12.0            # Eq.(3-39) radius^2
    kyy2 = (0.25 * lpp) ** 2                            # p.428 default
    gm_t = km_m - kg_m
    _require(gm_t > 0.0, "kg_m", kg_m, "KM > KG",
             "roll stiffness needs positive GM_T")
    inertia_roll = disp_mass * kxx2
    mass = np.diag([disp_mass, inertia_roll, disp_mass * kyy2])
    stiff = np.diag([
        density * GRAVITY_M_S2 * waterplane_area_m2,
        disp_mass * GRAVITY_M_S2 * gm_t,
        disp_mass * GRAVITY_M_S2 * float(bml_m),
    ])
    # book-calibrated equivalent viscous damping on the roll DOF
    omega_phi = 2.0 * math.pi / (
        roll_period_regulation(beam, kg_m, gm_t) * math.sqrt(1.25))
    b_extra_roll = 2.0 * roll_mu * inertia_roll * omega_phi
    dissipation = np.diag([0.0, b_extra_roll, 0.0])
    dof_names = [str(d) for d in body.dofs]
    order = [dof_names.index("Heave"), dof_names.index("Roll"),
             dof_names.index("Pitch")]
    solver = cpt.BEMSolver()
    periods = sorted(float(p) for p in periods_s)
    problems = []
    for period in periods:
        _require(math.isfinite(period) and period > 0.0,
                 "periods_s", period, "finite T > 0",
                 "wave periods must be positive")
        omega = 2.0 * math.pi / period
        for dof in body.dofs:
            problems.append(cpt.RadiationProblem(
                body=body, omega=omega, radiating_dof=dof,
                rho=density))
        # beta = 0 head (Nemoh convention) for pitch/heave; pi/2 beam
        problems.append(cpt.DiffractionProblem(
            body=body, omega=omega, wave_direction=0.0, rho=density))
        problems.append(cpt.DiffractionProblem(
            body=body, omega=omega, wave_direction=math.pi / 2,
            rho=density))
    dataset = cpt.assemble_dataset(
        solver.solve_all(problems, progress_bar=False))

    points: list[RaoPoint] = []
    notes = (
        "hydrodynamics: capytaine (linear potential flow, zero speed); "
        "mass/inertia/stiffness: whitelisted chain; roll viscous "
        "damping: equivalent linear B = 2*mu*I*omega_phi calibrated "
        "to the book mu range (p.394) at the stage-1 roll period — "
        "radiation damping adds on top (conservative); surge/sway/yaw "
        "suppressed; dry strip up to the deck carries Airy-decayed "
        "pressure; roll/pitch coupling neglected",
    )
    for seas, beta in (("head", 0.0), ("beam", math.pi / 2)):
        sub = dataset.sel(wave_direction=beta)
        sub["inertia_matrix"] = (("influenced_dof", "radiating_dof"), mass)
        sub["hydrostatic_stiffness"] = (
            ("influenced_dof", "radiating_dof"), stiff)
        import xarray as xr

        diss = xr.DataArray(
            dissipation,
            dims=("influenced_dof", "radiating_dof"),
            coords={
                "influenced_dof": [str(d) for d in
                                   sub.influenced_dof.values],
                "radiating_dof": [str(d) for d in
                                  sub.radiating_dof.values],
            })
        rao = cpt.post_pro.rao(sub, dissipation=diss)
        rao = rao.assign_coords(
            radiating_dof=[str(d) for d in rao.radiating_dof.values])
        for period in periods:
            omega = 2.0 * math.pi / period
            for motion in ("Heave", "Roll", "Pitch"):
                value = complex(np.asarray(
                    rao.sel(omega=omega, radiating_dof=motion)))
                points.append(RaoPoint(
                    motion=motion.lower(), seas=seas, period_s=period,
                    rao_abs=abs(value),
                    rao_phase_deg=math.degrees(
                        math.atan2(value.imag, value.real)),
                ))
    return RaoResult(
        periods_s=tuple(periods),
        points=tuple(points),
        mesh_info=info,
        notes=notes,
    )
