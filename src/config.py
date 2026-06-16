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
# Bands are anchored to the full-text-verified values now in
# data/curated/literature_kinetics.csv (see data/curated/PROVENANCE.md):
#   BG  on cellobiose : kcat 31.6-80.3 1/s (A. niger/T. reesei/A. fumigatus),
#                       Km 0.88-22.3 mM (incl. high-Km T. maritima BglA).
#   CBH on crystalline cellulose : steady-state kcat ~0.02 1/s, apparent Km a few g/L
#                       (T. reesei & R. emersonii Cel7A; Sorensen 2015).
#   EG  : kcat 6-1721 1/s spanning crystalline (slow) to soluble lichenin/CMC (fast);
#         apparent Km up to ~157 mM glucose-equiv on CMC (AcCel12B).
# Earlier (pre-full-text) bands assumed inflated, misattributed BG kcat (~2589 1/s);
# they are widened here to bound the real measured ranges while still catching
# gross transcription errors (values off by >~1 order of magnitude).
PLAUSIBILITY_BANDS = {
    # class : {"kcat": (lo, hi), "Km": (lo, hi)}   (kcat 1/s; Km mM where defined)
    "BG":  {"kcat": (1e1, 1e4), "Km": (0.05, 30.0)},    # on cellobiose (soluble)
    "CBH": {"kcat": (5e-3, 5.0), "Km": (0.1, 60.0)},    # on cellulose; Km apparent
    "EG":  {"kcat": (1e-2, 1e4), "Km": (0.1, 200.0)},   # soluble + insoluble; apparent Km
}

# ==========================================================================
# Real-biomass support: lignin inhibition & geometric accessibility (Phase 3).
# These parameterise the substrate-property multipliers applied to the
# cellulose-attack rate in src/validation/validator.py. They are a separate
# effect from the conversion-dependent accessibility decay `alpha` (alpha = how
# the rate falls as conversion proceeds; the factors below = how a given
# biomass/pretreatment gates the initial attackable surface).
#
# PROVENANCE DISCIPLINE (mirrors the kinetics layer): each constant below is
# tagged as either
#   [MEASURED]  -- a value read verbatim from full text (documented with a DOI
#                  and quote in data/curated/PROVENANCE.md "Substrate-property
#                  layer" section), OR
#   [PARAMETER] -- a structural/assumed model parameter that is NOT a direct
#                  measurement. Where a [PARAMETER] is fit to literature yield
#                  bands it is "calibrated" by calibrate_biomass.py and the
#                  fitted value is persisted to biomass_calibration.json.
# This separation is what keeps the layer honest: a [PARAMETER] must never be
# presented to the user as a measurement.
# ==========================================================================

# --- Lignin hydrophobicity, by biomass type -------------------------------
# [PARAMETER, assumed-ordinal] Drives non-productive cellulase adsorption to
# lignin. The literature (Li & Zheng 2017, Biotechnol Adv 35(4):466-489,
# doi:10.1016/j.biotechadv.2017.03.010; primary data Yu et al. 2014,
# Biotechnol Biofuels 7:38, PMC3995585) supports a DIRECTION only:
# GUAIACYL-rich lignin (softwood, LOW S/G ratio) adsorbs cellulase MORE strongly
# than syringyl-rich (hardwood, high S/G) lignin -- "the lower the S/G ratio, the
# higher affinity". No paper tabulates a dimensionless 0-1 index; these numbers
# encode that rank ORDER only and their magnitudes are assumed, not measured
# (kept fixed; not calibrated).
HYDROPHOBICITY_INDEX = {
    "softwood": 0.85,   # guaiacyl-rich (low S/G) -> strongest adsorption
    "hardwood": 0.65,   # syringyl-rich (high S/G) -> weaker adsorption
    "grass": 0.50,      # p-coumarate/ferulate esters -> weakest
}

