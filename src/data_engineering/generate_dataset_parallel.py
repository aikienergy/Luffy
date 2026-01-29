"""
Purpose: Scalable Training Data Generation using Parallel Processing.
Overview: Runs batch simulations in parallel (multi-core) to handle large grids (e.g. 7500+ simulations) efficiently.
"""
import pandas as pd
import numpy as np
import os
import sys
from joblib import Parallel, delayed
import time

# Add src to path to import validator
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from src.validation.validator import EnzymeValidator

def simulate_single_condition(row, temp, ph, substrate, activity_map, enzyme_conc_gL=1e-5, duration=24*3600):
    """
    Worker function for a single simulation.
    Must be standalone for pickling.
    """
    try:
        # Re-instantiate validator inside worker to avoid Roadrunner pickling issues
        # (Roadrunner objects are C++ pointers, often not pickleable)
        val_local = EnzymeValidator()
        
        eid = row['id']
        kcat_base = row['kcat']
        Km_base = row['Km'] 
        spec_type = row.get('specificity', 'Other')
        ki = row['Ki']
        t_opt = row['t_opt']
        ph_opt = row['ph_opt']
        
        eff = activity_map.get(spec_type, {}).get(substrate, 0.05)
        kcat_eff_sub = kcat_base * eff
        
        t, y = val_local.run_kinetic_simulation(
            kcat=kcat_eff_sub, Km=Km_base, 
            substrate_conc_init=100.0,
            enzyme_conc=enzyme_conc_gL,
            duration=duration, 
            temp=temp, ph=ph, ki=ki,
            t_opt=t_opt, ph_opt=ph_opt
        )
        
        if y is not None:
            p_final = y[-1, 1]
            yield_val = p_final / 100.0
            
            return {
                'id': eid,
                'temp': temp,
                'ph': ph,
                'substrate': substrate,
                'yield': round(yield_val, 4),
                'kcat_base': kcat_base,
                'Km_base': Km_base,
                'enzyme_type': spec_type
            }
    except Exception as e:
        # print(f"Error in {eid}: {e}")
        return None
    return None

def generate_dataset_parallel():
    input_kinetics = "data/processed/enzyme_kinetics.csv"
    output_file = "data/processed/training_dataset.csv"
    
    if not os.path.exists(input_kinetics):
        print("Error: Kinetics file not found.")
        return

    df_enz = pd.read_csv(input_kinetics)
    print(f"Loaded {len(df_enz)} enzymes.")
    
    # FULL GRID
    temps = [30.0, 40.0, 50.0, 60.0, 70.0] # 5 temps
    phs = [4.0, 5.0, 6.0, 7.0, 8.0]        # 5 pHs
    substrates = ['Cellulose', 'Xylan', 'Bagasse'] # 3 subs
    
    activity_map = {
        'Cellulase': {'Cellulose': 1.0, 'Xylan': 0.1, 'Bagasse': 0.70},
        'Xylanase':  {'Cellulose': 0.1, 'Xylan': 1.0, 'Bagasse': 0.40},
        'Other':     {'Cellulose': 0.05, 'Xylan': 0.05, 'Bagasse': 0.05}
    }
    
    tasks = []
    print(f"Generating tasks for {len(df_enz)} enzymes x {len(temps)} temps x {len(phs)} pHs x {len(substrates)} substrates.")
    
    for idx, row in df_enz.iterrows():
        for sub in substrates:
            for temp in temps:
                for ph in phs:
                    tasks.append((row, temp, ph, sub))
                    
    total_tasks = len(tasks)
    print(f"Total Simulations: {total_tasks}")
    
    print("Starting Parallel Execution (n_jobs=-1)...")
    start_time = time.time()
    
    # Execute in parallel
    results = Parallel(n_jobs=-1, verbose=5)(
        delayed(simulate_single_condition)(row, t, p, s, activity_map) for row, t, p, s in tasks
    )
    
    # Filter None
    valid_results = [r for r in results if r is not None]
    
    end_time = time.time()
    duration = end_time - start_time
    print(f"Completed in {duration:.1f} seconds. ({len(valid_results)} valid results out of {total_tasks})")
    
    df_res = pd.DataFrame(valid_results)
    df_res.to_csv(output_file, index=False)
    print(f"Saved dataset to {output_file}")

if __name__ == "__main__":
    generate_dataset_parallel()
