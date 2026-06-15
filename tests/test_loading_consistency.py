"""Enzyme-loading is unified across app/training (fixes the 3-regime bug)."""
import pytest

from src import config
from src.validation.validator import enzyme_mM


def test_enzyme_mM_formula():
    # 15 mg/g * 50 g/L = 750 mg/L = 0.75 g/L; /50000 g/mol = 1.5e-5 M = 0.015 mM
    assert enzyme_mM(15, 50, 50000) == pytest.approx(0.015)


def test_same_loading_same_concentration():
    """Tab1, Tab3 and training all call enzyme_mM with the SAME loading -> same mM."""
    cel_g_L = config.CALIB_SUBSTRATE_G_PER_L
    mw = config.ENZYME_MW_DA["EG"]
    a = enzyme_mM(config.ENZYME_LOADING_MG_PER_G_GLUCAN, cel_g_L, mw)
    b = enzyme_mM(config.ENZYME_LOADING_MG_PER_G_GLUCAN, cel_g_L, mw)
    assert a == b


def test_loading_monotonic():
    assert enzyme_mM(30, 50, 50000) > enzyme_mM(15, 50, 50000)
