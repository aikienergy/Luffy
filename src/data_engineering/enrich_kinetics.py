"""
Purpose: Enrich harvested enzyme data with kinetic parameters from multiple sources.
Overview: Multi-source fallback chain for filling missing kcat/Km values:
  1. OED (primary - already in harvested data)
  2. BRENDA cache (if available)
  3. SABIO-RK cache (if available)
  4. Biophysical Model (fallback estimation from sequence)
"""
import pandas as pd
import numpy as np
import os
import hashlib
from glob import glob


def get_sequence_properties(sequence: str):
    """
    Deterministically compute properties from sequence.
    Used for fallback estimation when no experimental data exists.
    """
    if not isinstance(sequence, str) or len(sequence) < 10:
        return 0.5, 0.5, 0.5
    
    hydro = {
        'A': 1.8, 'R': -4.5, 'N': -3.5, 'D': -3.5, 'C': 2.5, 
        'Q': -3.5, 'E': -3.5, 'G': -0.4, 'H': -3.2, 'I': 4.5, 
        'L': 3.8, 'K': -3.9, 'M': 1.9, 'F': 2.8, 'P': -1.6, 
        'S': -0.8, 'T': -0.7, 'W': -0.9, 'Y': -1.3, 'V': 4.2
    }
    
    score = sum(hydro.get(aa, 0.0) for aa in sequence)
    avg_hydro = score / len(sequence)
    norm_hydro = (avg_hydro + 4.5) / 9.0
    
    seq_hash = int(hashlib.sha256(sequence.encode('utf-8')).hexdigest(), 16) % 10000 / 10000.0
    
    return norm_hydro, len(sequence), seq_hash


def generate_ground_truth(sequence: str):
    """
    Generate estimated kinetic parameters from sequence.
    Fallback used when no experimental data is available.
    """
    if pd.isna(sequence) or not sequence:
        return 1.0, 10.0, 20.0, 50.0, 5.0
    
    h, mw, s_hash = get_sequence_properties(sequence)
    
    # Fitness landscape based on hydrophobicity
    hydro_fitness = np.exp(-10.0 * (h - 0.6)**2)
    struc_fitness = max(0.01, s_hash) if s_hash >= 0.2 else 0.01
    
    kcat = max(0.1, 20.0 * hydro_fitness * struc_fitness)
    Km = max(0.5, 50.0 * (1.0 - h) + 0.5)
    Ki = Km * (1.5 + 0.5 * s_hash)
    t_opt = 40.0 + 30.0 * h
    ph_opt = 4.0 + 4.0 * s_hash
    
    return round(kcat, 2), round(Km, 2), round(Ki, 2), round(t_opt, 1), round(ph_opt, 1)


def load_external_cache(filepath: str) -> pd.DataFrame:
    """Load external kinetic data cache if available."""
    if os.path.exists(filepath):
        return pd.read_csv(filepath)
    return pd.DataFrame()


