"""
Purpose: Define biomass material properties used by the app.

Overview:
    Biomass composition figures are representative literature values. Enzyme
    kinetic parameters are NOT defined here -- they live in
    data/processed/enzyme_kinetics.csv (literature-sourced + clearly-labelled
    estimates), so the app has a single, provenance-tracked source of kinetics.

    Each entry also carries the physical properties used by the real-biomass
    model in src/validation/validator.py:
      - lignin_fraction : lignin mass fraction (drives non-productive cellulase
                          adsorption -> lower hydrolysis rate).
      - particle_size   : mm; smaller = more accessible surface.
      - crystallinity   : CrI (0-1); higher = harder to attack.
      - biomass_type    : grass / hardwood / softwood (sets lignin hydrophobicity).
      - literature_yield: plausible glucose-conversion band (simple crushing).

Composition sources:
    - Rice/wheat straw, corn stover, bagasse: NREL feedstock composition / Alvira
      et al. (2010). Spent coffee grounds: Phyllis2 biomass database (ECN.TNO).
    (Composition varies by cultivar/pretreatment; representative dry-weight %.)
"""

BIOMASS_DATA = {
    "Rice Straw": {
        "description": "Agricultural residue from rice production.",
        "composition": {"Cellulose": 35.0, "Hemicellulose": 25.0, "Lignin": 20.0, "Ash": 15.0},
        "lignin_fraction": 0.20, "particle_size": 1.0, "crystallinity": 0.65,
        "biomass_type": "grass", "literature_yield": (0.30, 0.40),
        "source": "NREL feedstock composition / literature",
    },
    "Wheat Straw": {
        "description": "Agricultural residue from wheat production.",
        "composition": {"Cellulose": 40.0, "Hemicellulose": 23.0, "Lignin": 18.0, "Ash": 10.0},
        "lignin_fraction": 0.18, "particle_size": 2.0, "crystallinity": 0.70,
        "biomass_type": "grass", "literature_yield": (0.25, 0.30),
        "source": "Alvira et al. (2010)",
    },
    "Corn Stover": {
        "description": "Stalks/leaves remaining after maize harvest.",
        "composition": {"Cellulose": 38.0, "Hemicellulose": 26.0, "Lignin": 19.0, "Ash": 8.0},
        "lignin_fraction": 0.19, "particle_size": 1.5, "crystallinity": 0.68,
        "biomass_type": "grass", "literature_yield": (0.25, 0.35),
        "source": "NREL feedstock composition database",
    },
    "Sugarcane Bagasse": {
        "description": "Fibrous matter remaining after sugarcane crushing.",
        "composition": {"Cellulose": 42.0, "Hemicellulose": 25.0, "Lignin": 20.0, "Ash": 2.0},
        "lignin_fraction": 0.20, "particle_size": 1.0, "crystallinity": 0.65,
        "biomass_type": "grass", "literature_yield": (0.20, 0.30),
        "source": "NREL feedstock composition",
    },
    "Coffee Beans (Spent)": {
        "description": "Residue after coffee extraction.",
        "composition": {"Cellulose": 12.0, "Hemicellulose": 39.0, "Lignin": 23.0, "Protein": 10.0},
        "lignin_fraction": 0.23, "particle_size": 0.5, "crystallinity": 0.60,
        "biomass_type": "hardwood", "literature_yield": (0.15, 0.25),
        "source": "Phyllis2 biomass database (ECN.TNO)",
    },
}

# Pretreatment presets: severity raises geometric accessibility (breaks
# crystallinity / removes lignin) and shifts the plausible conversion band.
# Combined Severity Factor (CSF) ranges and rice-straw literature yields are
# representative; see src/config.py for the inhibition/accessibility constants.
PRETREATMENT_PRESETS = {
    "Simple Crushing": {
        "severity": 0.0, "csf_range": None,
        "description": "Mechanical crushing only (blender/mixer).",
        "literature": {"yield": (0.30, 0.40), "time_h": 72, "source": "MDPI (2023)",
                       "enzyme": "Cellic CTec2", "eg_bg_ratio": "70:30", "fpu": 10},
    },
    "Dilute Acid": {
        "severity": 0.6, "csf_range": (1.5, 2.5),
        "description": "0.5-2% H2SO4, 121 C, 60 min.",
        "literature": {"yield": (0.28, 0.36), "time_h": 72, "source": "RSC Advances (2019)",
                       "enzyme": "Accellerase 1500", "eg_bg_ratio": "65:35", "fpu": 40},
    },
    "Hydrothermal": {
        "severity": 0.5, "csf_range": (1.5, 2.5),
        "description": "180-210 C, 10-30 min, hot water.",
        "literature": {"yield": (0.50, 0.70), "time_h": 48, "source": "NIH/PubMed (2020)",
                       "enzyme": "Cellic CTec2 + NS22118", "eg_bg_ratio": "60:40", "fpu": 20},
    },
    "Steam Explosion": {
        "severity": 1.0, "csf_range": (3.0, 4.0),
        "description": "210 C, 10 min, rapid decompression.",
        "literature": {"yield": (0.80, 1.00), "time_h": 72, "source": "NIH/PubMed (2018)",
                       "enzyme": "Celluclast 1.5L + Novozyme 188", "eg_bg_ratio": "80:20", "fpu": 20},
    },
}
