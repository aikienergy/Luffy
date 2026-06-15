"""
Purpose: Biochemically meaningful screening of cellulase cocktails.

Overview:
    Builds enzyme cocktails for the cellulolytic cascade using the REAL
    functional class of each enzyme (column `enzyme_class`: EG / CBH / BG),
    not a substring match on the id. This fixes the previous bug where the
    EG/BG pools were both empty and silently fell back to head/tail halves of
    the same endoglucanase list (every pair was EG x EG).

    A cocktail is an (EG, CBH, BG) triple scored by combined catalytic
    efficiency, with a defensible protein-mass split between the three classes.
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src import config


class SmartSampler:
    def __init__(self, df_kinetics):
        self.df = df_kinetics.copy()
        if "enzyme_class" not in self.df.columns:
            raise ValueError(
                "df_kinetics is missing 'enzyme_class'. Re-run populate_kinetics.py "
                "to regenerate enzyme_kinetics.csv with functional classes.")
        self.eg_list = self.df[self.df["enzyme_class"] == "EG"]
        self.cbh_list = self.df[self.df["enzyme_class"] == "CBH"]
        self.bg_list = self.df[self.df["enzyme_class"] == "BG"]

        # Fail loud rather than silently inventing a cascade from a single class.
        if self.eg_list.empty:
            raise ValueError("No endoglucanase (EG) enzymes available for screening.")
        if self.bg_list.empty:
            raise ValueError(
                "No beta-glucosidase (BG) enzymes available; the cellulose->glucose "
                "cascade requires a BG. Add one to data/curated/literature_kinetics.csv.")
        if self.cbh_list.empty:
            # CBH is strongly synergistic but not strictly required; warn and
            # fall back to the highest-kcat EG acting in the exo role.
            print("WARNING: no cellobiohydrolase (CBH) in dataset; using top EG as CBH proxy.")
            self.cbh_list = self.eg_list.nlargest(1, "kcat")

    def _eff(self, row):
        return float(row["kcat"]) / max(float(row["Km"]), 1e-6)

    def _predict_score(self, eg, cbh, bg):
        """Combined catalytic-efficiency score in [0,1] for an (EG,CBH,BG) cocktail."""
        try:
            eg_eff = self._eff(eg)
            cbh_eff = self._eff(cbh)
            bg_eff = self._eff(bg)
            bg_ki = np.log1p(float(bg.get("Ki", config.KI_GLUCOSE_MM)))
            # Cellulose attack (EG+CBH) is rate-limiting -> weighted highest.
            combined = (np.log10(eg_eff + 0.1) * 0.35
                        + np.log10(cbh_eff + 0.1) * 0.35
                        + np.log10(bg_eff + 0.1) * 0.20
                        + bg_ki * 0.10)
            return float(np.clip((combined + 2.0) / 6.0, 0.01, 0.99))
        except Exception:
            return 0.5

    def _optimize_ratio(self, eg, cbh, bg):
        """
        Protein-mass fractions (EG, CBH, BG). Starts from the defensible default
        cocktail and nudges toward whichever cellulose-attacking class is slower
        (rate-limiting needs more enzyme). Always normalised to sum 1.
        """
        base = config.DEFAULT_COCKTAIL_FRACTIONS
        f_eg, f_cbh, f_bg = base["EG"], base["CBH"], base["BG"]
        try:
            # Shift mass between EG and CBH toward the slower of the two.
            kcat_eg = max(float(eg["kcat"]), 1e-6)
            kcat_cbh = max(float(cbh["kcat"]), 1e-6)
            shift = 1.0 / (1.0 + np.sqrt(kcat_eg / kcat_cbh))  # fraction of EG+CBH to EG
            pool = f_eg + f_cbh
            f_eg = float(np.clip(shift, 0.2, 0.8)) * pool
            f_cbh = pool - f_eg
        except Exception:
            pass
        total = f_eg + f_cbh + f_bg
        return {"EG": round(f_eg / total, 3),
                "CBH": round(f_cbh / total, 3),
                "BG": round(f_bg / total, 3)}

    def sample_plate(self, size=96):
        """Generate up to `size` (EG,CBH,BG) cocktail candidates, ranked by score."""
        samples = []
        top_eg = self.eg_list.nlargest(max(1, int(len(self.eg_list) * 0.25)), "kcat")
        cbh_opts = self.cbh_list
        bg_opts = self.bg_list.nlargest(len(self.bg_list), "Ki")

        seen = set()

        def add(eg, cbh, bg, reason):
            key = (eg["id"], cbh["id"], bg["id"])
            if key in seen:
                return False
            seen.add(key)
            ratio = self._optimize_ratio(eg, cbh, bg)
            samples.append({
                "eg_id": eg["id"], "cbh_id": cbh["id"], "bg_id": bg["id"],
                "reason": reason,
                "Predicted_Score": self._predict_score(eg, cbh, bg),
                "ratio_eg": ratio["EG"], "ratio_cbh": ratio["CBH"], "ratio_bg": ratio["BG"],
            })
            return True

        # 1. High-performance combinations
        for _, eg in top_eg.iterrows():
            for _, cbh in cbh_opts.iterrows():
                for _, bg in bg_opts.iterrows():
                    if len(samples) >= size:
                        break
                    add(eg, cbh, bg, "High Performance Synergy")
        # 2. Diversity fill (sample with replacement across full pools)
        guard = 0
        while len(samples) < size and guard < size * 20:
            guard += 1
            eg = self.eg_list.sample(1).iloc[0]
            cbh = self.cbh_list.sample(1).iloc[0]
            bg = self.bg_list.sample(1).iloc[0]
            add(eg, cbh, bg, "Exploration (Diversity)")

        samples.sort(key=lambda x: x["Predicted_Score"], reverse=True)
        return samples[:size]
