"""
Purpose: AI Design Engine (Inference & Optimization).
Overview: "AI Sommelier" Logic. Recommends the best enzyme from the OED database and employs Active Learning to engineer novel sequences.
Uses ESM-2 for embeddings and a Biophysical Oracle for validation.
"""
import pandas as pd
import numpy as np
import joblib
import os
import torch
import sys
from transformers import EsmTokenizer, EsmModel

# Add src to path to import data_engineering
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
from data_engineering.populate_kinetics import generate_ground_truth

class DesignEngine:
    def __init__(self, custom_dataframe=None):
        self.model_path = "models/yield_predictor.pkl"
        self.features_path = "data/processed/enzyme_features.csv"
        self.kinetics_path = "data/processed/enzyme_kinetics.csv"
        self.cols_path = "models/yield_predictor_cols.pkl"
        
        self.model = None
        self.df_features = None
        self.df_kinetics = None
        self.feature_cols = None
        self.custom_df = custom_dataframe # Store injected data
        
        # ESM-2 Model (Loaded lazily)
        self.tokenizer = None
        self.esm_model = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        self.load_resources()

    def load_resources(self):
        if os.path.exists(self.model_path):
            try:
                self.model = joblib.load(self.model_path)
            except:
                print("Warning: Could not load model (shape mismatch?). Retraining required.")
        if os.path.exists(self.features_path):
            self.df_features = pd.read_csv(self.features_path)
            
        # Priority: Injected DF > Disk CSV
        if self.custom_df is not None:
            self.df_kinetics = self.custom_df
        elif os.path.exists(self.kinetics_path):
            self.df_kinetics = pd.read_csv(self.kinetics_path)
        if os.path.exists(self.cols_path):
            self.feature_cols = joblib.load(self.cols_path)
            
    def _load_esm(self):
        if self.esm_model is None:
            print("Loading ESM-2 Model for Design Engine...")
            try:
                self.tokenizer = EsmTokenizer.from_pretrained("facebook/esm2_t6_8M_UR50D")
                self.esm_model = EsmModel.from_pretrained("facebook/esm2_t6_8M_UR50D").to(self.device)
                self.esm_model.eval()
            except Exception as e:
                print(f"Error loading ESM-2: {e}")

    def _get_embedding(self, sequence):
        self._load_esm()
        if self.esm_model is None:
            return np.zeros(320)
            
        with torch.no_grad():
            inputs = self.tokenizer(sequence, return_tensors="pt", truncation=True, max_length=1024)
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            outputs = self.esm_model(**inputs)
            # Mean pooling
            embedding = outputs.last_hidden_state.mean(dim=1).cpu().numpy()[0]
        return embedding

    def calculate_properties(self, sequence):
        """
        Calculates biophysical properties for visualization.
        Returns:
            dict: {Hydrophobicity (1-5), Charge (1-5), Stability (1-5)}
                  Normalized to 1-5 scale for Radar Chart.
        """
        if not sequence: return {'Hydrophobicity': 3, 'Charge': 3, 'Stability': 3}
        
        # 1. Kyte-Doolittle Hydrophobicity
        kd = {
            'I': 4.5, 'V': 4.2, 'L': 3.8, 'F': 2.8, 'C': 2.5, 'M': 1.9, 'A': 1.8, 
            'G': -0.4, 'T': -0.7, 'S': -0.8, 'W': -0.9, 'Y': -1.3, 'P': -1.6, 
            'H': -3.2, 'E': -3.5, 'Q': -3.5, 'D': -3.5, 'N': -3.5, 'K': -3.9, 'R': -4.5
        }
        hydro = sum(kd.get(aa, 0) for aa in sequence) / len(sequence)
        # Scale: -4.0 to 4.0 -> Map to 1-5
        # Avg usually around -0.5 to 0.5. 
        hydro_score = min(5, max(1, 3 + hydro))
        
        # 2. Net Charge (at pH 7)
        pos = sequence.count('R') + sequence.count('K')
        neg = sequence.count('D') + sequence.count('E')
        net_charge = pos - neg
        # Scale: -10 to +10 -> Map to 1-5
        charge_score = min(5, max(1, 3 + (net_charge / 5)))
        
        # 3. Stability (Mock based on A/V/L/I content vs G/S)
        # Aliphatic index proxy
        aliphatic = sum(sequence.count(aa) for aa in ['A','V','L','I'])
        flexible = sum(sequence.count(aa) for aa in ['G','S'])
        stability_ratio = aliphatic / (flexible + 1)
        stab_score = min(5, max(1, stability_ratio * 3))
        
        return {
            'Hydrophobicity': round(hydro_score, 1),
            'Charge': round(charge_score, 1),
            'Stability': round(stab_score, 1)
        }

    def recommend_best_enzyme(self, temp, ph, substrate="Cellulose"):
        if self.model is None or self.df_features is None:
            return None, 0.0, "Model not loaded"

        # Prepare input dataframe
        df_input = self.df_features.copy()
        
        # Add Environment columns
        df_input['temp'] = temp
        df_input['ph'] = ph
        df_input['substrate'] = substrate
        
        # One-Hot Encoding for Substrate
        sub_cols = [c for c in self.feature_cols if c.startswith('sub_')]
        for col in sub_cols:
            target_sub = col.replace('sub_', '')
            df_input[col] = (df_input['substrate'] == target_sub).astype(int)
            
        # Select columns in correct order
        try:
            X = df_input[self.feature_cols]
        except KeyError as e:
            return None, 0.0, f"Feature mismatch: {e}"
        
        # Predict
        yields = self.model.predict(X)
        
        best_idx = np.argmax(yields)
        best_yield = yields[best_idx]
        best_id = df_input.iloc[best_idx]['id']
        
        meta = self.df_kinetics[self.df_kinetics['id'] == best_id].iloc[0].to_dict()
        
        return {
            'id': best_id,
            'predicted_yield': best_yield,
            'kcat': meta.get('kcat'),
            'Km': meta.get('Km'),
            't_opt': meta.get('t_opt'),
            'organism': meta.get('organism', 'Unknown')
        }

    def _mutate_sequence(self, sequence):
        """
        Performs a single point mutation.
        """
        if not sequence: return sequence, "No seq"
        
        seq_list = list(sequence)
        pos = np.random.randint(0, len(seq_list))
        orig_aa = seq_list[pos]
        
        aas = ['A','R','N','D','C','Q','E','G','H','I','L','K','M','F','P','S','T','W','Y','V']
        new_aa = np.random.choice(aas)
        while new_aa == orig_aa:
             new_aa = np.random.choice(aas)
             
        seq_list[pos] = new_aa
        return "".join(seq_list), f"{orig_aa}{pos+1}{new_aa}"

    def apply_mutation(self, sequence, mutation_str):
        """
        Applies a mutation string (e.g. 'A154V') to a sequence.
        Returns the new sequence.
        """
        import re
        try:
            match = re.search(r'([A-Z])(\d+)([A-Z])', mutation_str)
            if not match:
                return sequence
            
            orig, pos, new = match.groups()
            idx = int(pos) - 1 # 1-based to 0-based
            
            if idx < 0 or idx >= len(sequence):
                return sequence
                
            # Verify original (optional, skip for robustness if data is messy)
            # if sequence[idx] != orig: print("Warning: Original AA mismatch")
            
            return sequence[:idx] + new + sequence[idx+1:]
        except:
            return sequence

    def propose_optimization(self, base_enzyme_id, temp, ph, substrate="Cellulose"):
        """
        Real sequence-based optimization.
        """
        if self.df_kinetics is None: return None
        
        row = self.df_kinetics[self.df_kinetics['id'] == base_enzyme_id]
        if row.empty: return None
        base_seq = row.iloc[0]['sequence']
        
        # Optimize for missing sequence (Recursive Parent Lookup)
        if pd.isna(base_seq) or not isinstance(base_seq, str) or len(base_seq) == 0:
            # Try to infer parent from ID (e.g., "EGLB_ASPNG_v1_AI")
            # Logic: Strip the suffix (_v1_AI, _v2_AI) and look up the original
            import re
            parent_match = re.search(r'^(.*)_v\d+_AI$', base_enzyme_id)
            
            if parent_match:
                parent_id = parent_match.group(1)
                # Look up parent
                parent_row = self.df_kinetics[self.df_kinetics['id'] == parent_id]
                if not parent_row.empty:
                    base_seq = parent_row.iloc[0]['sequence']
                    print(f"Recovered ancestry: Used parent {parent_id} sequence for {base_enzyme_id}")
                else:
                    # Parent also missing or not found? Crucial stop.
                    # We cannot invent biology.
                    return None
            else:
                # No clear parent pattern and no sequence. Cannot proceed scientifically.
                return None

        # 4. Predict Yield (Wild Type Baseline) - Calculated FIRST for comparison
        wt_vec = self._get_embedding(base_seq)
        dim = wt_vec.shape[0]
        wt_feat = {f'dim_{i}': wt_vec[i] for i in range(dim)}
        wt_feat['temp'] = temp
        wt_feat['ph'] = ph
        
        # Determine cols
        sub_cols = [c for c in self.feature_cols if c.startswith('sub_')]
        for col in sub_cols:
             t_sub = col.replace('sub_', '')
             wt_feat[col] = 1 if substrate == t_sub else 0
        for c in self.feature_cols:
             if c not in wt_feat: wt_feat[c] = 0
             
        df_wt = pd.DataFrame([wt_feat], columns=self.feature_cols)
        wt_yield = self.model.predict(df_wt)[0]

        # Optimization Loop (Best of 20)
        best_res = None
        best_diff = -999.0
        
        for _ in range(20):
            # 1. Mutate
            mut_seq, mut_desc = self._mutate_sequence(base_seq)
            
            # 2. Embed
            mut_vec = self._get_embedding(mut_seq)
            
            # 3. Predict Yield (Mutant)
            dim = mut_vec.shape[0]
            feat_dict = {f'dim_{i}': mut_vec[i] for i in range(dim)}
            feat_dict['temp'] = temp
            feat_dict['ph'] = ph
            # Substrate
            for col in sub_cols:
                target_sub = col.replace('sub_', '')
                feat_dict[col] = 1 if substrate == target_sub else 0
                
            # Ensure all columns
            for c in self.feature_cols:
                if c not in feat_dict: feat_dict[c] = 0
                
            df_input = pd.DataFrame([feat_dict], columns=self.feature_cols)
            
            pred_yield = self.model.predict(df_input)[0]
            
            # Compare
            diff = pred_yield - wt_yield
            if best_res is None or diff > best_diff:
                best_diff = diff
                best_res = {
                    'mutation': mut_desc,
                    'predicted_yield': pred_yield,
                    'baseline_yield': wt_yield,
                    'mechanism': 'AI Predicted Structural Improvement'
                }
        
        return best_res

    def _oracle_get_yield(self, sequence, temp, ph, substrate, duration=24*3600):
        """
        Biophysical Oracle.
        1. Get True Params from Sequence (generate_ground_truth).
        2. Run Kinetic Simulation.
        """
        from src.validation.validator import EnzymeValidator
        validator = EnzymeValidator()
        
        kcat, Km, Ki, t_opt, p_opt = generate_ground_truth(sequence)
        
        _, res = validator.run_kinetic_simulation(
            kcat=kcat, Km=Km, substrate_conc_init=100.0, enzyme_conc=1e-5,
            duration=duration, temp=temp, ph=ph, ki=Ki, t_opt=t_opt, ph_opt=p_opt
        )
        if res is not None:
             final_p = res[-1, 1]
             return final_p / 100.0, kcat
        return 0.0, kcat

    def run_active_learning_loop(self, start_enzyme_id, temp, ph, substrate="Cellulose", rounds=5):
        """
        Real Active Learning Loop: Design -> Build -> Test -> Learn
        """
        history = []
        
        row = self.df_kinetics[self.df_kinetics['id'] == start_enzyme_id]
        if row.empty: return []
        current_seq = row.iloc[0]['sequence']
        
        current_yield, current_kcat = self._oracle_get_yield(current_seq, temp, ph, substrate)
        
        history.append({
            "round": 0, "yield": current_yield, "kcat": current_kcat, "mutation": "Initial"
        })
        
        best_seq = current_seq
        best_yield = current_yield
        
        print(f"Starting AL Loop. Initial Yield: {current_yield:.4f}")
        
        for r in range(1, rounds + 1):
            # 1. Design (Generate 10 mutants, predict best)
            candidates = []
            
            for _ in range(10):
                m_seq, m_desc = self._mutate_sequence(best_seq)
                vec = self._get_embedding(m_seq)
                
                # Predict
                if self.model:
                    # Construct DF
                    dim = vec.shape[0] # 320
                    feat_dict = {f'dim_{i}': vec[i] for i in range(dim)}
                    feat_dict['temp'] = temp
                    feat_dict['ph'] = ph
                    sub_cols = [c for c in self.feature_cols if c.startswith('sub_')]
                    for col in sub_cols:
                        t_sub = col.replace('sub_', '')
                        feat_dict[col] = 1 if substrate == t_sub else 0
                    
                    # Fill missing
                    for c in self.feature_cols:
                        if c not in feat_dict: feat_dict[c] = 0
                        
                    df_in = pd.DataFrame([feat_dict], columns=self.feature_cols)
                    pred = self.model.predict(df_in)[0]
                else:
                    pred = 0.0 # Random exploration if no model
                
                candidates.append((m_seq, m_desc, pred))
            
            # Application Function: Greedy or UCB. Greedy for now.
            candidates.sort(key=lambda x: x[2], reverse=True)
            top_candidate = candidates[0]
            
            target_seq = top_candidate[0]
            desc = top_candidate[1]
            
            # 2. Test (Oracle)
            real_yield, real_kcat = self._oracle_get_yield(target_seq, temp, ph, substrate)
            
            # 3. Learn (Update Best)
            type_str = "Exploration"
            if real_yield > best_yield:
                best_yield = real_yield
                best_seq = target_seq
                type_str = "New Best"
            
            history.append({
                "round": r,
                "yield": round(real_yield, 4),
                "kcat": real_kcat,
                "mutation": desc,
                "type": type_str
            })
            print(f"Round {r}: {desc} -> Yield {real_yield:.4f} ({type_str})")
            
        return history
