import pytest

from src.data_engineering import units


def test_kcat_identity_and_per_minute():
    assert units.kcat_to_per_s(10, "1/s") == 10
    assert units.kcat_to_per_s(60, "1/min") == pytest.approx(1.0)


def test_kcat_specific_activity_requires_mw():
    # 48.7 umol/min/mg with MW 46 kDa -> 48.7 * 46 / 60
    assert units.kcat_to_per_s(48.7, "umol/min/mg", mw_kda=46) == pytest.approx(48.7 * 46 / 60)
    with pytest.raises(ValueError):
        units.kcat_to_per_s(48.7, "umol/min/mg")  # missing MW


def test_kcat_unknown_unit_raises():
    with pytest.raises(ValueError):
        units.kcat_to_per_s(1.0, "furlongs/fortnight")


def test_km_units():
    assert units.km_to_mM(5, "mM") == 5
    assert units.km_to_mM(1000, "uM") == pytest.approx(1.0)
    # g/L on cellobiose (MW 342.30): 0.342 g/L -> ~1 mM
    assert units.km_to_mM(0.3423, "g/L", substrate="cellobiose") == pytest.approx(1.0, rel=1e-2)


def test_km_polymeric_returns_none():
    assert units.km_to_mM(5.1, "mg/mL", substrate="CMC") is None
    assert units.km_to_mM(3.5, "g/L", substrate="Avicel") is None


def test_km_unknown_unit_raises():
    with pytest.raises(ValueError):
        units.km_to_mM(1.0, "smoots")
