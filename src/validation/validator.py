import numpy as np
"""
Purpose: Simulation engine for enzyme kinetics.
Overview: Uses Tellurium/Roadrunner to simulate Michaelis-Menten kinetics. 
          Calculates product yield over time given enzyme parameters and environmental conditions.
          Phase 3: Includes real biomass support with lignin inhibition model.
"""
import tellurium as te
from src.shared.constants import HYDROPHOBICITY_INDEX, INHIBITION_CONSTANTS

class EnzymeValidator:
    def __init__(self):
        pass

    # =========================================================================
    # Phase 3: Real Biomass Support Methods
    # =========================================================================
    
    def calculate_accessibility(
        self,
        particle_size: float,
        crystallinity: float = 0.7,
        severity: float = 0.0
    ) -> float:
        """
        Calculates geometric accessibility factor (η_access).
        
        Based on particle size and crystallinity barrier.
        Literature: Alvira et al. (2010)
        
        Args:
            particle_size: Particle diameter in mm (0.1-5.0)
            crystallinity: Crystallinity index CrI (0.5-0.9)
            severity: Pretreatment severity (0.0=crushing, 1.0=steam explosion)
        
        Returns:
            η_access: 0.01-0.99 (accessibility factor)
        """
        D_REF = 0.5  # Reference particle size (mm)
        EXPONENT = 1.5  # Surface area scaling exponent
        
        # Surface area factor: smaller particles = higher access
        surface_factor = 1 / (1 + (particle_size / D_REF) ** EXPONENT)
        
        # Crystallinity barrier: higher severity breaks crystalline structure
        crystal_factor = 1 - crystallinity * (1 - severity)
        
        eta = surface_factor * crystal_factor
        return max(0.01, min(0.99, eta))  # Numerical stability

    def calculate_inhibition_factor(
        self,
        lignin_content: float,
        biomass_type: str = 'grass',
        phenol_conc: float = 0.0,
        furfural_conc: float = 0.0,
        ki_phenol: float = None,
        ki_furfural: float = None
    ) -> float:
        """
        Calculates lignin inhibition factor.
        
        Combines Langmuir adsorption model with phenolic/furfural inhibition.
        Literature: Li & Zheng (2017), Ximenes et al. (2010)
        
        Args:
            lignin_content: Lignin fraction (0.0-0.3)
            biomass_type: 'softwood', 'hardwood', or 'grass'
            phenol_conc: Phenolic compound concentration (mM)
            furfural_conc: Furfural concentration (mM)
            ki_phenol: Override Ki for phenol (default from constants)
            ki_furfural: Override Ki for furfural (default from constants)
        
        Returns:
            Inhibition factor: 0.01-0.99 (1.0 = no inhibition)
        """
        # Get constants
        hydro = HYDROPHOBICITY_INDEX.get(biomass_type, 0.65)
        k_ads = INHIBITION_CONSTANTS['k_ads']
        ki_ph = ki_phenol if ki_phenol is not None else INHIBITION_CONSTANTS['ki_phenol']
        ki_fur = ki_furfural if ki_furfural is not None else INHIBITION_CONSTANTS['ki_furfural']
        
        # Langmuir adsorption: α_ads = (L × H) / (K_ads + L × H)
        alpha_ads = (lignin_content * hydro) / (k_ads + lignin_content * hydro)
        
        # Phenolic inhibition (non-competitive)
        phenol_factor = 1 / (1 + phenol_conc / ki_ph) if ki_ph > 0 else 1.0
        
        # Furfural inhibition (from hemicellulose degradation)
        furfural_factor = 1 / (1 + furfural_conc / ki_fur) if ki_fur > 0 else 1.0
        
        # Combined factor
        factor = (1 - alpha_ads) * phenol_factor * furfural_factor
        return max(0.01, min(0.99, factor))

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
                               t_opt=50.0, ph_opt=5.0,
                               # Phase 3: Real Biomass Parameters
                               particle_size: float = None,
                               crystallinity: float = 0.7,
                               severity: float = 0.0,
                               lignin_content: float = 0.0,
                               biomass_type: str = 'grass',
                               phenol_conc: float = 0.0,
                               furfural_conc: float = 0.0):
        """
        Simulates time-course reaction with Inhibition and Environmental Factors.
        
        Model:
        v = (kcat_eff * E * S) / (Km * (1 + P/Ki) + S)
        
        Phase 3 Extension:
        kcat_eff *= η_access × inhibition_factor
        """
        
        # Calculate Effective kcat (Temperature + pH)
        kcat_eff = self.calculate_effective_kcat(kcat, temp, ph, t_opt, ph_opt)
        
        # Phase 3: Apply accessibility and inhibition factors
        if particle_size is not None:
            eta_access = self.calculate_accessibility(particle_size, crystallinity, severity)
            kcat_eff *= eta_access
        
        if lignin_content > 0:
            inh_factor = self.calculate_inhibition_factor(
                lignin_content, biomass_type, phenol_conc, furfural_conc
            )
            kcat_eff *= inh_factor
        
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
                                   temp=50.0, ph=5.0,
                                   # Phase 3: Real Biomass Parameters
                                   particle_size: float = None,
                                   crystallinity: float = 0.7,
                                   severity: float = 0.0,
                                   lignin_content: float = 0.0,
                                   biomass_type: str = 'grass',
                                   phenol_conc: float = 0.0,
                                   furfural_conc: float = 0.0):
        """
        Simulates Synergistic Reaction: Cellulose (S) -> Cellobiose (C2) -> Glucose (G)
        
        Phase 3: Applies geometric accessibility and lignin inhibition to both enzymes.
        
        Args:
            params_EG/BG: dict with {kcat, Km, Ki, t_opt, ph_opt}
            particle_size: Particle diameter in mm (None = pure substrate)
            lignin_content: Lignin fraction (0.0-0.3)
            biomass_type: 'softwood', 'hardwood', or 'grass'
            phenol_conc, furfural_conc: Inhibitor concentrations (mM)
        """
        
        # Calculate Effective kcat for both
        kcat_eff_EG = self.calculate_effective_kcat(
            params_EG['kcat'], temp, ph, params_EG.get('t_opt', 50), params_EG.get('ph_opt', 5)
        )
        kcat_eff_BG = self.calculate_effective_kcat(
            params_BG['kcat'], temp, ph, params_BG.get('t_opt', 50), params_BG.get('ph_opt', 5)
        )
        
        # Phase 3: Apply biomass factors to both enzymes
        if particle_size is not None:
            eta_access = self.calculate_accessibility(particle_size, crystallinity, severity)
            kcat_eff_EG *= eta_access
            kcat_eff_BG *= eta_access
        
        if lignin_content > 0:
            inh_factor = self.calculate_inhibition_factor(
                lignin_content, biomass_type, phenol_conc, furfural_conc
            )
            kcat_eff_EG *= inh_factor
            kcat_eff_BG *= inh_factor
        
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

