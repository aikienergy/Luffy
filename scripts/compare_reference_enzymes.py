"""
Compare AI predictions with literature-reported kcat/Km for enzymes
used in the referenced papers (Cellic CTec2, Accellerase, Celluclast).
These are commercial cocktails based on T. reesei cellulases.
"""
import pandas as pd

ai = pd.read_csv("data/processed/enzyme_kinetics.csv")

print("=" * 80)
print("COMPARISON: AI Predictions vs. Reference Paper Enzyme Values")
print("=" * 80)

# Published kcat/Km values for enzymes commonly found in CTec2/Celluclast cocktails
# These are the individual enzyme kinetics from characterization papers
literature_reference = {
    "T. reesei Cel7A (CBH I)": {
        "kcat_s": 4.3,      # s^-1 (BRENDA, on Avicel)
        "Km_mM": 0.041,     # mM (Avicel) - from Jalak & Valjamae (2010)
        "substrate": "Avicel (crystalline cellulose)",
        "source": "BRENDA / Murphy et al. (2012)",
        "type": "Cellobiohydrolase"
    },
    "T. reesei Cel6A (CBH II)": {
        "kcat_s": 3.9,      # s^-1
        "Km_mM": 0.024,     # mM (crystalline cellulose)
        "substrate": "crystalline cellulose",
        "source": "BRENDA",
        "type": "Cellobiohydrolase"
    },
    "T. reesei Cel7B (EG I)": {
        "kcat_s": 15.0,     # s^-1 on CMC
        "Km_mM": 0.5,       # mM (CMC)
        "substrate": "CMC",
        "source": "BRENDA",
        "type": "Cellulase"
    },
    "T. reesei Cel5A (EG II)": {
        "kcat_s": 28.0,     # s^-1 on CMC
        "Km_mM": 0.35,      # mM (CMC)
        "substrate": "CMC",
        "source": "BRENDA",
        "type": "Cellulase"
    },
    "T. reesei Cel12A (EG III)": {
        "kcat_s": 358.0,    # s^-1 (very high activity EG)
        "Km_mM": 9.5,       # mM (CMC)
        "substrate": "CMC",
        "source": "BRENDA",
        "type": "Cellulase"
    },
    "A. niger BGL1 (Beta-glucosidase)": {
        "kcat_s": 72.9,     # s^-1
        "Km_mM": 2.7,       # mM (cellobiose)
        "substrate": "cellobiose",
        "source": "BRENDA",
        "type": "Beta-glucosidase"
    },
    "T. reesei BGL1 (Beta-glucosidase)": {
        "kcat_s": 66.7,     # s^-1
        "Km_mM": 1.11,      # mM (cellobiose)
        "substrate": "cellobiose",
        "source": "BRENDA",
        "type": "Beta-glucosidase"
    },
}

print("\n--- Reference Enzyme Parameters (from characterization papers) ---\n")
for name, vals in literature_reference.items():
    eff = vals["kcat_s"] / vals["Km_mM"]
    print(f"  {name}")
    print(f"    kcat = {vals['kcat_s']:.1f} s-1, Km = {vals['Km_mM']:.3f} mM, kcat/Km = {eff:.1f} s-1.mM-1")
    print(f"    Substrate: {vals['substrate']}, Source: {vals['source']}")
    print()

# Compare with our AI predictions by specificity
print("=" * 80)
print("AI Prediction Ranges by Enzyme Type")
print("=" * 80)

for spec in ["Cellulase", "Beta-glucosidase", "Cellobiohydrolase"]:
    sub = ai[ai["specificity"] == spec]
    kcat_med = sub["kcat"].median()
    km_med = sub["Km"].median()
    eff_med = kcat_med / km_med
    
    # Get reference values for this type
    ref_vals = {k:v for k,v in literature_reference.items() if v["type"] == spec}
    
    print(f"\n{'='*60}")
    print(f"  {spec} (n={len(sub)})")
    print(f"{'='*60}")
    print(f"  AI Predictions (DLKcat kcat + CatPred Km):")
    print(f"    kcat: {sub['kcat'].min():.2f} - {sub['kcat'].max():.2f} (median={kcat_med:.2f}) s-1")
    print(f"    Km:   {sub['Km'].min():.4f} - {sub['Km'].max():.4f} (median={km_med:.4f}) mM")
    print(f"    kcat/Km: {eff_med:.1f} s-1.mM-1")
    
    if ref_vals:
        print(f"\n  Literature Reference Values:")
        for name, vals in ref_vals.items():
            eff_ref = vals["kcat_s"] / vals["Km_mM"]
            print(f"    {name}:")
            print(f"      kcat = {vals['kcat_s']:.1f} s-1, Km = {vals['Km_mM']:.3f} mM, kcat/Km = {eff_ref:.1f}")
        
        # Average literature values
        avg_kcat_lit = sum(v["kcat_s"] for v in ref_vals.values()) / len(ref_vals)
        avg_km_lit = sum(v["Km_mM"] for v in ref_vals.values()) / len(ref_vals)
        
        print(f"\n  Comparison (AI median vs Literature average):")
        print(f"    kcat ratio (AI/Lit): {kcat_med/avg_kcat_lit:.2f}x")
        print(f"    Km ratio (AI/Lit):   {km_med/avg_km_lit:.2f}x")

# T. reesei specific
print("\n" + "=" * 80)
print("T. reesei Enzymes in AI Dataset (these are the CTec2/Celluclast components)")
print("=" * 80)
tr = ai[ai['organism'].str.contains('Trichoderma|reesei|Hypocrea', case=False, na=False)]
for spec in tr['specificity'].unique():
    sub_tr = tr[tr['specificity'] == spec]
    print(f"\n  {spec} (n={len(sub_tr)}):")
    for _, row in sub_tr.iterrows():
        eff = row['kcat'] / row['Km'] if row['Km'] > 0 else 0
        print(f"    {row['accession']:12s} kcat={row['kcat']:8.2f}  Km={row['Km']:8.4f}  kcat/Km={eff:.1f}")
