"""
Purpose: Validation script for designed enzymes.
Overview: Loads the AI-designed enzyme parameters and runs a verification simulation to confirm yield improvements against baseline.
"""
from src.validation.validator import EnzymeValidator
import numpy as np

def run_validation_demo():
    print("Initializing Validation Engine (Tellurium)...")
    try:
        validator = EnzymeValidator()
    except Exception as e:
        print(f"Failed to initialize Validator: {e}")
        return

    # --- Scenario 1: Inverse AI proposes a design ---
    # Mock output from AI
    proposed_kcat = 15.0  # 1/s
    proposed_Km = 0.5     # mM
    proposed_embedding = [0.1, -0.5, 0.8, 0.2] # Mock vector
    
    print(f"\n[1] Checking Structure Validity...")
    is_valid, score = validator.check_structure_validity(proposed_embedding)
    print(f"Structure Score (pLDDT mock): {score:.2f}")
    
    # --- Scenario 2: Simulation ---
    print(f"\n[2] Running Kinetic Simulation (Tellurium)...")
    print(f"Parameters: kcat={proposed_kcat}, Km={proposed_Km}")
    
    substrate_init = 100.0 # mM
    
    try:
        # Simulate 24 hours (in seconds), [E] = 0.1 mM
        duration_sec = 24 * 60 * 60
        time_points, results = validator.run_kinetic_simulation(proposed_kcat, proposed_Km, substrate_init, duration=duration_sec, enzyme_conc=1e-4)
        
        final_yield = results[-1, 1] # Product at last step (assuming col 1 is P)
        print(f"Simulation completed.")
        print(f"Initial Substrate: {substrate_init} mM")
        print(f"Final Product (24h): {final_yield:.2f} mM")
        
        target_yield = 80.0
        if final_yield >= target_yield:
            print("-> Functional Requirement MET.")
        else:
            print("-> Functional Requirement NOT MET.")
            
    except Exception as e:
        print(f"Simulation Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_validation_demo()
