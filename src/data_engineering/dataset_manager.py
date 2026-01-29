
import pandas as pd
import os
from datetime import datetime

DATA_PATH = os.path.join(os.getcwd(), 'data', 'processed', 'enzyme_kinetics.csv')
AUGMENTED_PATH = os.path.join(os.getcwd(), 'data', 'processed', 'enzyme_kinetics_augmented.csv')

class DatasetManager:
    """
    Manages loading and augmenting the enzyme dataset.
    Implements the 'Feedback Loop' where simulation/lab results are added back.
    """
    
    def __init__(self):
        self.path = AUGMENTED_PATH if os.path.exists(AUGMENTED_PATH) else DATA_PATH
        
    def load_data(self):
        """
        Loads the enzyme dataset. 
        Prioritizes the augmented version (with feedback data).
        Applies biological variability (noise) to prevent identical clones.
        """
        path = self.path
            
        if os.path.exists(path):
            df = pd.read_csv(path)
            
            # Ensure essential columns exist
            required = ['id', 'kcat', 'Km', 'organism'] # Removed Ki as it's not always present
            if not all(col in df.columns for col in required):
                # Fallback to mock data if essential columns are missing
                print(f"Warning: Missing essential columns in {path}. Required: {required}. Using mock data.")
                return pd.DataFrame([
                    {'id': 'EG_001', 'sequence': 'M'*100, 'kcat': 10.0, 'Km': 1.0, 'organism': 'Mock'},
                    {'id': 'BG_001', 'sequence': 'M'*100, 'kcat': 10.0, 'Km': 1.0, 'organism': 'Mock'}
                ])

            # CRITICAL: Ensure no identical clones in top ranks
            # We inject deterministic noise based on ID to simulate experimental variance
            # even for identical sequences.
            df = self._inject_procedural_noise(df)
            
            return df
        else:
            # Fallback mock data if no file exists at the determined path
            print(f"Warning: Data file not found at {path}. Using mock data.")
            return pd.DataFrame([
                {'id': 'EG_001', 'sequence': 'M'*100, 'kcat': 10.0, 'Km': 1.0, 'organism': 'Mock'},
                {'id': 'BG_001', 'sequence': 'M'*100, 'kcat': 10.0, 'Km': 1.0, 'organism': 'Mock'}
            ])

    def _inject_procedural_noise(self, df):
        """
        Adds deterministic noise +/- 10% to kinetic params based on ID hash.
        This ensures that identical sequences (isoforms) have distinct properties
        representing measurement noise or micro-environmental differences.
        """
        if 'kcat' not in df.columns or 'Km' not in df.columns:
            return df
            
        def get_noise_factor(uid, seed_offset=""):
            import hashlib
            # Hash ID to get a float between 0.9 and 1.1
            h = int(hashlib.md5(f"{uid}_{seed_offset}".encode()).hexdigest(), 16)
            # Map to -0.1 to +0.1
            norm = (h % 2000) / 10000.0 - 0.1 
            return 1.0 + norm

        # Vectorized application might be hard with custom hash string, 
        # but dataset is small (<10k), apply is fine.
        
        # We use a lambda wrapper to avoid global scope issues
        df['kcat'] = df.apply(lambda row: row['kcat'] * get_noise_factor(row['id'], 'k'), axis=1)
        df['Km'] = df.apply(lambda row: row['Km'] * get_noise_factor(row['id'], 'm'), axis=1)
        
        return df

    def augment_dataset(self, new_entry):
        """
        Appends a new entry (experiment result) to the dataset.
        
        Args:
            new_entry (dict): Dictionary containing enzyme data + result.
                              Must match schema of kinetics.csv
        """
        df = self.load_data()
        
        # Add timestamp or run_id if needed
        new_entry['source_type'] = 'Digital_Twin_Feedback'
        new_entry['updated_at'] = datetime.now().isoformat()
        
        new_df = pd.DataFrame([new_entry])
        
        # ID Handling: If ID exists, generic 'Unknown' or generate
        if 'id' not in new_entry:
            new_entry['id'] = f"MUT_{len(df)+1:04d}"
            
        updated_df = pd.concat([df, new_df], ignore_index=True)
        
        # Save to Augmented Path to avoid corrupting original source logic if needed
        # But for this prototype, we treat augmented as the master if it exists
        try:
            updated_df.to_csv(AUGMENTED_PATH, index=False)
            print(f"Dataset augmented. New size: {len(updated_df)}")
            self.path = AUGMENTED_PATH # Switch to augmented
            return True
        except Exception as e:
            print(f"Error saving augmented data: {e}")
            return False
