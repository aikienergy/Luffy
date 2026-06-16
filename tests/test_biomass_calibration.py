"""Biomass (substrate-property) calibration: predictions must land in the
full-text-verified literature yield bands, and the fitted structural parameters
must stay inside their plausibility bands.

Mirrors test_calibration.py for the accessibility `alpha`, but for the
{k_ads, d_ref, exponent} parameters fit by calibrate_biomass.py.
"""
import json
import os

import pytest

from src import config
from src.resources.materials import PRETREATMENT_PRESETS

CAL = os.path.join("data", "curated", "biomass_calibration.json")


@pytest.fixture(scope="module")
def cal():
    if not os.path.exists(CAL):
        pytest.skip("biomass_calibration.json not present; run calibrate_biomass.py")
    with open(CAL, "r", encoding="utf-8") as fh:
        return json.load(fh)


def test_status_pass_all_targets_in_band(cal):
    assert cal.get("status") == "PASS", f"biomass calibration status: {cal.get('status')}"
    report = cal.get("report", [])
    assert report, "calibration report is empty"
    for r in report:
        assert r["pass"], (f"{r['target']} predicted {r['achieved']} outside band "
                           f"{tuple(r['band'])}")


def test_fitted_params_in_plausibility_bands(cal):
    p = cal["parameters"]
    bands = config.SUBSTRATE_PROPERTY_BANDS
    klo, khi = bands["k_ads"];               assert klo <= p["k_ads"] <= khi
    dlo, dhi = bands["d_ref_mm"];            assert dlo <= p["d_ref"] <= dhi
    elo, ehi = bands["accessibility_exponent"]; assert elo <= p["exponent"] <= ehi


def test_validator_honours_calibrated_params(cal):
    """The validator must read the persisted calibration (not the defaults)."""
    got = config.get_biomass_params()
    for k, v in cal["parameters"].items():
        assert got[k] == pytest.approx(v, rel=1e-6)


def test_predicted_yield_monotonic_in_severity(cal):
    """Higher pretreatment severity -> higher (or equal, at the ceiling)
    predicted conversion, matching the verified yield ordering."""
    by_label = {r["target"]: r for r in cal["report"]}
    order = ["Rice Straw / Simple Crushing", "Rice Straw / Dilute Acid",
             "Rice Straw / Hydrothermal", "Rice Straw / Steam Explosion"]
    achieved = [by_label[o]["achieved"] for o in order if o in by_label]
    assert achieved == sorted(achieved), f"non-monotonic predicted yields: {achieved}"


def test_severities_match_yield_ordering():
    """Guard the preset severities stay ordered with their literature yields."""
    rows = [(p["severity"], p["literature"]["yield"]) for p in PRETREATMENT_PRESETS.values()]
    rows.sort(key=lambda x: x[0])
    mids = [0.5 * (lo + hi) for _, (lo, hi) in rows]
    assert mids == sorted(mids), f"severity order contradicts yield order: {rows}"
