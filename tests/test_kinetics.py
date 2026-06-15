"""Physical correctness of the cellulolytic kinetic model (§2 / §6)."""
import numpy as np
import pandas as pd
import pytest

from src import config
from src.validation.validator import (EnzymeValidator, enzyme_mM,
                                       cellulose_gpl_to_glucose_equiv_mM)

KINETICS = "data/processed/enzyme_kinetics.csv"


def _params(r):
    return {"kcat": float(r["kcat"]), "Km": float(r["Km"]), "Ki": float(r["Ki"]),
            "t_opt": float(r["t_opt"]), "ph_opt": float(r["ph_opt"])}


@pytest.fixture(scope="module")
def sim():
    df = pd.read_csv(KINETICS)
    eg = df[(df.enzyme_class == "EG") & (df.source_type == "Literature")].iloc[0]
    cbh = df[df.enzyme_class == "CBH"].iloc[0]
    bg = df[df.enzyme_class == "BG"].iloc[0]
    cel_g_L = config.CALIB_SUBSTRATE_G_PER_L
    Cel0 = cellulose_gpl_to_glucose_equiv_mM(cel_g_L)
    fr = config.DEFAULT_COCKTAIL_FRACTIONS
    L = config.ENZYME_LOADING_MG_PER_G_GLUCAN
    v = EnzymeValidator()
    t, Cel, C2, G = v.run_cellulolytic_simulation(
        _params(eg), _params(cbh), _params(bg), Cel0,
        enzyme_mM(L * fr["EG"], cel_g_L, config.ENZYME_MW_DA["EG"]),
        enzyme_mM(L * fr["CBH"], cel_g_L, config.ENZYME_MW_DA["CBH"]),
        enzyme_mM(L * fr["BG"], cel_g_L, config.ENZYME_MW_DA["BG"]),
        duration=config.DEFAULT_DURATION_H * 3600.0, steps=300)
    return dict(t=t, Cel=Cel, C2=C2, G=G, Cel0=Cel0)


def test_no_nan_or_inf(sim):
    for k in ("Cel", "C2", "G"):
        assert np.all(np.isfinite(sim[k]))


def test_conversion_not_exceeding_100pct(sim):
    assert np.max(sim["G"] / sim["Cel0"]) <= 1.0001


def test_glucose_equivalent_mass_conserved(sim):
    total = sim["Cel"] + 2 * sim["C2"] + sim["G"]
    assert np.allclose(total, sim["Cel0"], rtol=1e-3)


def test_monotonic_progress(sim):
    assert np.all(np.diff(sim["G"]) >= -1e-6)      # glucose non-decreasing
    assert np.all(np.diff(sim["Cel"]) <= 1e-6)     # cellulose non-increasing


def test_accessibility_rate_retardation(sim):
    """Hydrolysis rate must fall as conversion rises (recalcitrance signature)."""
    G = sim["G"]
    n = len(G)
    early = G[max(1, n // 20)] - G[0]
    late = G[-1] - G[-1 - max(1, n // 20)]
    assert late < early


def test_effective_kcat_peaks_at_optimum():
    v = EnzymeValidator()
    peak = v.calculate_effective_kcat(10.0, 50.0, 5.0, t_opt=50.0, ph_opt=5.0)
    off = v.calculate_effective_kcat(10.0, 30.0, 8.0, t_opt=50.0, ph_opt=5.0)
    assert peak == pytest.approx(10.0)
    assert off < peak
