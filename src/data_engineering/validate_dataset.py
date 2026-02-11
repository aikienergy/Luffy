"""
Purpose: Validate enzyme kinetics dataset quality.
Overview: Performs quality checks on the processed dataset:
  - Class balance (EG/BG/CBH distribution)
  - Missing value analysis
  - Quality gates for minimum counts
  - Generates QA report
"""
import pandas as pd
import os
from datetime import datetime


def validate():
    """
    Main validation function.
    Checks dataset quality and generates report.
    """
    print("=" * 60)
    print("LUFFY Data Engineering: Dataset Validation")
    print("=" * 60)
    
    input_file = "data/processed/enzyme_kinetics.csv"
    
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found. Run enrich_kinetics.py first.")
        return False
    
    df = pd.read_csv(input_file)
    print(f"Loaded {len(df)} records")
    
    report = []
    report.append(f"# Dataset Quality Report")
    report.append(f"\nGenerated: {datetime.now().isoformat()}")
    report.append(f"\n## Summary")
    report.append(f"\n- Total records: {len(df)}")
    
    # 1. Class Distribution
    report.append(f"\n## Class Distribution")
    counts = df['specificity'].value_counts()
    report.append(f"\n| Specificity | Count |")
    report.append(f"|:---|---:|")
    for spec, count in counts.items():
        report.append(f"| {spec} | {count} |")
    
    # 2. Missing Values
    report.append(f"\n## Missing Values")
    missing = df.isnull().sum()
    important_cols = ['accession', 'sequence', 'kcat', 'Km', 'Ki', 't_opt', 'ph_opt']
    report.append(f"\n| Column | Missing |")
    report.append(f"|:---|---:|")
    for col in important_cols:
        if col in missing:
            report.append(f"| {col} | {missing[col]} |")
    
    # 3. Quality Gates
    report.append(f"\n## Quality Gates")
    
    bg_count = len(df[df['specificity'] == 'Beta-glucosidase'])
    cbh_count = len(df[df['specificity'] == 'Cellobiohydrolase'])
    eg_count = len(df[df['specificity'] == 'Cellulase'])
    
    gates = [
        ("BG >= 20", bg_count >= 20, bg_count),
        ("CBH >= 10", cbh_count >= 10, cbh_count),
        ("EG >= 50", eg_count >= 50, eg_count),
        ("No missing kcat", df['kcat'].isna().sum() == 0, df['kcat'].isna().sum()),
        ("No missing Km", df['Km'].isna().sum() == 0, df['Km'].isna().sum()),
    ]
    
    report.append(f"\n| Check | Status | Value |")
    report.append(f"|:---|:---:|---:|")
    
    all_passed = True
    for check_name, passed, value in gates:
        status = "✅" if passed else "❌"
        report.append(f"| {check_name} | {status} | {value} |")
        if not passed:
            all_passed = False
    
    # 4. Data Source Distribution
    if 'kinetics_source' in df.columns:
        report.append(f"\n## Kinetics Source")
        source_counts = df['kinetics_source'].value_counts()
        report.append(f"\n| Source | Count |")
        report.append(f"|:---|---:|")
        for src, count in source_counts.items():
            report.append(f"| {src} | {count} |")
    
    # Save report
    os.makedirs("reports", exist_ok=True)
    report_file = "reports/dataset_qa.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write("\n".join(report))
    
    print(f"\nReport saved: {report_file}")
    print("\n" + "\n".join(report[-15:]))
    
    if all_passed:
        print("\n✅ All quality gates PASSED")
    else:
        print("\n❌ Some quality gates FAILED - review report")
    
    return all_passed


if __name__ == "__main__":
    validate()