# --- Soluble-inhibitor constants (mM) -------------------------------------
# [PARAMETER] None of these is a full-text Ki: the primary literature reports
# phenol/furan effects as % deactivation or mg-ratios, NOT Michaelis Ki in mM
# (see PROVENANCE.md "Soluble inhibitors"). They are calibrated/assumed scales
# encoding the well-established MECHANISM: phenolics are POTENT cellulase
# inhibitors/deactivators (small Ki) whereas furans (furfural/HMF) are
# comparatively WEAK on the enzymes (large Ki) -- so ki_phenol << ki_furfural.
#   Mechanism refs: phenols  -> Ximenes et al. 2010, Enzyme Microb Technol
#                   46(3-4):170, doi:10.1016/j.enzmictec.2009.11.001; 2011
#                   48(1):54, doi:10.1016/j.enzmictec.2010.09.006 (PMID 22112771).
#                   furans   -> Kim et al. 2011, Enzyme Microb Technol
#                   48(4-5):408, doi:10.1016/j.enzmictec.2011.01.007
#                   (PMID 22112958) -- furans weak; phenolics are the cause.
INHIBITION_CONSTANTS = {
    "ki_phenol": 8.0,     # mM  [PARAMETER] phenolics potent -> small Ki
    "ki_furfural": 50.0,  # mM  [PARAMETER] furans weak -> large Ki (>> ki_phenol)
    "ki_hmf": 60.0,       # mM  [PARAMETER] HMF weaker still
    "k_ads": 0.15,        # [PARAMETER, calibrated] Langmuir lignin-adsorption const
}

# --- Geometric accessibility parameters -----------------------------------
# [PARAMETER, calibrated] Surface-accessibility law in validator.calculate_
# accessibility: surface_factor = 1/(1 + (particle_size/D_REF)**EXPONENT).
# Smaller particles / lower crystallinity expose more attackable surface
# (qualitatively per Alvira et al. 2010, doi:10.1016/j.biortech.2009.11.093);
# D_REF and EXPONENT are NOT measured -- they are fit to literature yield bands
# by calibrate_biomass.py (result in biomass_calibration.json).
GEOMETRIC_ACCESSIBILITY = {
    "d_ref": 0.5,       # mm, reference particle size
    "exponent": 1.5,    # surface-decay exponent
}

# --------------------------------------------------------------------------
# Biomass-property calibration persistence (analogous to calibration.json for
# alpha). calibrate_biomass.py fits the [PARAMETER, calibrated] structural
# constants {k_ads, d_ref, exponent} so the predicted conversion per
# (biomass x pretreatment) lands inside that combination's literature yield
# band. Until calibrated, the documented defaults above are used.
# --------------------------------------------------------------------------
_BIOMASS_CALIBRATION_FILE = os.path.join(
    os.path.dirname(__file__), "..", "data", "curated", "biomass_calibration.json"
)


def get_biomass_params():
    """Return calibrated {k_ads, d_ref, exponent}, falling back to documented
    defaults. Used by the validator's substrate-property factors so that a
    biomass calibration (if present) is honoured everywhere consistently."""
    defaults = {
        "k_ads": INHIBITION_CONSTANTS["k_ads"],
        "d_ref": GEOMETRIC_ACCESSIBILITY["d_ref"],
        "exponent": GEOMETRIC_ACCESSIBILITY["exponent"],
    }
    try:
        with open(_BIOMASS_CALIBRATION_FILE, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        fitted = data.get("parameters", {})
        for k in defaults:
            if k in fitted:
                defaults[k] = float(fitted[k])
    except (FileNotFoundError, KeyError, ValueError, json.JSONDecodeError):
        pass
    return defaults


def save_biomass_params(params, metadata=None):
    """Persist the fitted biomass structural parameters (used by calibrate_biomass)."""
    os.makedirs(os.path.dirname(_BIOMASS_CALIBRATION_FILE), exist_ok=True)
    payload = {"parameters": {k: float(v) for k, v in params.items()}}
    if metadata:
        payload.update(metadata)
    with open(_BIOMASS_CALIBRATION_FILE, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)


# --- Plausibility bands for substrate-property constants -------------------
# [audit] Guard rails for the substrate-property layer, analogous to
# PLAUSIBILITY_BANDS for kinetics. A calibrated/edited constant outside its band
# signals a transcription or fitting error. Enforced by tests/test_plausibility.py.
SUBSTRATE_PROPERTY_BANDS = {
    "ki_phenol_mM": (0.5, 50.0),      # phenol cellulase Ki / IC50 range
    "ki_furfural_mM": (5.0, 200.0),   # furans weak -> high Ki
    "ki_hmf_mM": (5.0, 300.0),
    "k_ads": (0.01, 5.0),             # Langmuir adsorption constant
    "d_ref_mm": (0.05, 5.0),          # reference particle size
    "accessibility_exponent": (0.5, 4.0),
    "lignin_fraction": (0.05, 0.40),  # dry-weight lignin fraction of biomass
    "crystallinity": (0.30, 0.85),    # cellulose crystallinity index (CrI)
}
