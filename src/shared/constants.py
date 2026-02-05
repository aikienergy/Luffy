"""
Phase 3: Real Biomass Support Constants
Biomass presets and lignin inhibition parameters
"""

# Lignin hydrophobicity index by biomass type
# Based on Li & Zheng (2017) - S/G ratio affects enzyme adsorption
HYDROPHOBICITY_INDEX = {
    'softwood': 0.85,   # High syringyl content
    'hardwood': 0.65,   # High guaiacyl content
    'grass': 0.50       # p-coumarate esters
}

# Biomass presets with literature-backed composition and expected yields
BIOMASS_PRESETS = {
    'rice_straw': {
        'name': '稲わら (Rice Straw)',
        'cellulose': 0.37,
        'hemicellulose': 0.24,
        'lignin': 0.15,
        'particle_size': 1.0,
        'crystallinity': 0.65,
        'type': 'grass',
        'literature_yield': (0.30, 0.40),  # Simple crushing @24h
        'literature_time_h': 24,  # Measurement time in hours
        'literature_source': 'NIH, MDPI databases'
    },
    'wheat_straw': {
        'name': '小麦わら (Wheat Straw)',
        'cellulose': 0.40,
        'hemicellulose': 0.23,
        'lignin': 0.18,
        'particle_size': 2.0,
        'crystallinity': 0.70,
        'type': 'grass',
        'literature_yield': (0.25, 0.30),  # Simple crushing @24h
        'literature_time_h': 24,
        'literature_source': 'Alvira et al. (2010)'
    },
    'corn_stover': {
        'name': 'トウモロコシ茎 (Corn Stover)',
        'cellulose': 0.38,
        'hemicellulose': 0.26,
        'lignin': 0.19,
        'particle_size': 1.5,
        'crystallinity': 0.68,
        'type': 'grass',
        'literature_yield': (0.25, 0.35),  # Simple crushing @24h
        'literature_time_h': 24,
        'literature_source': 'NREL Database'
    },
    'bagasse': {
        'name': 'バガス (Bagasse)',
        'cellulose': 0.42,
        'hemicellulose': 0.25,
        'lignin': 0.20,
        'particle_size': 1.0,
        'crystallinity': 0.65,
        'type': 'grass',
        'literature_yield': (0.20, 0.30),  # Simple crushing @24h
        'literature_time_h': 24,
        'literature_source': 'General literature'
    }
}

# Pretreatment severity mapping to Combined Severity Factor (CSF)
# Now includes rice straw specific literature data
PRETREATMENT_PRESETS = {
    'simple_crushing': {
        'name': 'Simple Crushing',
        'severity': 0.0,
        'csf_range': None,
        'description': 'Mechanical crushing only (blender/mixer)',
        'rice_straw_literature': {
            'yield': (0.30, 0.40),
            'time_h': 72,
            'source': 'MDPI (2023) - Untreated rice straw hydrolysis'
        }
    },
    'dilute_acid': {
        'name': 'Dilute Acid',
        'severity': 0.6,
        'csf_range': (1.5, 2.5),
        'description': '0.5-2% H2SO4, 121°C, 60 min',
        'rice_straw_literature': {
            'yield': (0.28, 0.36),
            'time_h': 72,
            'source': 'RSC Advances (2019) - Dilute acid pretreatment optimization'
        }
    },
    'mild_hydrothermal': {
        'name': 'Hydrothermal',
        'severity': 0.5,
        'csf_range': (1.5, 2.5),
        'description': '180-210°C, 10-30 min, hot water',
        'rice_straw_literature': {
            'yield': (0.50, 0.70),
            'time_h': 48,
            'source': 'NIH/PubMed (2020) - Hydrothermal pretreatment of rice straw'
        }
    },
    'steam_explosion': {
        'name': 'Steam Explosion',
        'severity': 1.0,
        'csf_range': (3.0, 4.0),
        'description': '210°C, 10 min, rapid decompression',
        'rice_straw_literature': {
            'yield': (0.80, 1.00),
            'time_h': 72,
            'source': 'NIH/PubMed (2018) - Steam explosion at 210°C'
        }
    }
}

# Inhibition constants from literature
INHIBITION_CONSTANTS = {
    'ki_phenol': 8.0,       # mM, Ximenes et al. (2010)
    'ki_furfural': 2.0,     # mM, literature consensus
    'ki_hmf': 5.0,          # mM, hydroxymethylfurfural
    'k_ads': 0.15           # Langmuir adsorption constant
}
