"""Real-biomass model: lignin inhibition + geometric accessibility (integration).

These factors multiply the cellulose-attack rate. They default to a neutral 1.0
so calibration/training (which pass no biomass) are unaffected; the app passes
real biomass/pretreatment properties.
"""
import pandas as pd
import pytest

from src import config
from src.validation.validator import (EnzymeValidator, enzyme_mM,
                                       cellulose_gpl_to_glucose_equiv_mM)

KINETICS = "data/processed/enzyme_kinetics.csv"


@pytest.fixture(scope="module")
def v():
    return EnzymeValidator()


def test_neutral_biomass_factor_is_one(v):
    # No biomass properties -> neutral multiplier (keeps calibration/training intact).
    assert v.biomass_factor() == 1.0


def test_inhibition_bounds_and_monotonic_in_lignin(v):
    f_lo = v.calculate_inhibition_factor(0.10, "grass")
    f_hi = v.calculate_inhibition_factor(0.25, "grass")
    assert 0.01 <= f_hi <= f_lo <= 0.99
    assert f_hi < f_lo  # more lignin -> stronger inhibition (lower factor)


def test_softwood_more_inhibitory_than_grass(v):
    assert (v.calculate_inhibition_factor(0.20, "softwood")
            < v.calculate_inhibition_factor(0.20, "grass"))


def test_phenol_furfural_reduce_factor(v):
    base = v.calculate_inhibition_factor(0.15, "grass")
    inhibited = v.calculate_inhibition_factor(0.15, "grass", phenol_conc=8.0, furfural_conc=2.0)
    assert inhibited < base


def test_accessibility_bounds_and_trends(v):
    assert 0.01 <= v.calculate_accessibility(1.0, 0.7, 0.0) <= 0.99
    assert v.calculate_accessibility(0.2, 0.7, 0.0) > v.calculate_accessibility(3.0, 0.7, 0.0)
    # harsher pretreatment (severity) breaks crystallinity -> more accessible
    assert v.calculate_accessibility(1.0, 0.7, 1.0) > v.calculate_accessibility(1.0, 0.7, 0.0)


def test_biomass_factor_lowers_cascade_conversion(v):
    df = pd.read_csv(KINETICS)

    def params(cls):
        sub = df[(df.enzyme_class == cls) & (df.source_type == "Literature")]
        r = sub.iloc[0]
        return {"kcat": float(r.kcat), "Km": float(r.Km), "Ki": float(r.Ki),
                "t_opt": float(r.t_opt), "ph_opt": float(r.ph_opt)}

    eg, cbh, bg = params("EG"), params("CBH"), params("BG")
    cel_g_L = config.CALIB_SUBSTRATE_G_PER_L
    Cel0 = cellulose_gpl_to_glucose_equiv_mM(cel_g_L)
    fr = config.DEFAULT_COCKTAIL_FRACTIONS
    L = config.ENZYME_LOADING_MG_PER_G_GLUCAN
    kw = dict(substrate_conc_init=Cel0,
              conc_EG=enzyme_mM(L * fr["EG"], cel_g_L, config.ENZYME_MW_DA["EG"]),
              conc_CBH=enzyme_mM(L * fr["CBH"], cel_g_L, config.ENZYME_MW_DA["CBH"]),
              conc_BG=enzyme_mM(L * fr["BG"], cel_g_L, config.ENZYME_MW_DA["BG"]),
              steps=300)
    _, _, _, g_full = v.run_cellulolytic_simulation(eg, cbh, bg, bio_factor=1.0, **kw)
    _, _, _, g_inh = v.run_cellulolytic_simulation(eg, cbh, bg, bio_factor=0.3, **kw)
    assert float(g_inh[-1]) < float(g_full[-1])  # inhibition lowers final glucose
