"""
Purpose: Define biomass material properties used by the app.

Overview:
    Biomass composition figures are representative literature values. Enzyme
    kinetic parameters are NOT defined here -- they live in
    data/processed/enzyme_kinetics.csv (literature-sourced + clearly-labelled
    estimates), so the app has a single, provenance-tracked source of kinetics.
    The previous mock `BASELINE_ENZYMES` dict (fabricated ids/sequences) has
    been removed.

Composition sources:
    - Rice straw / sugarcane bagasse: NREL feedstock composition databases.
    - Spent coffee grounds: Phyllis2 biomass database (ECN.TNO).
    (Lignocellulose composition varies by cultivar/pretreatment; these are
     representative dry-weight percentages.)
"""

BIOMASS_DATA = {
    "Rice Straw": {
        "description": "Agricultural residue from rice production.",
        "composition": {
            "Cellulose": 35.0,     # % dry weight
            "Hemicellulose": 25.0,
            "Lignin": 20.0,
            "Ash": 15.0,
        },
        "source": "NREL feedstock composition / literature",
    },
    "Coffee Beans (Spent)": {
        "description": "Residue after coffee extraction.",
        "composition": {
            "Cellulose": 12.0,
            "Hemicellulose": 39.0,
            "Lignin": 23.0,
            "Protein": 10.0,
        },
        "source": "Phyllis2 biomass database (ECN.TNO)",
    },
    "Sugarcane Bagasse": {
        "description": "Fibrous matter remaining after sugarcane crushing.",
        "composition": {
            "Cellulose": 42.0,
            "Hemicellulose": 25.0,
            "Lignin": 20.0,
            "Ash": 2.0,
        },
        "source": "NREL feedstock composition",
    },
}
