"""Simulation-vs-literature error standard (§2.5c)."""
import json
import os

import pytest

from src import config

CAL = os.path.join("data", "curated", "calibration.json")


def test_calibration_file_exists():
    assert os.path.exists(CAL), "Run `python -m src.data_engineering.calibrate_model` first."


def test_relative_error_within_tolerance():
    data = json.load(open(CAL, encoding="utf-8"))
    re = float(data["relative_error"])
    assert re <= config.CALIB_TOLERANCE_REL, \
        f"calibration RE {re:.3f} exceeds tolerance {config.CALIB_TOLERANCE_REL}"


def test_achieved_conversion_in_literature_band():
    data = json.load(open(CAL, encoding="utf-8"))
    x = float(data["achieved_conversion"])
    lo, hi = config.LIT_RATE_BAND
    assert lo <= x <= hi, f"achieved conversion {x} outside literature band {config.LIT_RATE_BAND}"


def test_alpha_is_used_by_default():
    assert config.get_accessibility_alpha() > 0
