"""Biological-plausibility bands for literature kinetic values (§2.5b)."""
import pandas as pd
import pytest

from src import config

KINETICS = "data/processed/enzyme_kinetics.csv"


@pytest.fixture(scope="module")
def lit():
    df = pd.read_csv(KINETICS)
    return df[df["source_type"] == "Literature"]


def test_literature_kcat_km_in_class_bands(lit):
    bands = config.PLAUSIBILITY_BANDS
    for _, r in lit.iterrows():
        cls = r["enzyme_class"]
        if cls not in bands:
            continue
        klo, khi = bands[cls]["kcat"]
        mlo, mhi = bands[cls]["Km"]
        assert klo <= float(r["kcat"]) <= khi, \
            f"{r['id']} ({cls}) kcat {r['kcat']} outside {bands[cls]['kcat']}"
        assert mlo <= float(r["Km"]) <= mhi, \
            f"{r['id']} ({cls}) Km {r['Km']} outside {bands[cls]['Km']}"


def test_bg_much_faster_than_cbh(lit):
    """Sanity: soluble-cellobiose BG turnover >> crystalline-cellulose CBH turnover."""
    bg = lit[lit["enzyme_class"] == "BG"]["kcat"].max()
    cbh = lit[lit["enzyme_class"] == "CBH"]["kcat"].max()
    assert bg > 100 * cbh


# --------------------------------------------------------------------------
# Substrate-property layer (real-biomass) plausibility.
# --------------------------------------------------------------------------
def test_inhibition_constants_in_bands():
    bands = config.SUBSTRATE_PROPERTY_BANDS
    ic = config.INHIBITION_CONSTANTS
    assert bands["ki_phenol_mM"][0] <= ic["ki_phenol"] <= bands["ki_phenol_mM"][1]
    assert bands["ki_furfural_mM"][0] <= ic["ki_furfural"] <= bands["ki_furfural_mM"][1]
    assert bands["ki_hmf_mM"][0] <= ic["ki_hmf"] <= bands["ki_hmf_mM"][1]


def test_furans_weaker_inhibitors_than_phenol():
    """Correctness guard: phenolics are POTENT (small Ki), furans WEAK (large Ki).
    The pre-correction values had furfural (2 mM) 'stronger' than phenol (8 mM),
    contradicting the literature (Kim et al. 2011)."""
    ic = config.INHIBITION_CONSTANTS
    assert ic["ki_furfural"] > ic["ki_phenol"]
    assert ic["ki_hmf"] > ic["ki_phenol"]


def test_geometric_and_adsorption_params_in_bands():
    bands = config.SUBSTRATE_PROPERTY_BANDS
    p = config.get_biomass_params()
    assert bands["k_ads"][0] <= p["k_ads"] <= bands["k_ads"][1]
    assert bands["d_ref_mm"][0] <= p["d_ref"] <= bands["d_ref_mm"][1]
    assert bands["accessibility_exponent"][0] <= p["exponent"] <= bands["accessibility_exponent"][1]


def test_biomass_composition_in_bands():
    from src.resources.materials import BIOMASS_DATA
    bands = config.SUBSTRATE_PROPERTY_BANDS
    for name, m in BIOMASS_DATA.items():
        lf = m["lignin_fraction"]
        assert bands["lignin_fraction"][0] <= lf <= bands["lignin_fraction"][1], \
            f"{name} lignin_fraction {lf} outside {bands['lignin_fraction']}"
        cr = m["crystallinity"]
        assert bands["crystallinity"][0] <= cr <= bands["crystallinity"][1], \
            f"{name} crystallinity {cr} outside {bands['crystallinity']}"
