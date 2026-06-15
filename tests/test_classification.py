"""Enzyme-class assignment & screening partition (fixes the EG/BG split bug)."""
import pandas as pd
import pytest

from src.data_engineering.populate_kinetics import classify_enzyme
from src.ai_model.screening import SmartSampler

KINETICS = "data/processed/enzyme_kinetics.csv"


def test_classify_by_annotation_and_ec():
    assert classify_enzyme("Beta-glucosidase", "3.2.1.21") == "BG"
    assert classify_enzyme("Cellobiohydrolase A", "3.2.1.91") == "CBH"
    assert classify_enzyme("Endoglucanase EG-1", "3.2.1.4") == "EG"
    assert classify_enzyme("AA9 lytic polysaccharide monooxygenase", "1.14.99.56", "LP9F_EMENI") == "LPMO"


def test_dataset_has_each_required_class():
    df = pd.read_csv(KINETICS)
    classes = set(df["enzyme_class"])
    assert {"EG", "CBH", "BG"}.issubset(classes)
    # the LPMO must be present and labelled (excluded from hydrolase pools)
    assert (df["enzyme_class"] == "LPMO").any()


def test_smartsampler_partitions_by_real_class_not_substring():
    df = pd.read_csv(KINETICS)
    s = SmartSampler(df)
    assert not s.eg_list.empty and not s.bg_list.empty
    # BG pool contains only real beta-glucosidases (not the bottom half of EGs)
    assert (s.bg_list["enzyme_class"] == "BG").all()
    # EG pool must not leak BG enzymes
    assert "BGL1_ASPNG" not in set(s.eg_list["id"])
    assert "BGL1_ASPNG" in set(s.bg_list["id"])


def test_smartsampler_fails_loud_without_bg():
    df = pd.read_csv(KINETICS)
    df_no_bg = df[df["enzyme_class"] != "BG"]
    with pytest.raises(ValueError):
        SmartSampler(df_no_bg)
