"""
Purpose: Define biomass material properties used by the app.

Overview:
    Biomass composition figures are representative literature values, each tied
    to a citable primary source (DOI) — see "Composition sources" below and the
    "Substrate-property layer" section of data/curated/PROVENANCE.md. Enzyme
    kinetic parameters are NOT defined here — they live in
    data/processed/enzyme_kinetics.csv (literature-sourced + clearly-labelled
    estimates), so the app has a single, provenance-tracked source of kinetics.

    Each entry also carries the physical properties used by the real-biomass
    model in src/validation/validator.py:
      - lignin_fraction : lignin mass fraction (drives non-productive cellulase
                          adsorption -> lower hydrolysis rate).
      - particle_size   : mm; smaller = more accessible surface.
      - crystallinity   : CrI (0-1); higher = harder to attack (representative).
      - biomass_type    : grass / hardwood / softwood (sets lignin hydrophobicity).
      - literature_yield: plausible glucose-conversion band (mild/mechanical only).

Composition sources (full-text verified, see PROVENANCE.md):
    - Rice straw: Binod et al. (2010) Bioresour Technol, doi:10.1016/j.biortech.2009.10.079
      (cellulose ~32-35%, hemicellulose ~24%, lignin ~12-18%, high ash/silica ~12-17%).
    - Wheat straw: Alvira et al. (2010) Bioresour Technol, doi:10.1016/j.biortech.2009.11.093
      (review; Table 1 reproduced from Sun & Cheng 2002, doi:10.1016/S0960-8524(01)00212-7).
    - Corn stover: Templeton et al. (2010) J Agric Food Chem, doi:10.1021/jf100807b;
      NREL standard feedstock TP-510-32438 (glucan ~37%, xylan ~21%, lignin ~18%).
    - Sugarcane bagasse: Pandey et al. (2000) Bioresour Technol,
      doi:10.1016/S0960-8524(99)00142-X (~45% cellulose, ~27% hemicellulose, ~22% lignin).
    - Spent coffee grounds: Ballesteros et al. (2014) Food Bioprocess Technol,
      doi:10.1007/s11947-014-1349-z (cellulose 12.4%, hemicellulose 39.1%, lignin 23.9%).
    (Composition varies by cultivar/season; representative dry-weight %.)
"""

BIOMASS_DATA = {
    "Rice Straw": {
        "description": "Agricultural residue from rice production.",
        "composition": {"Cellulose": 35.0, "Hemicellulose": 24.0, "Lignin": 17.0, "Ash": 14.0},
        "lignin_fraction": 0.17, "particle_size": 1.0, "crystallinity": 0.55,
        "biomass_type": "grass", "literature_yield": (0.30, 0.45),
        "source": "Binod et al. (2010) Bioresour Technol, doi:10.1016/j.biortech.2009.10.079",
    },
    "Wheat Straw": {
        "description": "Agricultural residue from wheat production.",
        "composition": {"Cellulose": 35.0, "Hemicellulose": 24.0, "Lignin": 17.0, "Ash": 7.0},
        "lignin_fraction": 0.17, "particle_size": 2.0, "crystallinity": 0.60,
        "biomass_type": "grass", "literature_yield": (0.25, 0.35),
        "source": "Alvira et al. (2010) Bioresour Technol, doi:10.1016/j.biortech.2009.11.093",
    },
    "Corn Stover": {
        "description": "Stalks/leaves remaining after maize harvest.",
        "composition": {"Cellulose": 37.0, "Hemicellulose": 21.0, "Lignin": 18.0, "Ash": 6.0},
        "lignin_fraction": 0.18, "particle_size": 1.5, "crystallinity": 0.62,
        "biomass_type": "grass", "literature_yield": (0.25, 0.35),
        "source": "Templeton et al. (2010) J Agric Food Chem, doi:10.1021/jf100807b; NREL TP-510-32438",
    },
    "Sugarcane Bagasse": {
        "description": "Fibrous matter remaining after sugarcane crushing.",
        "composition": {"Cellulose": 45.0, "Hemicellulose": 27.0, "Lignin": 22.0, "Ash": 3.0},
        "lignin_fraction": 0.22, "particle_size": 1.0, "crystallinity": 0.60,
        "biomass_type": "grass", "literature_yield": (0.20, 0.30),
        "source": "Pandey et al. (2000) Bioresour Technol, doi:10.1016/S0960-8524(99)00142-X",
    },
    "Coffee Beans (Spent)": {
        "description": "Residue after coffee extraction.",
        "composition": {"Cellulose": 12.0, "Hemicellulose": 39.0, "Lignin": 24.0, "Protein": 17.0},
        "lignin_fraction": 0.24, "particle_size": 0.5, "crystallinity": 0.55,
        "biomass_type": "hardwood", "literature_yield": (0.15, 0.25),
        "source": "Ballesteros et al. (2014) Food Bioprocess Technol, doi:10.1007/s11947-014-1349-z",
    },
}

