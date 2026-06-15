"""Screening produces well-formed cocktails."""
import pandas as pd

from src.ai_model.screening import SmartSampler

KINETICS = "data/processed/enzyme_kinetics.csv"


def test_sample_plate_shape_and_scores():
    df = pd.read_csv(KINETICS)
    samples = SmartSampler(df).sample_plate(size=8)
    assert len(samples) == 8
    for s in samples:
        for key in ("eg_id", "cbh_id", "bg_id", "Predicted_Score",
                    "ratio_eg", "ratio_cbh", "ratio_bg"):
            assert key in s
        assert 0.0 <= s["Predicted_Score"] <= 1.0
        assert abs((s["ratio_eg"] + s["ratio_cbh"] + s["ratio_bg"]) - 1.0) < 0.02
