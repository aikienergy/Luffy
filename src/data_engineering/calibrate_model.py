"""
Purpose: Calibrate the cellulose-hydrolysis model to a literature benchmark.

Overview:
    The cellulolytic model (src/validation/validator.py) has exactly ONE free
    parameter: the substrate-accessibility decay coefficient `alpha`. All kcat /
    Km values are fixed to literature (data/curated/literature_kinetics.csv).

    This script fits `alpha` by bisection so that the simulated cellulose->glucose
    conversion at the benchmark conditions matches the literature target
    (src/config.py CALIB_TARGET_CONVERSION) within CALIB_TOLERANCE_REL. The
    fitted value is persisted via config.save_accessibility_alpha().

    Error standard (the user's calibration requirement):
        RE = |X_sim(t_benchmark) - X_target| / X_target  must be <= 15 %.

    No network access required (tellurium only).
"""
import os
import sys

import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src import config
from src.validation.validator import EnzymeValidator, enzyme_mM, cellulose_gpl_to_glucose_equiv_mM

KINETICS = "data/processed/enzyme_kinetics.csv"


def _reference_cocktail(df):
    """Pick one Literature enzyme of each class (EG, CBH, BG) for calibration."""
    def pick(cls):
        sub = df[(df["enzyme_class"] == cls) & (df["source_type"] == "Literature")]
        if sub.empty:
            sub = df[df["enzyme_class"] == cls]
        if sub.empty:
            raise RuntimeError(f"No enzyme available for class {cls}; cannot calibrate.")
        return sub.iloc[0].to_dict()
    return pick("EG"), pick("CBH"), pick("BG")


def _params(row):
    return {"kcat": float(row["kcat"]), "Km": float(row["Km"]),
            "Ki": float(row.get("Ki", config.KI_CELLOBIOSE_MM)),
            "t_opt": float(row.get("t_opt", config.DEFAULT_TEMP_C)),
            "ph_opt": float(row.get("ph_opt", config.DEFAULT_PH))}


def simulate_conversion(alpha, eg, cbh, bg, validator=None):
    """Return glucose conversion fraction X = G/Cel0 at the benchmark time."""
    validator = validator or EnzymeValidator()
    cel_g_L = config.CALIB_SUBSTRATE_G_PER_L
    Cel0 = cellulose_gpl_to_glucose_equiv_mM(cel_g_L)
    fr = config.DEFAULT_COCKTAIL_FRACTIONS
    load = config.ENZYME_LOADING_MG_PER_G_GLUCAN
    e_eg = enzyme_mM(load * fr["EG"], cel_g_L, config.ENZYME_MW_DA["EG"])
    e_cbh = enzyme_mM(load * fr["CBH"], cel_g_L, config.ENZYME_MW_DA["CBH"])
    e_bg = enzyme_mM(load * fr["BG"], cel_g_L, config.ENZYME_MW_DA["BG"])

    t, Cel, C2, G = validator.run_cellulolytic_simulation(
        _params(eg), _params(cbh), _params(bg),
        substrate_conc_init=Cel0, conc_EG=e_eg, conc_CBH=e_cbh, conc_BG=e_bg,
        duration=config.DEFAULT_DURATION_H * 3600.0, steps=600,
        temp=config.DEFAULT_TEMP_C, ph=config.DEFAULT_PH, alpha=alpha)
    if G is None:
        return None
    return float(G[-1]) / Cel0


def calibrate(target=None, tol=None, lo=0.05, hi=40.0, max_iter=60):
    target = config.CALIB_TARGET_CONVERSION if target is None else target
    tol = config.CALIB_TOLERANCE_REL if tol is None else tol
    df = pd.read_csv(KINETICS)
    eg, cbh, bg = _reference_cocktail(df)
    validator = EnzymeValidator()

    # Conversion DECREASES as alpha increases (more accessibility decay).
    x_lo = simulate_conversion(lo, eg, cbh, bg, validator)  # high conversion
    x_hi = simulate_conversion(hi, eg, cbh, bg, validator)  # low conversion
    print(f"alpha={lo}: X={x_lo:.3f} | alpha={hi}: X={x_hi:.3f} | target={target:.3f}")
    if x_lo is None or x_hi is None:
        raise RuntimeError("Simulation failed during calibration bracketing.")
    if not (x_hi <= target <= x_lo):
        print("WARNING: target not bracketed by [lo,hi]; clamping to closest feasible alpha.")

    best_alpha, best_x = lo, x_lo
    for _ in range(max_iter):
        mid = 0.5 * (lo + hi)
        x = simulate_conversion(mid, eg, cbh, bg, validator)
        if abs(x - target) < abs(best_x - target):
            best_alpha, best_x = mid, x
        if x > target:      # too much conversion -> need more decay
            lo = mid
        else:               # too little -> less decay
            hi = mid
        if abs(x - target) / target <= tol * 0.2:  # tight inner convergence
            best_alpha, best_x = mid, x
            break

    re = abs(best_x - target) / target
    status = "PASS" if re <= tol else "FAIL"
    print(f"Calibrated alpha={best_alpha:.4f} -> X(72h)={best_x:.4f} "
          f"(target {target:.3f}, RE={re*100:.1f}%) [{status}]")
    config.save_accessibility_alpha(best_alpha, metadata={
        "target_conversion": target,
        "achieved_conversion": round(best_x, 4),
        "relative_error": round(re, 4),
        "status": status,
        "reference_enzymes": {"EG": eg["id"], "CBH": cbh["id"], "BG": bg["id"]},
        "benchmark_doi": config.CALIB_BENCHMARK_DOI,
        "substrate_g_per_L": config.CALIB_SUBSTRATE_G_PER_L,
        "loading_mg_per_g": config.ENZYME_LOADING_MG_PER_G_GLUCAN,
        "duration_h": config.DEFAULT_DURATION_H,
    })
    if re > tol:
        print("Calibration did NOT meet tolerance; review model/parameters.")
    return best_alpha, best_x, re


if __name__ == "__main__":
    calibrate()