# Pretreatment presets (rice-straw-anchored). `severity` (0-1) is a NORMALISED
# model input encoding how much recalcitrance the pretreatment removes
# (defibrillation/decrystallisation + delignification); it is ordered to match
# the full-text-verified rice-straw glucose-yield series (untreated/mechanical
# ~36% < dilute acid ~66-72% < hydrothermal >=85% < steam explosion ~89-100%),
# NOT a measured CSF. `inhibitors` are representative post-pretreatment soluble
# inhibitor levels (mM); acid/hydrothermal release more furfural/HMF (furans are
# WEAK cellulase inhibitors) and some phenolics (potent). See PROVENANCE.md.
PRETREATMENT_PRESETS = {
    "Simple Crushing": {
        "severity": 0.05, "csf_range": None,
        "description": "Mechanical crushing only (blender/mixer).",
        "inhibitors": {"phenol": 0.0, "furfural": 0.0},
        "literature": {"yield": (0.30, 0.45), "time_h": 72,
                       "source": "Yu et al. (2024) Agronomy 14(11):2550, doi:10.3390/agronomy14112550",
                       "enzyme": "Cellic CTec2", "eg_bg_ratio": "70:30", "fpu": 10},
    },
    "Dilute Acid": {
        "severity": 0.55, "csf_range": (1.5, 2.5),
        "description": "0.5-2% H2SO4, 121-160 C; releases furfural/HMF.",
        "inhibitors": {"phenol": 2.0, "furfural": 10.0},
        "literature": {"yield": (0.60, 0.75), "time_h": 72,
                       "source": "Agrawal et al. (2018) Front Energy Res 6:115, doi:10.3389/fenrg.2018.00115",
                       "enzyme": "Accellerase 1500", "eg_bg_ratio": "65:35", "fpu": 40},
    },
    "Hydrothermal": {
        "severity": 0.90, "csf_range": (3.5, 4.5),
        "description": "Liquid hot water, 180-210 C, 10-30 min.",
        "inhibitors": {"phenol": 3.0, "furfural": 8.0},
        "literature": {"yield": (0.80, 0.90), "time_h": 48,
                       "source": "Yu G. et al. (2010) Appl Biochem Biotechnol 160(2):539, doi:10.1007/s12010-008-8420-z",
                       "enzyme": "Cellic CTec2 + NS22118", "eg_bg_ratio": "60:40", "fpu": 20},
    },
    "Steam Explosion": {
        "severity": 0.97, "csf_range": (3.5, 4.5),
        "description": "190-210 C, 5-10 min, rapid decompression.",
        "inhibitors": {"phenol": 4.0, "furfural": 15.0},
        "literature": {"yield": (0.85, 1.00), "time_h": 72,
                       "source": ("Wood et al. (2016) Biotechnol Biofuels 9:193, doi:10.1186/s13068-016-0599-6; "
                                  "Semwal et al. (2019) Biomass Bioenergy 130:105390, doi:10.1016/j.biombioe.2019.105390"),
                       "enzyme": "Celluclast 1.5L + Novozyme 188", "eg_bg_ratio": "80:20", "fpu": 20},
    },
}
