"""Transcription-fidelity & provenance checks (ask #1 / §2.5a)."""
import os

import pandas as pd
import pytest

CURATED = "data/curated/literature_kinetics.csv"
KINETICS = "data/processed/enzyme_kinetics.csv"
PROVENANCE = "data/curated/PROVENANCE.md"


@pytest.fixture(scope="module")
def kin():
    return pd.read_csv(KINETICS)


@pytest.fixture(scope="module")
def curated():
    return pd.read_csv(CURATED)


def test_literature_rows_have_provenance(kin):
    lit = kin[kin["source_type"] == "Literature"]
    assert len(lit) >= 3, "expected at least the seeded literature anchors"
    for _, r in lit.iterrows():
        # a citation handle (DOI or PMID), plus authors/year/substrate
        has_handle = (pd.notna(r.get("doi")) and str(r.get("doi")).strip()) or \
                     (pd.notna(r.get("pmid")) and str(r.get("pmid")).strip())
        assert has_handle, f"{r['id']} has neither DOI nor PMID"
        for col in ("authors", "year", "substrate", "verification_status"):
            assert pd.notna(r.get(col)) and str(r.get(col)).strip(), f"{r['id']} missing {col}"


def test_reported_values_match_curated_within_1pct(kin, curated):
    """Stored reported values must equal the curated source (no mangling)."""
    cur = {str(r["id"]): r for _, r in curated.iterrows()}
    lit = kin[kin["source_type"] == "Literature"]
    for _, r in lit.iterrows():
        cid = str(r["id"])
        assert cid in cur, f"{cid} not found in curated file"
        assert float(r["kcat_reported"]) == pytest.approx(float(cur[cid]["kcat"]), rel=0.01)
        assert float(r["Km_reported"]) == pytest.approx(float(cur[cid]["Km"]), rel=0.01)


def test_provenance_ledger_documents_each_value(kin):
    assert os.path.exists(PROVENANCE)
    text = open(PROVENANCE, encoding="utf-8").read()
    for eid in kin[kin["source_type"] == "Literature"]["id"]:
        assert str(eid) in text, f"{eid} not documented in PROVENANCE.md"
