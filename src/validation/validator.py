import numpy as np
"""
Purpose: Simulation engine for enzyme kinetics.
Overview: Uses Tellurium/Roadrunner to simulate Michaelis-Menten kinetics. Calculates product yield over time given enzyme parameters and environmental conditions (Temp, pH).
"""
import tellurium as te

class EnzymeValidator:
    def __init__(self):
        pass

    def check_structure_validity(self, embedding_vector):
        """
        Structure Validity Check.
        For ESM-2 embeddings, we assume the sequence was valid enough to generate an embedding.
        In a full implementation, this would check pLDDT from ESMFold.
        For now, we return True.
        """
        # Placeholder for ESMFold integration
        # if pLDDT < 70: return False
        return True, 90.0


    def calculate_effective_kcat(self, kcat_base, temp, ph, t_opt=50.0, ph_opt=5.0):
        """
        Calculates kcat adjusted for Temperature and pH.
        """
        # 1. Temperature Effect (Gaussian Approximation of Arrhenius + Denaturation)
        # Models a peak at t_opt with specific width
        t_width = 10.0
        temp_factor = np.exp(-0.5 * ((temp - t_opt) / t_width) ** 2)
        
        # 2. pH Effect (Bell curve)
        ph_width = 1.5
        ph_factor = np.exp(-0.5 * ((ph - ph_opt) / ph_width) ** 2)
        
        return kcat_base * temp_factor * ph_factor

    def run_kinetic_simulation(self, kcat, Km, substrate_conc_init, enzyme_conc=1e-6, 
                               duration=24, steps=100, 
                               temp=50.0, ph=5.0, 
                               ki=10.0, # Product Inhibition Constant (e.g. 10 g/L)
                               t_opt=50.0, ph_opt=5.0):
        """
        Simulates time-course reaction with Inhibition and Environmental Factors.
        
        Model:
        v = (kcat_eff * E * S) / (Km * (1 + P/Ki) + S)
        """
        
        # Calculate Effective parameters
        kcat_eff = self.calculate_effective_kcat(kcat, temp, ph, t_opt, ph_opt)
        
        # Antimony Model Definition
        antimony_model = f"""
        model EnzymeModel
            # Species
            species S, P;
            
            # Initial Conditions
            S = {substrate_conc_init};
            P = 0.0;
            E = {enzyme_conc};
            
            # Parameters
            kcat_eff = {kcat_eff};
            Km = {Km};
            Ki = {ki};
            
            # Reaction: Michaelis-Menten with Competitive Product Inhibition
            # Rate = kcat * [E] * [S] / (Km * (1 + P/Ki) + S)
            J0: S -> P; kcat_eff * E * S / (Km * (1 + P/Ki) + S);
        end
        """
        
        # Load and Simulate
        try:
            r = te.loada(antimony_model)
            result = r.simulate(0, duration, steps)
            
            # Extract S and P
            # Result columns are usually ['time', '[S]', '[P]']
            # We map them to standard return format
            t = result['time']
            s_conc = result['[S]']
            p_conc = result['[P]']
            
            y_result = np.column_stack((s_conc, p_conc))
            return t, y_result
            
        except Exception as e:
            print(f"Simulation Error: {e}")
            return None, None

    def run_multienzyme_simulation(self, 
                                   params_EG, params_BG,
                                   substrate_conc_init=100.0, 
                                   conc_EG=0.5e-6, conc_BG=0.5e-6,
                                   duration=24, steps=100, 
                                   temp=50.0, ph=5.0):
        """
        Simulates Synergistic Reaction: Cellulose (S) -> Cellobiose (C2) -> Glucose (G)
        
        params_EG/BG: dict with {kcat, Km, Ki, t_opt, ph_opt}
        """
        
        # Calculate Effective kcat for both
        kcat_eff_EG = self.calculate_effective_kcat(
            params_EG['kcat'], temp, ph, params_EG.get('t_opt', 50), params_EG.get('ph_opt', 5)
        )
        kcat_eff_BG = self.calculate_effective_kcat(
            params_BG['kcat'], temp, ph, params_BG.get('t_opt', 50), params_BG.get('ph_opt', 5)
        )
        
        model = f"""
        model MultiEnzymeSynergy
            species S, C2, G;
            
            # Initial
            S = {substrate_conc_init};
            C2 = 0.0;
            G = 0.0;
            
            E_EG = {conc_EG};
            E_BG = {conc_BG};
            
            # Params EG
            kcat_EG = {kcat_eff_EG};
            Km_EG = {params_EG['Km']};
            Ki_EG = {params_EG['Ki']}; # Inhibited by C2
            
            # Params BG
            kcat_BG = {kcat_eff_BG};
            Km_BG = {params_BG['Km']};
            Ki_BG = {params_BG['Ki']}; # Inhibited by G
            
            # Rate 1: S -> C2 (EG)
            # Competitive Inhibition by Product (C2)
            J1: S -> C2; kcat_EG * E_EG * S / (Km_EG * (1 + C2/Ki_EG) + S);
            
            # Rate 2: C2 -> G (BG)
            # Competitive Inhibition by Product (G)
            J2: C2 -> G; kcat_BG * E_BG * C2 / (Km_BG * (1 + G/Ki_BG) + C2);
        end
        """
        
        try:
            r = te.loada(model)
            result = r.simulate(0, duration, steps)
            return result['time'], result['[S]'], result['[C2]'], result['[G]']
        except Exception as e:
            print(f"MultiEnzyme Error: {e}")
            return None, None, None, None

