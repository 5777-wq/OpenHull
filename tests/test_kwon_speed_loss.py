"""Kwon speed-loss method tests (whitelisted 2026-09-23).

Transcription source, archived and page-verified: Cheng, C.-W. et
al., J. Marine Science and Engineering 2025, 13(1), 42 (MDPI, open
access CC-BY), section 2.2 — quoting Kwon, Y.J. (2008), The Naval
Architect, RINA.  Primary literature archived: Kwon, Y.J. (1981),
"On Ship Speed Performance", PhD thesis, Newcastle University
(349 pp.).  Internal archive note with the verbatim tables:
internal 知识库/Kwon_speed_loss/SOURCE_NOTES.md.

Acceptance anchors:
- the printed table 2 doubling convention (paper usage: head-sea
  C_mu = 1.0);
- the archived paper's own KCS comparison (its table 15: Kwon
  f_w = 0.932 at Sea State 5) reproduced within 0.01 — the exact
  inputs are not restated in the paper, so the tolerance carries
  the declared input ambiguity;
- the declared refusal of a non-positive dR (low Fr x high Cb).
"""

import pytest

from openhull.seakeeping import (
    kwon_cf,
    kwon_cm,
    kwon_delta_r,
    kwon_speed_loss_percent,
)
from openhull.spec import SpecValidationError


def test_head_sea_direction_coefficient_is_one():
    # the paper's doubling convention: printed 2*C_mu = 2 -> C_mu = 1
    assert kwon_cm("head", 6.0) == pytest.approx(1.0)
    assert kwon_cm("head", 11.0) == pytest.approx(1.0)


def test_direction_coefficient_quadratic_forms():
    # printed 2*C_mu forms, halved
    assert kwon_cm("bow", 4.0) == pytest.approx(0.85)
    assert kwon_cm("beam", 6.0) == pytest.approx(0.45)
    assert kwon_cm("following", 8.0) == pytest.approx(0.2)
    # directions order the severity at the same sea state
    bn = 6.0
    assert (kwon_cm("head", bn) >= kwon_cm("bow", bn)
            >= kwon_cm("beam", bn) >= kwon_cm("following", bn))


def test_delta_r_table_rows():
    # printed quadratic rows (table 3)
    assert kwon_delta_r(0.65, 0.26, "normal") == pytest.approx(
        2.6 - 3.7 * 0.26 - 11.6 * 0.26 ** 2)
    assert kwon_delta_r(0.55, 0.10, "normal") == pytest.approx(
        1.7 - 1.4 * 0.10 - 7.4 * 0.10 ** 2)
    assert kwon_delta_r(0.80, 0.10, "ballast") == pytest.approx(
        3.0 - 16.3 * 0.10 - 21.6 * 0.10 ** 2)


def test_delta_r_nearest_cb_declared():
    # cb between printed rows takes the nearest printed Cb (0.70)
    assert kwon_delta_r(0.68, 0.20, "normal") == kwon_delta_r(
        0.70, 0.20, "normal")


def test_non_positive_correction_refused():
    # Cb 0.85 loaded at Fr 0.14: dR = 3.1 - 18.7*0.14 - 28*0.14^2 < 0
    with pytest.raises(SpecValidationError):
        kwon_delta_r(0.85, 0.14, "loaded")
    with pytest.raises(SpecValidationError):
        kwon_speed_loss_percent(0.85, 0.14, 6.0, 178370.0)


def test_domain_guards():
    with pytest.raises(SpecValidationError):
        kwon_delta_r(0.50, 0.20)  # below the printed Cb domain
    with pytest.raises(SpecValidationError):
        kwon_delta_r(0.65, 0.40)  # above the printed Fr domain
    with pytest.raises(SpecValidationError):
        kwon_cm("head", 15.0)
    with pytest.raises(SpecValidationError):
        kwon_cf(6.0, 52030.0, ship_type="container", loading="ballast")


def test_cf_table_4_rows():
    # printed forms: 0.5/0.7 linear, 2.7/22.0 denominators
    cf = kwon_cf(6.0, 52030.0, ship_type="container", loading="normal")
    assert cf == pytest.approx(0.7 * 6.0 + 6.0 ** 6.5 / (22.0 * 52030.0 ** (
        2.0 / 3.0)))
    cf_general = kwon_cf(6.0, 52030.0, loading="loaded")
    assert cf_general == pytest.approx(0.5 * 6.0 + 6.0 ** 6.5 / (2.7 *
                                 52030.0 ** (2.0 / 3.0)))


def test_kcs_cross_check_against_archived_paper():
    # the archived paper's table 15: Kwon f_w = 0.932 for the KCS at
    # Sea State 5 (calm 24.00 kn).  KCS: Cb 0.60 normal, container,
    # nabla 52,030 m3, Fr ~ 0.26.  The paper does not restate its
    # exact Kwon inputs, so the tolerance carries that ambiguity.
    pct, ratio = kwon_speed_loss_percent(
        0.60, 0.26, 6.0, 52030.0, ship_type="container",
        loading="normal")
    assert ratio == pytest.approx(0.932, abs=0.01)


def test_speed_loss_monotone_in_beaufort():
    losses = [kwon_speed_loss_percent(0.70, 0.25, bn, 60000.0,
                                      loading="normal")[0]
              for bn in (4.0, 5.0, 6.0)]
    assert losses == sorted(losses)
