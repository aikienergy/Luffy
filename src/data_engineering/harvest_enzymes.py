"""
Purpose: Harvest enzyme data from OpenEnzymeDB and UniProt.
Overview: 2-stage fetch architecture:
  Stage 1: OED API → kcat, Km, UniProt ID (kinetic data)
  Stage 2: UniProt API → Amino acid sequence

Supports multiple EC numbers for EG, BG, and CBH enzyme classes.
"""
import requests
import pandas as pd
import time
import os
from datetime import datetime

# API Endpoints
OED_API = "https://openenzymedb-api.platform.moleculemaker.org/api/v1/data"
UNIPROT_API = "https://rest.uniprot.org/uniprotkb"

# Target enzyme classes
EC_TARGETS = {
    'eg': {
        'ec': '3.2.1.4',
        'limit': 100,
        'specificity': 'Cellulase',
        'description': 'Endoglucanase'
    },
    'bg': {
        'ec': '3.2.1.21',
        'limit': 50,
        'specificity': 'Beta-glucosidase',
        'description': 'Beta-glucosidase'
    },
    'cbh': {
        'ec': '3.2.1.91',
        'limit': 30,
        'specificity': 'Cellobiohydrolase',
        'description': 'Cellobiohydrolase (non-reducing end)'
    },
    'cbh2': {
        'ec': '3.2.1.176',
        'limit': 20,
        'specificity': 'Cellobiohydrolase',
        'description': 'Cellobiohydrolase (reducing end)'
    },
}

# === SUBSTRATE FILTERS ===
# Natural/standard substrates for each enzyme class
SUBSTRATE_FILTERS = {
    'Cellulase': ['cmc', 'cellulose', 'pasc', 'carboxymethyl', 'avicel', 'filter paper'],
    'Beta-glucosidase': ['cellobiose', 'glucose', 'sophorose', 'laminaribiose', 'gentiobiose'],
    'Cellobiohydrolase': ['avicel', 'filter paper', 'crystalline', 'pasc', 'cellulose', 'cellobiose']
}

# Synthetic substrates to exclude (artificial chromogenic/fluorogenic)
EXCLUDE_SUBSTRATE_PATTERNS = ['nitrophenyl', 'pnp', '4-np', 'fluorescent', 'methylumbelliferyl', 'muf']


def filter_by_substrate(records: list, specificity: str) -> list:
    """
    Filter OED records to include only natural substrates.
    Excludes synthetic substrates (pNP, MUF, etc.) that give artificially high kcat values.
    """
    if not records:
        return []
    
    allowed = SUBSTRATE_FILTERS.get(specificity, [])
    filtered = []
    
    for r in records:
        substrate = str(r.get('substrate', '')).lower()
        
        # Check if excluded (synthetic substrate)
        is_excluded = any(excl in substrate for excl in EXCLUDE_SUBSTRATE_PATTERNS)
        if is_excluded:
            continue
        
        # Check if allowed (natural substrate) or no substrate info
        is_allowed = not substrate or any(allow in substrate for allow in allowed)
        if is_allowed:
            filtered.append(r)
    
    return filtered


def fetch_from_oed(ec_number: str, limit: int = 100) -> list:
    """
    Fetch enzyme kinetic data from OpenEnzymeDB API.
    
    Args:
        ec_number: EC number (e.g., '3.2.1.4')
        limit: Maximum records to fetch
    
    Returns:
        List of enzyme data dictionaries
    """
    print(f"Fetching from OED: EC {ec_number} (limit={limit})...")
    
    params = {
        "ec": ec_number,
        "limit": limit
    }
    
    try:
        response = requests.get(OED_API, params=params, timeout=60)
        if response.status_code == 200:
            data = response.json()
            records = data.get("data", [])
            print(f"  → Retrieved {len(records)} records")
            return records
        else:
            print(f"  → Error: {response.status_code}")
            return []
    except Exception as e:
        print(f"  → Exception: {e}")
        return []


