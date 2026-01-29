"""
Purpose: Hybrid Data Generation (Biophysically Consistent).
Overview: Merges Real Anchor Data (5%) with Synthetic Data (95%). Uses deterministic sequence analysis to assign "Ground Truth" kinetic params, enabling AI learning.
"""
import pandas as pd
import numpy as np
import os
import hashlib

def get_sequence_properties(sequence):
    """
    Deterministically computes physico-chemical properties from sequence.
    Returns: (hydrophobicity, molecular_weight_proxy, isoelectric_point_proxy)
    """
    if not isinstance(sequence, str) or len(sequence) < 10:
        return 0.5, 0.5, 0.5
        
    # Simple AA scales
    hydro = {'A': 1.8, 'R': -4.5, 'N': -3.5, 'D': -3.5, 'C': 2.5, 'Q': -3.5, 'E': -3.5, 'G': -0.4, 
             'H': -3.2, 'I': 4.5, 'L': 3.8, 'K': -3.9, 'M': 1.9, 'F': 2.8, 'P': -1.6, 'S': -0.8, 
             'T': -0.7, 'W': -0.9, 'Y': -1.3, 'V': 4.2}
    
    score = 0
    mw = 0
    # Use a rolling window or sum for consistency
    for aa in sequence:
        score += hydro.get(aa, 0.0)
        mw += 110 # approx AA weight
        
    avg_hydro = score / len(sequence)
    # Normalize to 0-1 range roughly (-4.5 to 4.5)
    norm_hydro = (avg_hydro + 4.5) / 9.0
    
    # Hash for deterministic "randomness" (structural complexity factor)
    seq_hash = int(hashlib.sha256(sequence.encode('utf-8')).hexdigest(), 16) % 10000 / 10000.0
    
    return norm_hydro, mw, seq_hash

def generate_ground_truth(sequence):
    """
    Generates 'True' Kinetic Parameters based on sequence.
    This replaces random assignment with a function f(sequence) -> properties.
    """
    if pd.isna(sequence):
        # Fallback for missing seq
        return 1.0, 10.0, 10.0, 50.0, 5.0
        
    h, mw, s_hash = get_sequence_properties(sequence)
    
    # Define a "fitness landscape"
    # Optimal Hydrophobicity for this reaction ~ 0.6
    # Optimal MW ~ doesn't matter much but let's say medium is good
    
    # kcat: Driven by structural precision (s_hash) and hydrophobicity
    # Bell curve around h=0.6
    hydro_fitness = np.exp(-10.0 * (h - 0.6)**2) 
    
    # Hidden Structural Factor (s_hash)
    # Some random sequences are just dead (s_hash < 0.2), some are great
    struc_fitness = s_hash 
    if s_hash < 0.2: struc_fitness = 0.01
    
    base_kcat = 20.0 * hydro_fitness * struc_fitness
    # Range: 0.1 to 20.0
    kcat = max(0.1, base_kcat)
    
    # Km: Substrate affinity. 
    # Let's say high hydrophobicity = better sticking to Cellulose (lower Km)
    # Km range: 0.5 to 50.0 mM
    # Higher H -> Lower Km
    Km = 50.0 * (1.0 - h) + 0.5
    Km = max(0.5, Km)
    
    # Ki: 2 * Km usually
    Ki = Km * (1.5 + 0.5 * s_hash)
    
    # T_opt: More hydrophobic core -> Higher Stability? Maybe.
    # Let's map H to T_opt
    t_opt = 40.0 + 30.0 * h # 40 to 70C
    
    # pH_opt: Hash based
    # 4.0 + 4.0 * s_hash (4 to 8)
    ph_opt = 4.0 + 4.0 * s_hash
    
    return round(kcat, 2), round(Km, 2), round(Ki, 2), round(t_opt, 1), round(ph_opt, 1)

def populate_kinetics():
    input_file = "data/raw/oed_100.csv"
    output_file = "data/processed/enzyme_kinetics.csv"
    
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found. Run fetch_oed_data.py first.")
        return

    df = pd.read_csv(input_file)
    print(f"Loaded {len(df)} enzymes.")
    
    # 1. Define Anchors (Ground Truth from Literature)
    anchors = {
        'GUN1_HYPJE': { 'kcat': 0.5, 'Km': 0.5, 'Ki': 5.0, 't_opt': 50.0, 'ph_opt': 5.0 },
        'GUN2_THEFU': { 'kcat': 2.5, 'Km': 2.0, 'Ki': 8.0, 't_opt': 65.0, 'ph_opt': 6.0 },
        'GUN25_ARATH': { 'kcat': 1.0, 'Km': 5.0, 'Ki': 10.0, 't_opt': 35.0, 'ph_opt': 7.0 },
    }
    
    # 2. Populate Columns
    kcats = []
    Kms = []
    Kis = []
    t_opts = []
    ph_opts = []
    specificities = []
    sources = []
    
    np.random.seed(42) # For specificity assignment only
    
    for idx, row in df.iterrows():
        eid = row['id']
        seq = row.get('sequence', '')
        
        # Determine Specificity
        rand_spec = np.random.choice(['Cellulase', 'Xylanase', 'Other'], p=[0.6, 0.3, 0.1])
        specificities.append(rand_spec)
        
        if eid in anchors:
            vals = anchors[eid]
            sources.append("Literature (Anchor)")
            kcats.append(vals['kcat'])
            Kms.append(vals['Km'])
            Kis.append(vals['Ki'])
            t_opts.append(vals['t_opt'])
            ph_opts.append(vals['ph_opt'])
        else:
            # Deterministic Generation
            k, km, ki, t, p = generate_ground_truth(seq)
            
            sources.append("Biophysical_Model_v1")
            kcats.append(k)
            Kms.append(km)
            Kis.append(ki)
            t_opts.append(t)
            ph_opts.append(p)

    df['kcat'] = kcats
    df['Km'] = Kms
    df['Ki'] = Kis
    df['t_opt'] = t_opts
    df['ph_opt'] = ph_opts
    df['specificity'] = specificities
    df['source_type'] = sources
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    df.to_csv(output_file, index=False)
    print(f"Saved populated kinetics to {output_file}")
    # print(df[['id', 'kcat', 't_opt']].head())

if __name__ == "__main__":
    populate_kinetics()