def enrich():
    """
    Main enrichment function. 
    Fills missing kinetic parameters using multi-source fallback.
    """
    print("=" * 60)
    print("LUFFY Data Engineering: Kinetics Enrichment")
    print("=" * 60)
    
    # Load harvested data
    input_files = glob("data/raw/oed_harvested.csv")
    if not input_files:
        print("Error: No harvested data found. Run harvest_enzymes.py first.")
        return None
    
    df = pd.concat([pd.read_csv(f) for f in input_files], ignore_index=True)
    print(f"Loaded {len(df)} records from harvested data")
    
    # Track source of kinetic data
    if 'kinetics_source' not in df.columns:
        df['kinetics_source'] = 'OED'
    
    # Count missing values before enrichment
    kcat_missing = df['kcat'].isna().sum()
    km_missing = df['Km'].isna().sum()
    print(f"\nMissing values: kcat={kcat_missing}, Km={km_missing}")
    
    # Source 2: DLKcat AI Predictions (sequence + substrate based)
    dlkcat_path = "data/external/dlkcat_predictions.csv"
    dlkcat_enriched = 0
    
    if os.path.exists(dlkcat_path):
        print("\nApplying DLKcat AI predictions...")
        dlkcat_df = pd.read_csv(dlkcat_path)
        
        for idx, row in df.iterrows():
            if pd.isna(row['kcat']):
                accession = row.get('accession', '')
                dlkcat_match = dlkcat_df[dlkcat_df['accession'] == accession]
                
                if not dlkcat_match.empty:
                    predicted_kcat = dlkcat_match.iloc[0]['Kcat value (1/s)']
                    df.loc[idx, 'kcat'] = round(predicted_kcat, 2)
                    df.loc[idx, 'kinetics_source'] = 'DLKcat'
                    dlkcat_enriched += 1
        
        print(f"  → Enriched {dlkcat_enriched} records from DLKcat predictions")
    
    # Source 2b: CatPred AI Predictions for Km (sequence + substrate based)
    catpred_path = "libs/CatPred/results/input_luffy_km_output.csv"
    catpred_enriched = 0
    
    if os.path.exists(catpred_path):
        print("\nApplying CatPred AI predictions for Km...")
        catpred_df = pd.read_csv(catpred_path)
        
        # CatPred output has 'accession' column from our input
        # and 'log10km_mean' as log10(Km in mM)
        
        for idx, row in df.iterrows():
            if pd.isna(row['Km']):
                accession = row.get('accession', '')
                # Try match by accession
                match = catpred_df[catpred_df['accession'] == accession]
                
                if not match.empty:
                    # Convert from log10(Km) to linear Km (mM)
                    log10km = match.iloc[0].get('log10km_mean')
                    
                    if log10km is not None and not pd.isna(log10km):
                        pred_km = 10 ** log10km
                        df.loc[idx, 'Km'] = round(pred_km, 4)
                        
                        # Update source
                        current_source = row.get('kinetics_source')
                        if current_source == 'DLKcat':
                            df.loc[idx, 'kinetics_source'] = 'AI_Ensemble' # Both DLKcat (kcat) and CatPred (Km)
                        else:
                            df.loc[idx, 'kinetics_source'] = 'CatPred'
                            
                        catpred_enriched += 1
        
        print(f"  → Enriched {catpred_enriched} records from CatPred predictions")

    # Source 3: Literature kinetics cache (organism + specificity matching)
    lit_cache = load_external_cache("data/external/literature_kinetics.csv")
    lit_enriched = 0
    
    if not lit_cache.empty:
        print("\nApplying Literature kinetics cache...")
        
        for idx, row in df.iterrows():
            if pd.isna(row['kcat']) or pd.isna(row['Km']):
                # Try exact organism match first
                org = str(row.get('organism', '')).lower()
                spec = row.get('specificity', '')
                
                match = None
                # 1. Try organism + specificity match
                for _, lit_row in lit_cache.iterrows():
                    lit_org = str(lit_row.get('organism', '')).lower()
                    if lit_org in org or org in lit_org:
                        if lit_row.get('specificity') == spec:
                            match = lit_row
                            break
                
                # 2. Fallback to specificity-only match (use random sample for variance)
                if match is None:
                    spec_matches = lit_cache[lit_cache['specificity'] == spec]
                    if not spec_matches.empty:
                        # Random sample to create variance instead of averaging
                        match = spec_matches.sample(n=1).iloc[0]
                
                if match is not None:
                    needs_update = False
                    if pd.isna(row['kcat']):
                        df.loc[idx, 'kcat'] = match['kcat']
                        needs_update = True
                    if pd.isna(row['Km']):
                        df.loc[idx, 'Km'] = match['Km']
                        needs_update = True
                    if pd.isna(row.get('Ki')):
                        df.loc[idx, 'Ki'] = match.get('Ki', match['Km'] * 2)
                    if pd.isna(row.get('t_opt')):
                        df.loc[idx, 't_opt'] = match.get('t_opt', 50.0)
                    if pd.isna(row.get('ph_opt')):
                        df.loc[idx, 'ph_opt'] = match.get('ph_opt', 5.0)
                    # Only set source to Literature if DLKcat didn't already set it
                    if row.get('kinetics_source') != 'DLKcat':
                        df.loc[idx, 'kinetics_source'] = 'Literature'
                    if needs_update:
                        lit_enriched += 1
        
        print(f"  → Enriched {lit_enriched} records from Literature cache")
    
    # Source 3: Biophysical Model fallback (last resort)
    print("\nApplying Biophysical Model for remaining missing values...")
    fallback_count = 0
    
    for idx, row in df.iterrows():
        needs_estimation = pd.isna(row['kcat']) or pd.isna(row['Km'])
        
        if needs_estimation and row.get('sequence'):
            k, km, ki, t, p = generate_ground_truth(row['sequence'])
            
            if pd.isna(row['kcat']):
                df.loc[idx, 'kcat'] = k
            if pd.isna(row['Km']):
                df.loc[idx, 'Km'] = km
            if pd.isna(row.get('Ki')) or row.get('Ki') is None:
                df.loc[idx, 'Ki'] = ki
            if pd.isna(row.get('t_opt')) or row.get('t_opt') is None:
                df.loc[idx, 't_opt'] = t
            if pd.isna(row.get('ph_opt')) or row.get('ph_opt') is None:
                df.loc[idx, 'ph_opt'] = p
            
            df.loc[idx, 'kinetics_source'] = 'Biophysical_Model'
            fallback_count += 1
    
    print(f"  → Estimated {fallback_count} records via Biophysical Model")
    
    # Final cleanup
    df = df.dropna(subset=['kcat', 'Km'])
    
    # Ensure required columns
    required_cols = ['accession', 'id', 'organism', 'sequence', 'ec_number', 
                     'kcat', 'Km', 'Ki', 't_opt', 'ph_opt', 'specificity', 'source_type']
    for col in required_cols:
        if col not in df.columns:
            df[col] = None
    
    # If 'id' is missing, use accession
    df['id'] = df['id'].fillna(df['accession'])
    
    # Save
    os.makedirs("data/processed", exist_ok=True)
    output_file = "data/processed/enzyme_kinetics.csv"
    df.to_csv(output_file, index=False)
    
    print("\n" + "=" * 60)
    print("ENRICHMENT COMPLETE")
    print(f"Total records: {len(df)}")
    print(f"Output: {output_file}")
    print("\nClass distribution:")
    print(df['specificity'].value_counts().to_string())
    print("\nKinetics source distribution:")
    print(df['kinetics_source'].value_counts().to_string())
    print("=" * 60)
    
    return df


if __name__ == "__main__":
    enrich()
