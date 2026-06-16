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


def test_ki_units_molar_and_micromolar():
    assert units.ki_to_mM(8.0, "mM") == 8.0
    assert units.ki_to_mM(2000, "uM") == pytest.approx(2.0)
    assert units.ki_to_mM(0.005, "M") == pytest.approx(5.0)


def test_ki_mass_concentration_needs_molar_mass():
    # 0.9411 g/L phenol (MW 94.11) -> 10 mM
    assert units.ki_to_mM(0.9411, "g/L", inhibitor="phenol") == pytest.approx(10.0, rel=1e-3)
    # furfural 0.09608 g/L (MW 96.08) -> 1 mM
    assert units.ki_to_mM(0.09608, "g/L", inhibitor="furfural") == pytest.approx(1.0, rel=1e-3)
    # explicit molar mass also works
    assert units.ki_to_mM(0.12611, "mg/mL", mw_g_per_mol=126.11) == pytest.approx(1.0, rel=1e-3)


def test_ki_mass_without_molar_mass_fails_loud():
    with pytest.raises(ValueError):
        units.ki_to_mM(1.0, "g/L", inhibitor="mystery-compound")


def test_ki_unknown_unit_raises():
    with pytest.raises(ValueError):
        units.ki_to_mM(1.0, "smoots")
