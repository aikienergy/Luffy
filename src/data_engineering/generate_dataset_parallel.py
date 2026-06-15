"""
Purpose: Generate the yield-predictor training grid via parallel ODE simulation.

Overview:
    For each enzyme x temperature x pH x substrate, simulates cellulose
    hydrolysis (single-enzyme productivity, with accessibility decay) and records
    the cellulose->glucose CONVERSION (product / initial substrate), an explicit,
    unit-correct quantity -- replacing the previous ambiguous `p_final / 100.0`.

    Enzyme loading uses the unified enzyme_mM() conversion and the same loading
    constant as the app/calibration, so the trained model and the app share one
    physical regime. Only enzymes with ESM features are included so the training
    merge is clean.

    No network access required (tellurium only).
"""
import os
import sys
import time

import pandas as pd
from joblib import Parallel, delayed

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src import config
from src.validation.validator import (EnzymeValidator, enzyme_mM,
                                       cellulose_gpl_to_glucose_equiv_mM)

INPUT_KINETICS = "data/processed/enzyme_kinetics.csv"
FEATURES = "data/processed/enzyme_features.csv"
OUTPUT_FILE = "data/processed/training_dataset.csv"

# Coarse substrate-selectivity factor (cellulose-active vs not). This is an
# acknowledged heuristic for cross-substrate activity, kept simple and labelled.
SUBSTRATE_ACTIVITY = {
    "Cellulase": {"Cellulose": 1.0, "Bagasse": 0.7, "Xylan": 0.1},
    "Other":     {"Cellulose": 0.1, "Bagasse": 0.1, "Xylan": 0.1},
}


def simulate_single_condition(row, temp, ph, substrate):
    try:
        val = EnzymeValidator()
        enzyme_class = row.get("enzyme_class", "EG")
        mw = config.ENZYME_MW_DA.get(enzyme_class, config.DEFAULT_ENZYME_MW_DA)
        spec = row.get("specificity", "Cellulase")
        sel = SUBSTRATE_ACTIVITY.get(spec, SUBSTRATE_ACTIVITY["Other"]).get(substrate, 0.1)

        cel_g_L = config.CALIB_SUBSTRATE_G_PER_L
        Cel0 = cellulose_gpl_to_glucose_equiv_mM(cel_g_L)
        e_conc = enzyme_mM(config.ENZYME_LOADING_MG_PER_G_GLUCAN, cel_g_L, mw)

        t, y = val.run_kinetic_simulation(
            kcat=float(row["kcat"]) * sel, Km=float(row["Km"]),
            substrate_conc_init=Cel0, enzyme_conc=e_conc,
            duration=config.DEFAULT_DURATION_H * 3600.0, steps=200,
            temp=temp, ph=ph, ki=float(row.get("Ki", config.KI_CELLOBIOSE_MM)),
            t_opt=float(row.get("t_opt", config.DEFAULT_TEMP_C)),
            ph_opt=float(row.get("ph_opt", config.DEFAULT_PH)))
        if y is None:
            return None
        conversion = float(y[-1, 1]) / Cel0  # product / initial substrate
        conversion = max(0.0, min(1.0, conversion))
        return {"id": row["id"], "temp": temp, "ph": ph, "substrate": substrate,
                "yield": round(conversion, 4),
                "kcat_base": float(row["kcat"]), "Km_base": float(row["Km"]),
                "enzyme_type": enzyme_class}
    except Exception:
        return None


def generate_dataset_parallel():
    if not os.path.exists(INPUT_KINETICS):
        raise FileNotFoundError("enzyme_kinetics.csv not found. Run populate_kinetics first.")
    df_enz = pd.read_csv(INPUT_KINETICS)

    # Only enzymes with ESM features can be used for training (clean merge).
    if os.path.exists(FEATURES):
        feat_ids = set(pd.read_csv(FEATURES, usecols=["id"])["id"].astype(str))
        before = len(df_enz)
        df_enz = df_enz[df_enz["id"].astype(str).isin(feat_ids)]
        print(f"Using {len(df_enz)}/{before} enzymes that have ESM features.")
    else:
        print("WARNING: enzyme_features.csv not found; using all enzymes.")

    temps = [30.0, 40.0, 50.0, 60.0, 70.0]
    phs = [4.0, 5.0, 6.0, 7.0, 8.0]
    substrates = ["Cellulose", "Xylan", "Bagasse"]

    tasks = [(row, t, p, s)
             for _, row in df_enz.iterrows()
             for s in substrates for t in temps for p in phs]
    print(f"Total simulations: {len(tasks)}")

    start = time.time()
    results = Parallel(n_jobs=-1, verbose=1)(
        delayed(simulate_single_condition)(row, t, p, s) for row, t, p, s in tasks)
    valid = [r for r in results if r is not None]
    print(f"Completed in {time.time() - start:.1f}s ({len(valid)}/{len(tasks)} valid).")

    pd.DataFrame(valid).to_csv(OUTPUT_FILE, index=False)
    print(f"Saved dataset to {OUTPUT_FILE}")


if __name__ == "__main__":
    generate_dataset_parallel()
