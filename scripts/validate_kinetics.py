"""
Validate AI-predicted kcat/Km values against literature experimental values.
Compares enzyme_kinetics.csv (AI predictions) with literature_kinetics.csv (experimental).
"""
import pandas as pd
import numpy as np

ai = pd.read_csv("data/processed/enzyme_kinetics.csv")
lit = pd.read_csv("data/external/literature_kinetics.csv")

print("=" * 80)
print("KINETICS VALIDATION: AI Predictions vs. Literature Experimental Values")
print("=" * 80)

# Cross-match by organism (partial) + specificity
results = []
for _, lrow in lit.iterrows():
    lit_org_parts = lrow["organism"].lower().split()
    # Use genus + species for matching
    if len(lit_org_parts) >= 2:
        search_term = lit_org_parts[0]  # genus
    else:
        search_term = lit_org_parts[0]
    
    lit_spec = lrow["specificity"]
    
    matches = ai[
        ai["organism"].str.lower().str.contains(search_term, na=False) &
        (ai["specificity"] == lit_spec)
    ]
    
    for _, arow in matches.iterrows():
        results.append({
            "accession": arow["accession"],
            "organism_ai": str(arow["organism"])[:45],
            "organism_lit": lrow["organism"],
            "specificity": lit_spec,
            "kcat_AI": arow["kcat"],
            "kcat_Lit": lrow["kcat"],
            "Km_AI": arow["Km"],
            "Km_Lit": lrow["Km"],
            "lit_ref": lrow["reference"],
        })

rdf = pd.DataFrame(results)

if len(rdf) > 0:
    # Drop exact duplicates
    rdf = rdf.drop_duplicates(subset=["accession", "organism_lit", "specificity"])
    
    rdf["kcat_ratio"] = rdf["kcat_AI"] / rdf["kcat_Lit"]
    rdf["Km_ratio"] = rdf["Km_AI"] / rdf["Km_Lit"]
    rdf["kcat_log2_fold"] = np.log2(rdf["kcat_ratio"])
    rdf["Km_log2_fold"] = np.log2(rdf["Km_ratio"])
    
    print(f"\nFound {len(rdf)} matching pairs\n")
    
    # Print comparison table
    cols = ["accession", "organism_lit", "specificity", 
            "kcat_AI", "kcat_Lit", "kcat_ratio",
            "Km_AI", "Km_Lit", "Km_ratio", "lit_ref"]
    
    for _, row in rdf.iterrows():
        print(f"  {row['accession']:12s} | {row['organism_lit']:30s} | {row['specificity']:18s}")
        print(f"    kcat: AI={row['kcat_AI']:8.2f}  Lit={row['kcat_Lit']:8.2f}  ratio={row['kcat_ratio']:.2f}")
        print(f"    Km:   AI={row['Km_AI']:8.4f}  Lit={row['Km_Lit']:8.4f}  ratio={row['Km_ratio']:.2f}")
        print(f"    Ref: {row['lit_ref']}")
        print()
    
    print("=" * 80)
    print("SUMMARY STATISTICS")
    print("=" * 80)
    print(f"\nTotal matched pairs: {len(rdf)}")
    print(f"\n--- kcat (AI/Literature) ---")
    print(f"  Mean ratio:   {rdf['kcat_ratio'].mean():.2f}")
    print(f"  Median ratio: {rdf['kcat_ratio'].median():.2f}")
    print(f"  Within 2x:    {((rdf['kcat_ratio'] >= 0.5) & (rdf['kcat_ratio'] <= 2.0)).sum()}/{len(rdf)} ({((rdf['kcat_ratio'] >= 0.5) & (rdf['kcat_ratio'] <= 2.0)).mean()*100:.0f}%)")
    print(f"  Within 5x:    {((rdf['kcat_ratio'] >= 0.2) & (rdf['kcat_ratio'] <= 5.0)).sum()}/{len(rdf)} ({((rdf['kcat_ratio'] >= 0.2) & (rdf['kcat_ratio'] <= 5.0)).mean()*100:.0f}%)")
    print(f"  Within 10x:   {((rdf['kcat_ratio'] >= 0.1) & (rdf['kcat_ratio'] <= 10.0)).sum()}/{len(rdf)} ({((rdf['kcat_ratio'] >= 0.1) & (rdf['kcat_ratio'] <= 10.0)).mean()*100:.0f}%)")
    
    print(f"\n--- Km (AI/Literature) ---")
    print(f"  Mean ratio:   {rdf['Km_ratio'].mean():.2f}")
    print(f"  Median ratio: {rdf['Km_ratio'].median():.2f}")
    print(f"  Within 2x:    {((rdf['Km_ratio'] >= 0.5) & (rdf['Km_ratio'] <= 2.0)).sum()}/{len(rdf)} ({((rdf['Km_ratio'] >= 0.5) & (rdf['Km_ratio'] <= 2.0)).mean()*100:.0f}%)")
    print(f"  Within 5x:    {((rdf['Km_ratio'] >= 0.2) & (rdf['Km_ratio'] <= 5.0)).sum()}/{len(rdf)} ({((rdf['Km_ratio'] >= 0.2) & (rdf['Km_ratio'] <= 5.0)).mean()*100:.0f}%)")
    print(f"  Within 10x:   {((rdf['Km_ratio'] >= 0.1) & (rdf['Km_ratio'] <= 10.0)).sum()}/{len(rdf)} ({((rdf['Km_ratio'] >= 0.1) & (rdf['Km_ratio'] <= 10.0)).mean()*100:.0f}%)")
    
    # Per-specificity analysis
    print(f"\n--- Per Specificity ---")
    for spec in rdf["specificity"].unique():
        sub = rdf[rdf["specificity"] == spec]
        print(f"\n  {spec} (n={len(sub)}):")
        print(f"    kcat AI range: {sub['kcat_AI'].min():.2f} - {sub['kcat_AI'].max():.2f}")
        print(f"    kcat Lit range: {sub['kcat_Lit'].min():.2f} - {sub['kcat_Lit'].max():.2f}")
        print(f"    Km AI range: {sub['Km_AI'].min():.4f} - {sub['Km_AI'].max():.4f}")
        print(f"    Km Lit range: {sub['Km_Lit'].min():.4f} - {sub['Km_Lit'].max():.4f}")
    
    # Overall AI dataset stats
    print(f"\n--- Overall AI Dataset Stats ---")
    print(f"  kcat range: {ai['kcat'].min():.2f} - {ai['kcat'].max():.2f} (mean={ai['kcat'].mean():.2f})")
    print(f"  Km range:   {ai['Km'].min():.4f} - {ai['Km'].max():.4f} (mean={ai['Km'].mean():.4f})")
    
    # Save results
    rdf.to_csv("reports/validation_results.csv", index=False)
    print(f"\nResults saved to reports/validation_results.csv")
else:
    print("No matches found between AI and Literature datasets")
