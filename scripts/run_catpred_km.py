"""
CatPred Km Prediction Runner
Directly calls catpred_predict without shell scripts.
Designed to run inside WSL catpred conda environment.
"""
import os
import sys
import pandas as pd
import numpy as np
from rdkit import Chem
import json
import gzip
import argparse

def prepare_input(input_csv, parameter):
    """Prepare and validate input CSV for CatPred."""
    df = pd.read_csv(input_csv)
    
    # Validate SMILES
    smiles_new = []
    for i, smi in enumerate(df['SMILES']):
        try:
            mol = Chem.MolFromSmiles(smi)
            smi_canon = Chem.MolToSmiles(mol)
            if parameter == 'kcat' and '.' in smi_canon:
                smi_canon = '.'.join(sorted(smi_canon.split('.')))
            smiles_new.append(smi_canon)
        except:
            print(f"Invalid SMILES at row {i}, using original")
            smiles_new.append(smi)
    
    df['SMILES'] = smiles_new
    
    # Validate sequences
    valid_aas = set('ACDEFGHIKLMNPQRSTVWY')
    for i, seq in enumerate(df['sequence']):
        if not set(str(seq)).issubset(valid_aas):
            print(f"Warning: Invalid amino acid in sequence at row {i}")
    
    # Add pdbpath if missing (required by create_pdbrecords)
    if 'pdbpath' not in df.columns:
        df['pdbpath'] = [f"seq_{i}" for i in range(len(df))]
    
    # Save prepared input
    prepared_path = input_csv.replace('.csv', '_prepared.csv')
    df.to_csv(prepared_path, index=False)
    
    # Create protein records JSON
    records_path = prepared_path.replace('.csv', '.json.gz')
    dic_full = {}
    for _, row in df.iterrows():
        dic = {'name': row['pdbpath'], 'seq': row['sequence']}
        dic_full[row['pdbpath']] = dic
    
    with gzip.open(records_path, 'wb') as f:
        f.write(json.dumps(dic_full).encode('utf-8'))
    
    print(f"Prepared {len(df)} records")
    print(f"Input: {prepared_path}")
    print(f"Records: {records_path}")
    return prepared_path, records_path


def run_prediction(prepared_csv, records_path, checkpoint_dir, parameter):
    """Run CatPred prediction directly via Python API."""
    from catpred.train import catpred_predict
    from catpred.args import PredictArgs
    
    output_path = prepared_csv.replace('_prepared.csv', '_output.csv')
    
    # Set CPU mode
    os.environ['PROTEIN_EMBED_USE_CPU'] = '1'
    
    # Build prediction arguments
    predict_args = [
        '--test_path', prepared_csv,
        '--preds_path', output_path,
        '--checkpoint_dir', checkpoint_dir,
        '--uncertainty_method', 'mve',
        '--smiles_column', 'SMILES',
        '--individual_ensemble_predictions',
        '--protein_records_path', records_path,
    ]
    
    args = PredictArgs().parse_args(predict_args)
    
    print(f"\nRunning CatPred prediction for {parameter}...")
    print(f"Checkpoint: {checkpoint_dir}")
    print(f"Output: {output_path}")
    
    catpred_predict(args)
    
    return output_path


def process_results(output_path, parameter, accession_map):
    """Process CatPred output and extract Km predictions."""
    df = pd.read_csv(output_path)
    
    if parameter == 'km':
        target_col = 'log10km_mean'
        unit = 'mM'
    elif parameter == 'kcat':
        target_col = 'log10kcat_max'
        unit = '1/s'
    else:
        target_col = 'log10ki_mean'
        unit = 'mM'
    
    predictions = []
    for _, row in df.iterrows():
        prediction_log = row.get(target_col, None)
        if prediction_log is not None and not pd.isna(prediction_log):
            prediction_linear = 10 ** prediction_log
        else:
            prediction_linear = None
        
        predictions.append({
            'prediction_log10': prediction_log,
            f'Prediction_({unit})': prediction_linear,
        })
    
    pred_df = pd.DataFrame(predictions)
    result = pd.concat([df, pred_df], axis=1)
    
    # Add back accession info
    if accession_map:
        result['accession'] = accession_map
    
    final_path = output_path.replace('_output.csv', '_final.csv')
    result.to_csv(final_path, index=False)
    
    print(f"\nResults saved to: {final_path}")
    print(f"Predictions range: {pred_df[f'Prediction_({unit})'].min():.4f} - {pred_df[f'Prediction_({unit})'].max():.4f} {unit}")
    print(f"Mean: {pred_df[f'Prediction_({unit})'].mean():.4f} {unit}")
    
    return result


def main():
    parser = argparse.ArgumentParser(description="CatPred Km Prediction Runner")
    parser.add_argument("--input", required=True, help="Input CSV with SMILES, sequence, accession")
    parser.add_argument("--checkpoint_dir", required=True, help="Path to Km checkpoint directory")
    parser.add_argument("--parameter", default="km", choices=["kcat", "km", "ki"])
    args = parser.parse_args()
    
    print("=" * 60)
    print("CatPred Km Prediction Runner")
    print("=" * 60)
    
    # Read accession list before prepare step modifies it
    input_df = pd.read_csv(args.input)
    accession_map = input_df.get('accession', pd.Series()).tolist()
    
    # Step 1: Prepare input
    prepared_csv, records_path = prepare_input(args.input, args.parameter)
    
    # Step 2: Run prediction
    output_path = run_prediction(prepared_csv, records_path, args.checkpoint_dir, args.parameter)
    
    # Step 3: Process results
    result = process_results(output_path, args.parameter, accession_map)
    
    print("\n" + "=" * 60)
    print("PREDICTION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
