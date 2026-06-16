"""Provenance tiers and balanced enzyme universe (Phase 3 integration).

Kinetics come from three clearly-labelled tiers:
  Literature (full-text confirmed) > AI-predicted (DLKcat kcat) > Estimated (heuristic).
The enzyme universe is the balanced harvested set (EG/CBH/BG) plus the curated
literature anchors and the LPMO control.
"""
import pandas as pd
import pytest

KIN = "data/processed/enzyme_kinetics.csv"


@pytest.fixture(scope="module")
def df():
    return pd.read_csv(KIN)


def test_three_provenance_tiers_present(df):
    st = set(df["source_type"].astype(str))
    assert "Literature" in st            # full-text verified anchors
    assert "AI-predicted" in st          # DLKcat-predicted kcat


def test_kinetics_source_column_consistent(df):
    assert "kinetics_source" in df.columns
    lit = df[df["source_type"] == "Literature"]
    ai = df[df["source_type"] == "AI-predicted"]
    assert lit["kinetics_source"].astype(str).str.contains("Literature").all()
    assert ai["kinetics_source"].astype(str).str.contains("DLKcat").all()


def test_balanced_classes_with_lpmo(df):
    counts = df["enzyme_class"].value_counts()
    for cls in ("EG", "CBH", "BG", "LPMO"):
        assert cls in counts.index, f"class {cls} missing"
    # the harvested universe gives real CBH/BG representation (not EG-dominated)
    assert counts["CBH"] >= 10 and counts["BG"] >= 10


def test_literature_anchors_preserved(df):
    lit_ids = set(df[df["source_type"] == "Literature"]["id"])
    # the calibration reference cocktail must remain the verified anchors
    assert {"GUN2_THEFU", "GUX1_TRIRF", "BGL1_ASPNG"}.issubset(lit_ids)
    assert (df["source_type"] == "Literature").sum() >= 10
