"""
Purpose: Protein Feature Engineering.
Overview: Generates numerical embedding vectors for enzyme sequences using ESM-2 (8M parameter model).
"""
import pandas as pd
import numpy as np
import os
import torch
from transformers import EsmTokenizer, EsmModel

def generate_features():
    input_file = "data/processed/enzyme_kinetics.csv"
    output_file = "data/processed/enzyme_features.csv"
    
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return

    df = pd.read_csv(input_file)
    sequences = df['sequence'].tolist()
    ids = df['id'].tolist()
    
    print(f"Loading ESM-2 Model (facebook/esm2_t6_8M_UR50D)...")
    try:
        tokenizer = EsmTokenizer.from_pretrained("facebook/esm2_t6_8M_UR50D")
        model = EsmModel.from_pretrained("facebook/esm2_t6_8M_UR50D")
    except Exception as e:
        print(f"Error loading model: {e}")
        print("Please ensure 'transformers' and 'torch' are installed.")
        return

    print(f"Generating features for {len(sequences)} enzymes...")
    
    embeddings = []
    
    # Process in batches or single loop
    model.eval()
    
    # Check for GPU
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    print(f"Inference running on: {device}")
    
    with torch.no_grad():
        for i, seq in enumerate(sequences):
            if pd.isna(seq) or len(seq) < 5:
                # Handle invalid sequences with zero vector
                embeddings.append(np.zeros(320)) 
                continue
                
            # Tokenize
            inputs = tokenizer(seq, return_tensors="pt", truncation=True, max_length=1024)
            inputs = {k: v.to(device) for k, v in inputs.items()}
            
            # Forward pass
            outputs = model(**inputs)
            
            # Get mean embedding (excluding special tokens? simple mean is fine for now)
            # last_hidden_state: [batch, len, dim=320]
            # Mean over sequence length dimension
            seq_embedding = outputs.last_hidden_state.mean(dim=1).cpu().numpy()[0]
            
            embeddings.append(seq_embedding)
            
            if (i+1) % 10 == 0:
                print(f"Processed {i+1}/{len(sequences)}")
    
    # Stack features
    features_arr = np.vstack(embeddings)
    dim = features_arr.shape[1]
    
    # Create DataFrame
    feat_df = pd.DataFrame(features_arr, columns=[f"dim_{j}" for j in range(dim)])
    feat_df.insert(0, 'id', ids)
    
    # Save
    feat_df.to_csv(output_file, index=False)
    print(f"Saved ESM-2 enzyme features (dim={dim}) to {output_file}")

if __name__ == "__main__":
    generate_features()
