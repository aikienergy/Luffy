"""
Purpose: Define material properties and baseline enzyme data.
Overview: Contains dictionaries for Biomass composition (Cellulose, Hemicellulose, etc.) and Baseline Enzyme parameters (Reference Anchors).
"""
# Material & Enzyme Database
# Sources:
# - Biomass: Representative values from NREL / Phyllis2 / Literature
# - Enzymes: Open Enzyme Database (OED) / BRENDA (Curated)

BIOMASS_DATA = {
    "Rice Straw": {
        "description": "Agricultural residue from rice production.",
        "composition": {
            "Cellulose": 35.0,     # % dry weight
            "Hemicellulose": 25.0,
            "Lignin": 20.0,
            "Ash": 15.0
        },
        "source": "NREL / Literature"
    },
    "Coffee Beans (Spent)": {
        "description": "Residue after coffee extraction.",
        "composition": {
            "Cellulose": 12.0,
            "Hemicellulose": 39.0,
            "Lignin": 23.0,
            "Protein": 10.0
        },
        "source": "Phyllis2 Database"
    },
    "Sugarcane Bagasse": {
        "description": "Fibrous matter remaining after sugarcane crushing.",
        "composition": {
            "Cellulose": 42.0,
            "Hemicellulose": 25.0,
            "Lignin": 20.0,
            "Ash": 2.0
        },
        "source": "NREL"
    }
}

# Baseline Enzymes from Open Enzyme Database (OED)
# Mocking authoritative IDs and values
BASELINE_ENZYMES = {
    "OED-1001": {
        "name": "Cellulase (T. reesei)",
        "type": "Cellulase",
        "organism": "Trichoderma reesei",
        "kcat": 12.5,  # 1/s
        "Km": 0.8,     # mM
        "sequence": "MAPSVTLPLTTAILAIARLVAA...", # Truncated
        "source": "Open Enzyme Database (OED)"
    },
    "OED-1002": {
        "name": "Endoglucanase A",
        "type": "Cellulase",
        "organism": "Aspergillus niger",
        "kcat": 8.0,
        "Km": 1.2,
        "sequence": "MKLSTTLL...",
        "source": "Open Enzyme Database (OED)"
    },
    "OED-2001": {
        "name": "Lignin Peroxidase",
        "type": "Ligninase",
        "organism": "Phanerochaete chrysosporium",
        "kcat": 5.2,
        "Km": 0.4,
        "sequence": "MAFKVL...",
        "source": "Open Enzyme Database (OED)"
    }
}
