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
