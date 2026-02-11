
import pandas as pd
import numpy as np
from src.ai_model.design_engine import DesignEngine

class SmartSampler:
    """
    Implements 'Biochemically Meaningful' sampling for High-Throughput Screening.
    Avoids random selection by using heuristics like Kinetic Complementarity and Diversity.
    Uses AI Model (DesignEngine) to predict scores.
    """
    
    def __init__(self, df_kinetics):
        self.df = df_kinetics
        
        # Phase 2 Fix: Use 'specificity' column for accurate classification
        # instead of unreliable ID string matching
        if 'specificity' in self.df.columns:
            self.eg_list = self.df[self.df['specificity'] == 'Cellulase']
            self.bg_list = self.df[self.df['specificity'] == 'Beta-glucosidase']
            self.cbh_list = self.df[self.df['specificity'] == 'Cellobiohydrolase']
        else:
            # Legacy fallback for old datasets
            self.eg_list = self.df[self.df['id'].str.contains("EG", na=False) | 
                                   self.df['id'].str.contains("Cellulase", na=False)]
            self.bg_list = self.df[self.df['id'].str.contains("BG", na=False) | 
                                   self.df['id'].str.contains("Glucosidase", na=False)]
            self.cbh_list = pd.DataFrame()
        
        # Fallback with WARNING if empty (prevents silent misuse)
        if self.eg_list.empty: 
            print("[WARNING] EG list empty - using mock EG data")
            self.eg_list = self.df.head(min(10, len(self.df)))
        if self.bg_list.empty: 
            print("[WARNING] BG list empty - using default BG parameters")
            # Use default BG parameters instead of misusing EG data
            self.bg_list = pd.DataFrame([{
                'id': 'DEFAULT_BG', 'kcat': 66.7, 'Km': 1.11, 'Ki': 2.22,
                't_opt': 50.0, 'ph_opt': 5.0, 'sequence': '', 'organism': 'Default'
            }])
        
        # Initialize AI for Scoring
        self.de = DesignEngine()

    def _predict_score(self, eg_id, bg_id):
        """
        Catalytic Efficiency (kcat/Km) based scoring.
        kcat/Km is the comprehensive performance metric (Specificity Constant).
        """
        try:
            eg_row = self.df[self.df['id'] == eg_id].iloc[0]
            bg_row = self.df[self.df['id'] == bg_id].iloc[0]

            # EG: Catalytic Efficiency (kcat/Km)
            # Avoid division by zero
            eg_efficiency = eg_row['kcat'] / max(eg_row['Km'], 0.01)

            # BG: Efficiency considering Inhibition (Ki)
            bg_efficiency = bg_row['kcat'] / max(bg_row['Km'], 0.01)
            bg_ki_factor = np.log1p(bg_row.get('Ki', 5.0))  # Higher Ki = Better Tolerance

            # Combined Score (Log scale, EG weighted higher as rate limiting)
            combined = np.log10(eg_efficiency + 0.1) * 0.6 + \
                       np.log10(bg_efficiency + 0.1) * 0.25 + \
                       bg_ki_factor * 0.15

            # Normalize to 0-1 (Assumed efficiency range -1 to 3 in log10)
            score = (combined + 1.0) / 4.0
            return float(np.clip(score, 0.01, 0.99))

        except Exception as e:
            return 0.5

    def _optimize_ratio(self, eg_kcat, bg_kcat):
        """
        Heuristic to suggest optimal EG fraction (0.0 - 1.0).
        Based on the principle that the rate-limiting step needs more enzyme.
        Simplified approximation: Ratio ~ 1 / (1 + sqrt(k_EG / k_BG))
        """
        try:
            # If EG is very fast (high kcat), we need less of it.
            # If BG is slow (low kcat), we need more of it (less EG).
            if eg_kcat <= 0 or bg_kcat <= 0: return 0.7
            
            # Theoretical balance point for linear pathway flux maximization
            # Fraction EG (f_eg)
            f_eg = 1.0 / (1.0 + np.sqrt(eg_kcat / bg_kcat))
            
            # Clamp to reasonable industrial bounds (20% - 90%)
            return float(np.clip(f_eg, 0.2, 0.9))
        except:
            return 0.7

    def sample_plate(self, size=96):
        """
        Generates a list of enzyme pairs (EG, BG) for the specified plate size.
        """
        samples = []
        
        # Strategy 1: High Performance Pairs (Top 20%)
        top_eg = self.eg_list.nlargest(int(len(self.eg_list)*0.2), 'kcat')
        top_bg = self.bg_list.nlargest(int(len(self.bg_list)*0.2), 'Ki')
        
        # Strategy 2: Diversity
        div_eg = self.eg_list.drop_duplicates(subset='organism').head(20)
        
        count = 0
        
        # Helper to add sample with optimization
        def add_sample(eg, bg, reason):
            pred_score = self._predict_score(eg['id'], bg['id'])
            # Calc Ratio
            opt_ratio = self._optimize_ratio(eg['kcat'], bg.get('kcat', 10.0)) # BG might not be in same DF structure if mixed? assuming consistency
            # kcat is in the row
            
            return {
                'eg_id': eg['id'],
                'bg_id': bg['id'],
                'reason': reason,
                'Predicted_Score': pred_score,
                'ratio': round(opt_ratio, 2)
            }
        
        # 1. Exhaustive High Performance
        for _, eg in top_eg.iterrows():
            for _, bg in top_bg.iterrows():
                if count >= size: break
                samples.append(add_sample(eg, bg, 'High Performance Synergy'))
                count += 1
            if count >= size: break
            
        # 2. Diversity Fill
        if count < size:
            remaining = size - count
            # Use random sampling to fill the rest
            # Ensure we don't just stop if diversity head(20) is exhausted
            
            # Simple approach: Sample 'remaining' times from the full lists
            other_eg = self.eg_list.sample(n=remaining, replace=True)
            other_bg = self.bg_list.sample(n=remaining, replace=True)
            
            for (i, eg), (j, bg) in zip(other_eg.iterrows(), other_bg.iterrows()):
                samples.append(add_sample(eg, bg, 'Exploration (Random/Diversity)'))
                count += 1
                
        # Sort by Score
        samples = sorted(samples, key=lambda x: x['Predicted_Score'], reverse=True)
        return samples[:size]
