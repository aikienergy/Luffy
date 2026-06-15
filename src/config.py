"""
Purpose: Single source of truth for all process / simulation constants.

Overview:
    Every "magic number" that previously lived scattered across the app, the
    validator and the data-generation scripts is centralised here so that the
    trained model, the screening tab and the verification tab all share ONE
    physical regime. This is a prerequisite for the simulation output to be
    meaningfully comparable against literature benchmarks (see calibration).

    Units convention used throughout the project:
        - concentration : mM (glucose-equivalents for cellulose)
        - time          : seconds
        - kcat          : 1/s
    These are documented again on the simulator (src/validation/validator.py).

References for the chosen values are given inline; full citations live in
data/curated/PROVENANCE.md.
"""
import json
import os

# --------------------------------------------------------------------------
# Reproducibility
# --------------------------------------------------------------------------
RANDOM_SEED = 42

# --------------------------------------------------------------------------
# Default process conditions
# --------------------------------------------------------------------------
DEFAULT_TEMP_C = 50.0       # standard fungal-cellulase saccharification temp
DEFAULT_PH = 5.0            # standard fungal-cellulase saccharification pH
DEFAULT_DURATION_H = 72.0   # benchmark hydrolysis time (saccharification studies report 48-72 h)

# --------------------------------------------------------------------------
# Enzyme loading (unified across Tab1 / Tab3 / training)
# --------------------------------------------------------------------------
# Industrial / benchmark cellulase loadings are reported on a protein-mass
# basis, typically ~10-20 mg protein per g glucan (NREL benchmark studies,
# doi:10.1186/1754-6834-4-29). We use 15 mg/g as the default.
ENZYME_LOADING_MG_PER_G_GLUCAN = 15.0

# Approximate molecular weights per cellulolytic enzyme class (Da).
# EG (endoglucanase) ~ 48-52 kDa; CBH (cellobiohydrolase Cel7A) ~ 60-65 kDa;
# BG (beta-glucosidase, fungal) ~ 90-120 kDa.
ENZYME_MW_DA = {
    "EG": 50000.0,
    "CBH": 60000.0,
    "BG": 90000.0,
}
DEFAULT_ENZYME_MW_DA = 55000.0  # fallback when class is unknown

# Default cocktail split (fraction of total enzyme protein per class).
# Defensible starting point: CBH-dominated systems with EG support and a
# smaller amount of fast BG (e.g. T. reesei secretomes are CBH-rich).
DEFAULT_COCKTAIL_FRACTIONS = {"EG": 0.35, "CBH": 0.50, "BG": 0.15}

# --------------------------------------------------------------------------
# Product-inhibition constants (mM). Cellobiose strongly inhibits CBH/EG;
# glucose inhibits BG. Values are typical literature magnitudes; see PROVENANCE.
# --------------------------------------------------------------------------
KI_CELLOBIOSE_MM = 5.0   # cellobiose inhibition of EG / CBH
KI_GLUCOSE_MM = 50.0     # glucose inhibition of BG

# --------------------------------------------------------------------------
# Environmental-response widths for calculate_effective_kcat (Gaussian model).
# --------------------------------------------------------------------------
TEMP_WIDTH_C = 12.0
PH_WIDTH = 1.5

# --------------------------------------------------------------------------
# Calibration target & literature reaction-rate band (ask #2).
#
# CALIB_TARGET: cellulose -> glucose conversion expected at the benchmark
# loading/time/conditions. Saccharification literature: low cellulase loadings
# give ~57-85% glucose yield on (pre)treated cellulose, dropping with solids
# loading (doi:10.1186/s13068-024-02485-6; PMC9985267). We target 0.80 for a
# realistic amorphous/pretreated substrate at 15 mg/g, 72 h.
#
# LIT_RATE_BAND: the low/high conversion envelope a credible literature system
# would occupy; the default WT simulation must land inside this band. The error
# criterion (see calibrate_model / tests) is |X_sim - X_target|/X_target <= 0.15.
# --------------------------------------------------------------------------
CALIB_TARGET_CONVERSION = 0.80      # fraction at DEFAULT_DURATION_H
CALIB_TOLERANCE_REL = 0.15          # acceptance: relative error <= 15 %
LIT_RATE_BAND = (0.50, 0.92)        # plausible final-conversion envelope (fraction)
CALIB_SUBSTRATE_G_PER_L = 50.0      # benchmark substrate loading for calibration
CALIB_BENCHMARK_DOI = "10.1186/s13068-024-02485-6"  # see PROVENANCE.md

# --------------------------------------------------------------------------
# Accessibility decay coefficient (alpha) for the cellulose-attack term.
# This is the SINGLE free parameter fitted by calibrate_model.py against
# CALIB_TARGET_CONVERSION. Until calibrated, a documented default is used.
# The fitted value is persisted to data/curated/calibration.json.
# --------------------------------------------------------------------------
_DEFAULT_ALPHA_ACCESSIBILITY = 2.0
_CALIBRATION_FILE = os.path.join(
    os.path.dirname(__file__), "..", "data", "curated", "calibration.json"
)


def get_accessibility_alpha():
    """Return the calibrated accessibility coefficient, or the default."""
    try:
        with open(_CALIBRATION_FILE, "r", encoding="utf-8") as fh:
            return float(json.load(fh)["alpha_accessibility"])
    except (FileNotFoundError, KeyError, ValueError, json.JSONDecodeError):
        return _DEFAULT_ALPHA_ACCESSIBILITY


def save_accessibility_alpha(alpha, metadata=None):
    """Persist the fitted accessibility coefficient (used by calibrate_model)."""
    os.makedirs(os.path.dirname(_CALIBRATION_FILE), exist_ok=True)
    payload = {"alpha_accessibility": float(alpha)}
    if metadata:
        payload.update(metadata)
    with open(_CALIBRATION_FILE, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)


# --------------------------------------------------------------------------
# Biological-plausibility bands per enzyme class x substrate (ask #2, §2.5b).
# A stored kcat/Km is accepted only if it falls inside the literature-observed
# range for its class and substrate type. Enforced by tests/test_plausibility.py.
# (kcat in 1/s, Km in mM where defined.)
# --------------------------------------------------------------------------
PLAUSIBILITY_BANDS = {
    # class : {"kcat": (lo, hi), "Km": (lo, hi)}
    "BG":  {"kcat": (1e2, 1e4), "Km": (0.05, 10.0)},     # on cellobiose (soluble)
    "CBH": {"kcat": (5e-3, 5.0), "Km": (0.1, 60.0)},     # on cellulose; Km apparent
    "EG":  {"kcat": (1e-2, 1e2), "Km": (0.1, 60.0)},     # broad (soluble + insoluble)
}
