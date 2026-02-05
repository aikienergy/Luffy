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
        'literature_source': 'General literature'
    }
}

# Pretreatment severity mapping to Combined Severity Factor (CSF)
PRETREATMENT_PRESETS = {
    'simple_crushing': {
        'name': 'Simple Crushing',
        'severity': 0.0,
        'csf_range': None,
        'description': 'Mechanical crushing only (blender/mixer)'
    },
    'mild_hydrothermal': {
        'name': 'Mild Hydrothermal',
        'severity': 0.5,
        'csf_range': (1.5, 2.5),
        'description': '120-160°C, 10-30 min'
    },
    'steam_explosion': {
        'name': 'Steam Explosion',
        'severity': 1.0,
        'csf_range': (3.0, 4.0),
        'description': '180-220°C, 3-10 min, rapid decompression'
    }
}

# Inhibition constants from literature
INHIBITION_CONSTANTS = {
    'ki_phenol': 8.0,       # mM, Ximenes et al. (2010)
    'ki_furfural': 2.0,     # mM, literature consensus
    'ki_hmf': 5.0,          # mM, hydroxymethylfurfural
    'k_ads': 0.15           # Langmuir adsorption constant
}