def fetch_sequence_from_uniprot(uniprot_id: str) -> str:
    """
    Fetch amino acid sequence from UniProt.
    
    Args:
        uniprot_id: UniProt accession (e.g., 'P07981')
    
    Returns:
        Amino acid sequence string or empty string if failed
    """
    if not uniprot_id or pd.isna(uniprot_id):
        return ""
    
    url = f"{UNIPROT_API}/{uniprot_id}.fasta"
    
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            lines = response.text.strip().split("\n")
            # Skip header line (starts with >)
            sequence = "".join(lines[1:])
            return sequence
        else:
            return ""
    except Exception:
        return ""


def fetch_from_uniprot_direct(ec_number: str, limit: int = 30) -> list:
    """
    Fallback: Fetch enzymes directly from UniProt when OED has no data.
    
    Args:
        ec_number: EC number (e.g., '3.2.1.91')
        limit: Maximum records to fetch
    
    Returns:
        List of enzyme data dictionaries
    """
    import io
    
    print(f"  → OED empty, fetching from UniProt directly...")
    
    base_url = "https://rest.uniprot.org/uniprotkb/search"
    query_str = f"(ec:{ec_number}) AND (reviewed:true)"
    params = {
        "query": query_str,
        "format": "tsv",
        "fields": "accession,id,organism_name,protein_name,sequence,ec",
        "size": str(limit)
    }
    
    try:
        response = requests.get(base_url, params=params, timeout=60)
        if response.status_code == 200:
            df = pd.read_csv(io.StringIO(response.text), sep='\t')
            
            # Convert to list of dicts with our schema
            records = []
            for _, row in df.iterrows():
                record = {
                    'uniprot': row.get('Entry', row.get('accession', '')),
                    'organism': row.get('Organism', row.get('organism_name', '')),
                    'substrate': 'cellulose',
                    'sequence': row.get('Sequence', row.get('sequence', '')),
                    'kcat_value': None,  # Will be filled by enrich
                    'km_value': None,    # Will be filled by enrich
                    'source_type': 'UniProt_Direct'
                }
                records.append(record)
            
            print(f"  → Retrieved {len(records)} from UniProt")
            return records
        else:
            print(f"  → UniProt error: {response.status_code}")
            return []
    except Exception as e:
        print(f"  → UniProt exception: {e}")
        return []


