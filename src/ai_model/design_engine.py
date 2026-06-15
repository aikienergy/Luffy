"""
Purpose: AI Design Engine (inference & sequence optimization).

Overview:
    Loads the trained Gaussian-Process yield predictor and proposes point
    mutations to improve predicted yield, using ESM-2 embeddings. The GP's
    predictive standard deviation IS surfaced (it was previously discarded), so
    proposals carry an honest confidence interval. Missing ESM weights raise a
    clear error rather than silently returning a zero embedding that would yield
    meaningless predictions.
"""
import os
import sys

import joblib
import numpy as np
import pandas as pd
import torch
from transformers import EsmTokenizer, EsmModel

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src import config

ESM_MODEL_NAME = "facebook/esm2_t6_8M_UR50D"
EMBED_DIM = 320
AA_LIST = list("ARNDCQEGHILKMFPSTWYV")


class DesignEngine:
    def __init__(self, custom_dataframe=None):
        self.model_path = "models/yield_predictor.pkl"
        self.features_path = "data/processed/enzyme_features.csv"
        self.kinetics_path = "data/processed/enzyme_kinetics.csv"
        self.cols_path = "models/yield_predictor_cols.pkl"

        self.model = None
        self.df_features = None
        self.df_kinetics = None
        self.feature_cols = None
        self.custom_df = custom_dataframe

        self.tokenizer = None
        self.esm_model = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.rng = np.random.default_rng(config.RANDOM_SEED)
        self._embed_cache = {}

        self.load_resources()

    def load_resources(self):
        if os.path.exists(self.model_path):
            try:
                self.model = joblib.load(self.model_path)
            except Exception:
                print("Warning: could not load yield model (retrain required).")
        if os.path.exists(self.features_path):
            self.df_features = pd.read_csv(self.features_path)
        if self.custom_df is not None:
            self.df_kinetics = self.custom_df
        elif os.path.exists(self.kinetics_path):
            self.df_kinetics = pd.read_csv(self.kinetics_path)
        if os.path.exists(self.cols_path):
            self.feature_cols = joblib.load(self.cols_path)

    def _load_esm(self):
        if self.esm_model is None:
            print("Loading ESM-2 model for Design Engine...")
            self.tokenizer = EsmTokenizer.from_pretrained(ESM_MODEL_NAME)
            self.esm_model = EsmModel.from_pretrained(ESM_MODEL_NAME).to(self.device)
            self.esm_model.eval()

    def _get_embedding(self, sequence):
        """Mean-pooled ESM-2 embedding. Fails loud if the model can't load."""
        if sequence in self._embed_cache:
            return self._embed_cache[sequence]
        try:
            self._load_esm()
        except Exception as e:
            raise RuntimeError(
                f"ESM-2 ({ESM_MODEL_NAME}) failed to load: {e}. "
                f"Embeddings are required for design; cannot proceed with a "
                f"placeholder vector.") from e
        with torch.no_grad():
            inputs = self.tokenizer(sequence, return_tensors="pt",
                                    truncation=True, max_length=1024)
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            outputs = self.esm_model(**inputs)
            emb = outputs.last_hidden_state.mean(dim=1).cpu().numpy()[0]
        self._embed_cache[sequence] = emb
        return emb

    def calculate_properties(self, sequence):
        """
        Biophysical properties for the radar chart, normalised to 1-5.
        'Aliphatic Index' is a real sequence-derived proxy for thermostability
        (Ikai-style aliphatic residue content), not a mock 'stability' value.
        """
        if not sequence:
            return {"Hydrophobicity": 3, "Charge": 3, "Aliphatic Index": 3}
        kd = {'I': 4.5, 'V': 4.2, 'L': 3.8, 'F': 2.8, 'C': 2.5, 'M': 1.9, 'A': 1.8,
              'G': -0.4, 'T': -0.7, 'S': -0.8, 'W': -0.9, 'Y': -1.3, 'P': -1.6,
              'H': -3.2, 'E': -3.5, 'Q': -3.5, 'D': -3.5, 'N': -3.5, 'K': -3.9, 'R': -4.5}
        n = len(sequence)
        hydro = sum(kd.get(aa, 0) for aa in sequence) / n
        hydro_score = min(5, max(1, 3 + hydro))
        net_charge = (sequence.count('R') + sequence.count('K')
                      - sequence.count('D') - sequence.count('E'))
        charge_score = min(5, max(1, 3 + net_charge / 5))
        # Aliphatic index (Ala, Val, Ile, Leu) — higher => more thermostable.
        x_ala = sequence.count('A') / n * 100
        x_val = sequence.count('V') / n * 100
        x_ile_leu = (sequence.count('I') + sequence.count('L')) / n * 100
        ai = x_ala + 2.9 * x_val + 3.9 * x_ile_leu  # Ikai aliphatic index
        ai_score = min(5, max(1, ai / 30.0))        # ~0-150 -> 1-5
        return {"Hydrophobicity": round(hydro_score, 1),
                "Charge": round(charge_score, 1),
                "Aliphatic Index": round(ai_score, 1)}

    def recommend_best_enzyme(self, temp, ph, substrate="Cellulose"):
        if self.model is None or self.df_features is None:
            return None
        df_input = self.df_features.copy()
        df_input["temp"] = temp
        df_input["ph"] = ph
        for col in [c for c in self.feature_cols if c.startswith("sub_")]:
            df_input[col] = (substrate == col.replace("sub_", "")).astype(int) \
                if hasattr(substrate, "astype") else int(substrate == col.replace("sub_", ""))
        try:
            X = df_input[self.feature_cols]
        except KeyError as e:
            return None
        yields = self.model.predict(X)
        best_idx = int(np.argmax(yields))
        best_id = df_input.iloc[best_idx]["id"]
        meta = self.df_kinetics[self.df_kinetics["id"] == best_id].iloc[0].to_dict()
        return {"id": best_id, "predicted_yield": float(yields[best_idx]),
                "kcat": meta.get("kcat"), "Km": meta.get("Km"),
                "t_opt": meta.get("t_opt"), "organism": meta.get("organism", "Unknown")}

    def _mutate_sequence(self, sequence):
        if not sequence:
            return sequence, "No seq"
        seq = list(sequence)
        pos = int(self.rng.integers(0, len(seq)))
        orig = seq[pos]
        new = orig
        while new == orig:
            new = AA_LIST[int(self.rng.integers(0, len(AA_LIST)))]
        seq[pos] = new
        return "".join(seq), f"{orig}{pos + 1}{new}"

    def apply_mutation(self, sequence, mutation_str):
        import re
        try:
            m = re.search(r"([A-Z])(\d+)([A-Z])", mutation_str)
            if not m:
                return sequence
            _, pos, new = m.groups()
            idx = int(pos) - 1
            if idx < 0 or idx >= len(sequence):
                return sequence
            return sequence[:idx] + new + sequence[idx + 1:]
        except Exception:
            return sequence

    def _build_feature_row(self, vec, temp, ph, substrate):
        feat = {f"dim_{i}": vec[i] for i in range(len(vec))}
        feat["temp"] = temp
        feat["ph"] = ph
        for col in [c for c in self.feature_cols if c.startswith("sub_")]:
            feat[col] = 1 if substrate == col.replace("sub_", "") else 0
        for c in self.feature_cols:
            feat.setdefault(c, 0)
        return pd.DataFrame([feat], columns=self.feature_cols)

    def _predict(self, X):
        """Return (mean, std) using the GP's predictive variance when available."""
        try:
            mean, std = self.model.predict(X, return_std=True)
            return float(mean[0]), float(std[0])
        except TypeError:
            return float(self.model.predict(X)[0]), 0.0

    def _resolve_sequence(self, base_enzyme_id):
        row = self.df_kinetics[self.df_kinetics["id"] == base_enzyme_id]
        if row.empty:
            return None
        seq = row.iloc[0]["sequence"]
        if pd.isna(seq) or not isinstance(seq, str) or len(seq) == 0:
            import re
            m = re.search(r"^(.*)_v\d+_AI$", base_enzyme_id)
            if m:
                parent = self.df_kinetics[self.df_kinetics["id"] == m.group(1)]
                if not parent.empty:
                    return parent.iloc[0]["sequence"]
            return None
        return seq

    def propose_optimization(self, base_enzyme_id, temp, ph, substrate="Cellulose", n_tries=20):
        """Best-of-n point mutation by predicted yield, with GP uncertainty."""
        if self.df_kinetics is None or self.model is None:
            return None
        base_seq = self._resolve_sequence(base_enzyme_id)
        if not base_seq:
            return None

        wt_vec = self._get_embedding(base_seq)
        wt_yield, wt_std = self._predict(self._build_feature_row(wt_vec, temp, ph, substrate))

        best = None
        best_diff = -np.inf
        for _ in range(n_tries):
            mut_seq, mut_desc = self._mutate_sequence(base_seq)
            mvec = self._get_embedding(mut_seq)
            pred, pred_std = self._predict(self._build_feature_row(mvec, temp, ph, substrate))
            diff = pred - wt_yield
            if diff > best_diff:
                best_diff = diff
                best = {"mutation": mut_desc,
                        "predicted_yield": pred,
                        "predicted_yield_std": pred_std,
                        "baseline_yield": wt_yield,
                        "baseline_yield_std": wt_std,
                        "mechanism": "GP-predicted improvement (point mutation, ESM-2 embedding)"}
        return best
