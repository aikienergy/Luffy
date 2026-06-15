"""
Purpose: Load and augment the enzyme dataset (feedback loop).

Overview:
    Loads data/processed/enzyme_kinetics.csv. The optional procedural-noise
    injection (used to give isoforms distinct properties in the augmentation
    loop) NEVER perturbs literature-sourced rows and is OFF by default, so it
    can never corrupt cited kcat/Km values. Missing data raises a clear error
    instead of silently returning mock enzymes.
"""
import hashlib
import os
from datetime import datetime

import pandas as pd

DATA_PATH = os.path.join(os.getcwd(), "data", "processed", "enzyme_kinetics.csv")
AUGMENTED_PATH = os.path.join(os.getcwd(), "data", "processed", "enzyme_kinetics_augmented.csv")
REQUIRED = ["id", "kcat", "Km", "organism"]


class DatasetManager:
    def __init__(self):
        self.path = AUGMENTED_PATH if os.path.exists(AUGMENTED_PATH) else DATA_PATH

    def load_static(self):
        """Load the dataset exactly as stored (no noise). Use for display/screening."""
        if not os.path.exists(self.path):
            raise FileNotFoundError(
                f"Kinetics dataset not found at {self.path}. "
                f"Run `python -m src.data_engineering.populate_kinetics` first.")
        df = pd.read_csv(self.path)
        missing = [c for c in REQUIRED if c not in df.columns]
        if missing:
            raise ValueError(
                f"{self.path} is missing required columns {missing}. "
                f"Re-run populate_kinetics.py to regenerate it.")
        return df

    def load_data(self, apply_noise=False):
        """
        Load the dataset. With apply_noise=True, adds small deterministic
        variability to NON-literature rows only (for the feedback/augmentation
        path); literature kcat/Km are never altered.
        """
        df = self.load_static()
        if apply_noise:
            df = self._inject_procedural_noise(df)
        return df

    def _inject_procedural_noise(self, df):
        """Deterministic +/-10% variability on ESTIMATED rows only (isoform spread)."""
        if "kcat" not in df.columns or "Km" not in df.columns:
            return df

        def noise(uid, salt):
            h = int(hashlib.md5(f"{uid}_{salt}".encode()).hexdigest(), 16)
            return 1.0 + ((h % 2000) / 10000.0 - 0.1)

        is_literature = df.get("source_type", pd.Series(["Estimated"] * len(df))) == "Literature"
        df = df.copy()
        for i, row in df.iterrows():
            if bool(is_literature.iloc[i]):
                continue  # never perturb cited values
            df.at[i, "kcat"] = row["kcat"] * noise(row["id"], "k")
            df.at[i, "Km"] = row["Km"] * noise(row["id"], "m")
        return df

    def augment_dataset(self, new_entry):
        df = self.load_static()
        new_entry = dict(new_entry)
        new_entry.setdefault("source_type", "Digital_Twin_Feedback")
        new_entry["updated_at"] = datetime.now().isoformat()
        if "id" not in new_entry:
            new_entry["id"] = f"MUT_{len(df) + 1:04d}"
        updated = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
        updated.to_csv(AUGMENTED_PATH, index=False)
        self.path = AUGMENTED_PATH
        print(f"Dataset augmented. New size: {len(updated)}")
        return True