def harvest_all():
    """
    Main harvesting function. Fetches from OED and enriches with UniProt sequences.
    """
    print("=" * 60)
    print("LUFFY Data Engineering: Enzyme Harvester")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 60)
    
    all_data = []
    
    for key, config in EC_TARGETS.items():
        print(f"\n[{key.upper()}] {config['description']} (EC {config['ec']})")
        print("-" * 40)
        
        # Stage 1: Fetch from OED
        oed_records = fetch_from_oed(config['ec'], config['limit'])
        
        # Apply substrate filter to remove synthetic substrates (pNP, etc.)
        original_count = len(oed_records)
        oed_records = filter_by_substrate(oed_records, config['specificity'])
        filtered_count = original_count - len(oed_records)
        if filtered_count > 0:
            print(f"  → Filtered out {filtered_count} synthetic substrate records")
        
        # Fallback: If OED has no data, fetch from UniProt directly
        # Also supplement if OED count is below minimum threshold
        min_threshold = 50 if key == 'eg' else (20 if key == 'bg' else 10)
        
        if len(oed_records) == 0:
            oed_records = fetch_from_uniprot_direct(config['ec'], config['limit'])
            # UniProt direct already includes sequences
            for record in oed_records:
                record['specificity'] = config['specificity']
                record['ec_number'] = config['ec']
            all_data.extend(oed_records)
            continue
        elif len(oed_records) < min_threshold:
            # Supplement with UniProt data
            needed = min_threshold - len(oed_records) + 10  # Get extra
            print(f"  → OED has {len(oed_records)} < {min_threshold}, supplementing from UniProt...")
            supplement = fetch_from_uniprot_direct(config['ec'], needed)
            # Filter out duplicates by checking uniprot ID
            existing_ids = {r.get('uniprot', '') for r in oed_records}
            supplement = [r for r in supplement if r.get('uniprot', '') not in existing_ids]
            for record in supplement:
                record['specificity'] = config['specificity']
                record['ec_number'] = config['ec']
            oed_records.extend(supplement)
            print(f"  → After supplement: {len(oed_records)} records")
        
        # Stage 2: Enrich with UniProt sequences (for OED data)
        print(f"Fetching sequences from UniProt...")
        seq_count = 0
        
        for i, record in enumerate(oed_records):
            uniprot_id = record.get('uniprot', '')
            
            if uniprot_id:
                sequence = fetch_sequence_from_uniprot(uniprot_id)
                record['sequence'] = sequence
                if sequence:
                    seq_count += 1
                
                # Rate limiting
                if (i + 1) % 10 == 0:
                    print(f"  → Processed {i+1}/{len(oed_records)}")
                    time.sleep(0.5)
            else:
                record['sequence'] = ""
            
            # Add metadata
            record['specificity'] = config['specificity']
            record['ec_number'] = config['ec']
            record['source_type'] = 'OED'
        
        print(f"  → Sequences retrieved: {seq_count}/{len(oed_records)}")
        all_data.extend(oed_records)
    
    # Convert to DataFrame
    df = pd.DataFrame(all_data)
    
    # Standardize column names
    column_mapping = {
        'uniprot': 'accession',
        'kcat_value': 'kcat',
        'km_value': 'Km',
    }
    df = df.rename(columns=column_mapping)
    
    # Ensure substrate column exists
    if 'substrate' not in df.columns:
        df['substrate'] = 'unknown'
    
    # Deduplicate: Keep one entry per accession (prefer OED over UniProt_Direct)
    # Group by accession and take the median kcat/Km for entries with OED data
    if 'source_type' in df.columns:
        # Separate OED and UniProt_Direct entries
        df_oed = df[df['source_type'] == 'OED'].copy()
        df_uni = df[df['source_type'] == 'UniProt_Direct'].copy()
        
        # For OED: aggregate by accession (median of kinetics)
        if not df_oed.empty:
            numeric_cols = ['kcat', 'Km']
            agg_dict = {col: 'median' for col in numeric_cols if col in df_oed.columns}
            # Keep first for non-numeric columns
            first_cols = [c for c in df_oed.columns if c not in numeric_cols and c != 'accession']
            agg_dict.update({col: 'first' for col in first_cols})
            
            df_oed = df_oed.groupby('accession', as_index=False).agg(agg_dict)
        
        # Combine, preferring OED entries
        oed_ids = set(df_oed['accession'].tolist()) if not df_oed.empty else set()
        df_uni = df_uni[~df_uni['accession'].isin(oed_ids)]
        df = pd.concat([df_oed, df_uni], ignore_index=True)
        
        dedup_count = len(all_data) - len(df)
        if dedup_count > 0:
            print(f"\n  → Deduplicated {dedup_count} duplicate entries")
    
    # Add missing columns with defaults
    if 'Ki' not in df.columns:
        df['Ki'] = df['Km'] * 2  # Estimate Ki as 2x Km
    if 't_opt' not in df.columns:
        df['t_opt'] = 50.0
    if 'ph_opt' not in df.columns:
        df['ph_opt'] = 5.0
    if 'id' not in df.columns:
        df['id'] = df['accession']
    
    # Ensure output directory exists
    os.makedirs("data/raw", exist_ok=True)
    
    # Save
    output_file = "data/raw/oed_harvested.csv"
    df.to_csv(output_file, index=False)
    
    print("\n" + "=" * 60)
    print("HARVEST COMPLETE")
    print(f"Total records: {len(df)}")
    print(f"Output: {output_file}")
    print("\nClass distribution:")
    print(df['specificity'].value_counts().to_string())
    print("=" * 60)
    
    return df


if __name__ == "__main__":
    harvest_all()
