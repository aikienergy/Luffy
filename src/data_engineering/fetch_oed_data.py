"""
Purpose: Fetch source enzyme data from UniProt.
Overview: connecting to UniProt API to download real Cellulase (EC 3.2.1.4) entries. Saves to data/raw/oed_100.csv.
"""
import requests
import pandas as pd
import io

def fetch_oed_cellulases(output_file):
    print("Connecting to UniProt API to fetch Real Cellulases (EC 3.2.1.4)...")
    
    # Query: EC 3.2.1.4 (Cellulase), Reviewed (Swiss-Prot), limit 100
    base_url = "https://rest.uniprot.org/uniprotkb/search"
    query_str = "(ec:3.2.1.4) AND (reviewed:true)"
    params = {
        "query": query_str,
        "format": "tsv",
        "fields": "accession,id,organism_name,protein_name,sequence,ec",
        "size": "100"
    }
    
    print(f"Requesting {base_url} with params={params}")
    try:
        response = requests.get(base_url, params=params, timeout=30)
        print(f"Response URL: {response.url}")
        if response.status_code == 200:
            # Parse TSV
            df = pd.read_csv(io.StringIO(response.text), sep='\t')
            
            # Rename columns to match our system
            df = df.rename(columns={
                'Entry': 'accession',
                'Entry Name': 'id',
                'Organism': 'organism',
                'Protein names': 'name',
                'Sequence': 'sequence',
                'EC number': 'ec_number'
            })
            
            print(f"Fetched {len(df)} entries.")
            
            # Limit to 100
            df = df.head(100)
            
            # Add Source tag
            df['source'] = 'UniProt_Real'
            
            # Save
            df.to_csv(output_file, index=False)
            print(f"Saved real enzyme list to {output_file}")
            # print(df[['id', 'organism']].head())
            return True
        else:
            print(f"API Error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"Connection Error: {e}")
        return False

if __name__ == "__main__":
    fetch_oed_cellulases("data/raw/oed_100.csv")
