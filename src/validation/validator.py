"""
Purpose: Cellulose-specific enzyme-kinetics simulation engine.

Overview:
    Uses Tellurium/Roadrunner (CVODE) to integrate kinetics of enzymatic
    cellulose hydrolysis. Unlike a naive soluble-substrate Michaelis-Menten
    applied to insoluble cellulose, this engine models the recognised features
    of crystalline-cellulose saccharification:

      * a three-enzyme system  EG (endoglucanase) + CBH (cellobiohydrolase)
        attack insoluble cellulose -> cellobiose; BG (beta-glucosidase) cleaves
        the SOLUBLE cellobiose -> glucose with classical Michaelis-Menten,
      * a substrate-accessibility decay term  Phi(X) = exp(-alpha * X)  that
        reproduces the steep rate retardation with conversion (restart/fractal
        behaviour; Jeoh et al. 2017 doi:10.1002/bit.26277; Bansal et al. 2012),
      * competitive product inhibition (cellobiose on EG/CBH, glucose on BG),
      * correct stoichiometry: 1 cellobiose = 2 glucose units.

    Units convention (see src/config.py):
        concentration : mM   (cellulose & glucose tracked in GLUCOSE-EQUIVALENTS;
                              cellobiose tracked in cellobiose units)
        time          : seconds
        kcat          : 1/s
    Glucose-equivalent mass balance:  Cel + 2*C2 + G  ==  Cel0  (conserved).

    `alpha` (accessibility decay) is the single free parameter, fitted once by
    src/data_engineering/calibrate_model.py against a literature conversion
    benchmark (src/config.py CALIB_TARGET_CONVERSION).
"""
import numpy as np
import tellurium as te

import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src import config

# Glucose anhydro-unit molar mass (g/mol) used to express cellulose mass as
# glucose-equivalent molar concentration.
GLUCOSE_UNIT_G_PER_MOL = 162.14


def cellulose_gpl_to_glucose_equiv_mM(g_per_L):
    """Convert insoluble-cellulose mass concentration (g/L) to mM glucose-equiv."""
    return float(g_per_L) / GLUCOSE_UNIT_G_PER_MOL * 1000.0


def enzyme_mM(loading_mg_per_g, cellulose_g_per_L, mw_da):
    """
    Convert a protein-mass enzyme loading to molar concentration (mM).

    loading_mg_per_g : mg enzyme protein per g cellulose (glucan)
    cellulose_g_per_L: substrate loading (g/L)
    mw_da            : enzyme molecular weight (Da = g/mol)

    Returns concentration in mM. This single function is used by the screening
    tab, the verification tab AND the training-data generator so all three
    share one physical regime.
    """
    protein_g_per_L = float(loading_mg_per_g) * float(cellulose_g_per_L) / 1000.0
    mol_per_L = protein_g_per_L / float(mw_da)
    return mol_per_L * 1000.0  # mM


class EnzymeValidator:
    def __init__(self):
        pass

    # ------------------------------------------------------------------
    # Real-biomass substrate-property factors (lignin inhibition + geometric
    # accessibility). These multiply the cellulose-attack rate; they default to
    # a neutral 1.0 so calibration/training (which pass no biomass) are unchanged.
    # ------------------------------------------------------------------
    def calculate_accessibility(self, particle_size, crystallinity=0.7, severity=0.0):
        """Geometric accessibility factor in [0.01, 0.99]. Smaller particles and
        lower crystallinity expose more attackable surface; pretreatment severity
        physically opens up that surface (defibrillation + decrystallisation), so
        accessibility interpolates toward full exposure as severity -> 1
        (qualitatively per Alvira et al. 2010). D_REF/EXPONENT are calibrated
        model parameters (not measured) from config.get_biomass_params() so a
        biomass calibration is honoured here (see calibrate_biomass.py).

        At severity=0 this equals the untreated surface x (1-crystallinity)
        accessibility (back-compatible with the pre-calibration formula)."""
        bp = config.get_biomass_params()
        d_ref, exponent = bp["d_ref"], bp["exponent"]
        surface_factor = 1.0 / (1.0 + (float(particle_size) / d_ref) ** exponent)
        base = surface_factor * (1.0 - float(crystallinity))   # untreated accessible fraction
        access = base + float(severity) * (1.0 - base)         # pretreatment exposes surface
        return max(0.01, min(0.99, access))

    def calculate_inhibition_factor(self, lignin_content, biomass_type="grass",
                                    phenol_conc=0.0, furfural_conc=0.0,
                                    severity=0.0, ki_phenol=None, ki_furfural=None):
        """Lignin inhibition factor in [0.01, 0.99] (1.0 = no inhibition).
        Langmuir non-productive adsorption to lignin (k_ads is a calibrated model
        parameter) + non-competitive phenol/furfural inhibition (Ki from the
        soluble-inhibitor literature; see data/curated/PROVENANCE.md).

        Pretreatment severity DELIGNIFIES the substrate, lowering non-productive
        adsorption, so the lignin term relaxes toward no-inhibition as
        severity -> 1 (this is what lets steam-explosion-grade pretreatment reach
        the high literature yield bands; without it the model is capped by the
        raw-biomass lignin content). Lignin adsorption ordering follows Li &
        Zheng (2017); phenol cellulase inhibition follows Ximenes et al. (2010);
        furans are weak cellulase inhibitors so furfural has a small effect.

        At severity=0 this equals the pre-calibration formula (back-compatible)."""
        hydro = config.HYDROPHOBICITY_INDEX.get(biomass_type, 0.65)
        k_ads = config.get_biomass_params()["k_ads"]
        ki_ph = config.INHIBITION_CONSTANTS["ki_phenol"] if ki_phenol is None else ki_phenol
        ki_fur = config.INHIBITION_CONSTANTS["ki_furfural"] if ki_furfural is None else ki_furfural
        L = float(lignin_content)
        denom = k_ads + L * hydro
        alpha_ads = (L * hydro) / denom if denom > 0 else 0.0
        base_inhib = 1.0 - alpha_ads
        lignin_factor = base_inhib + float(severity) * (1.0 - base_inhib)  # delignification
        phenol_factor = 1.0 / (1.0 + phenol_conc / ki_ph) if ki_ph > 0 else 1.0
        furfural_factor = 1.0 / (1.0 + furfural_conc / ki_fur) if ki_fur > 0 else 1.0
        return max(0.01, min(0.99, lignin_factor * phenol_factor * furfural_factor))

    def biomass_factor(self, lignin_content=0.0, biomass_type="grass",
                       particle_size=None, crystallinity=0.7, severity=0.0,
                       phenol_conc=0.0, furfural_conc=0.0):
        """Combined substrate-property multiplier on the cellulose-attack rate.
        Returns 1.0 when no biomass properties are supplied (neutral default)."""
        bio = 1.0
        if lignin_content and float(lignin_content) > 0:
            bio *= self.calculate_inhibition_factor(lignin_content, biomass_type,
                                                    phenol_conc, furfural_conc,
                                                    severity=severity)
        if particle_size is not None:
            bio *= self.calculate_accessibility(particle_size, crystallinity, severity)
        return bio

    def calculate_effective_kcat(self, kcat_base, temp, ph,
                                 t_opt=config.DEFAULT_TEMP_C,
                                 ph_opt=config.DEFAULT_PH):
        """
        kcat adjusted for temperature and pH via Gaussian response curves
        (approximation of the Arrhenius-rise / thermal-denaturation balance and
        the bell-shaped pH-activity profile). Widths come from src/config.py.
        """
        t_width = config.TEMP_WIDTH_C
        ph_width = config.PH_WIDTH
        temp_factor = np.exp(-0.5 * ((temp - t_opt) / t_width) ** 2)
        ph_factor = np.exp(-0.5 * ((ph - ph_opt) / ph_width) ** 2)
        return kcat_base * temp_factor * ph_factor

    # ------------------------------------------------------------------
    # Single-enzyme productivity (used to characterise an enzyme for the
    # yield-predictor training grid). Cellulose attack with accessibility decay.
    # ------------------------------------------------------------------
    def run_kinetic_simulation(self, kcat, Km, substrate_conc_init, enzyme_conc=1e-3,
                               duration=86400, steps=200,
                               temp=config.DEFAULT_TEMP_C, ph=config.DEFAULT_PH,
                               ki=config.KI_CELLOBIOSE_MM,
                               t_opt=config.DEFAULT_TEMP_C, ph_opt=config.DEFAULT_PH,
                               alpha=None, bio_factor=1.0):
        """
        Single-enzyme cellulose hydrolysis: S (insoluble, glucose-equiv) -> P.
        Includes accessibility decay and product inhibition.

        Returns (t, y) where y[:,0]=[S], y[:,1]=[P] in mM glucose-equiv.
        Conversion is P/substrate_conc_init (computed by the caller).
        """
        if alpha is None:
            alpha = config.get_accessibility_alpha()
        kcat_eff = self.calculate_effective_kcat(kcat, temp, ph, t_opt, ph_opt)
        S0 = float(substrate_conc_init)
        if S0 <= 0:
            return None, None

        model = f"""
        model SingleEnzymeCellulose
            species S, P;
            S = {S0};
            P = 0.0;
            E = {enzyme_conc};
            kcat_eff = {kcat_eff};
            Km = {Km};
            Ki = {ki};
            alpha = {alpha};
            bio = {bio_factor};
            S0 = {S0};
            X := 1 - S/S0;
            Phi := exp(-alpha * X);
            J0: S -> P; kcat_eff * E * bio * Phi * S / (Km + S) / (1 + P/Ki);
        end
        """
        try:
            r = te.loada(model)
            result = r.simulate(0, duration, steps)
            t = np.asarray(result["time"])
            s_conc = np.asarray(result["[S]"])
            p_conc = np.asarray(result["[P]"])
            return t, np.column_stack((s_conc, p_conc))
        except Exception as e:  # pragma: no cover - solver edge cases
            print(f"Simulation Error: {e}")
            return None, None

    # ------------------------------------------------------------------
    # Three-enzyme cellulolytic cascade (process verification & calibration).
    # ------------------------------------------------------------------
    def run_cellulolytic_simulation(self, params_EG, params_CBH, params_BG,
                                    substrate_conc_init,
                                    conc_EG, conc_CBH, conc_BG,
                                    duration=None, steps=400,
                                    temp=config.DEFAULT_TEMP_C, ph=config.DEFAULT_PH,
                                    alpha=None, bio_factor=1.0):
        """
        Cellulose (Cel) --EG/CBH--> Cellobiose (C2) --BG--> Glucose (G).

        params_* : dict with keys kcat, Km, Ki, t_opt, ph_opt
                   (Km in mM glucose-equiv for EG/CBH; in mM cellobiose for BG).
        conc_*   : enzyme concentration in mM (use enzyme_mM()).
        Returns (t [h], Cel, C2, G) arrays in mM (glucose-equiv for Cel & G).
        """
        if duration is None:
            duration = config.DEFAULT_DURATION_H * 3600.0
        if alpha is None:
            alpha = config.get_accessibility_alpha()

        Cel0 = float(substrate_conc_init)
        if Cel0 <= 0:
            return None, None, None, None

        kcat_EG = self.calculate_effective_kcat(
            params_EG["kcat"], temp, ph,
            params_EG.get("t_opt", config.DEFAULT_TEMP_C),
            params_EG.get("ph_opt", config.DEFAULT_PH))
        kcat_CBH = self.calculate_effective_kcat(
            params_CBH["kcat"], temp, ph,
            params_CBH.get("t_opt", config.DEFAULT_TEMP_C),
            params_CBH.get("ph_opt", config.DEFAULT_PH))
        kcat_BG = self.calculate_effective_kcat(
            params_BG["kcat"], temp, ph,
            params_BG.get("t_opt", config.DEFAULT_TEMP_C),
            params_BG.get("ph_opt", config.DEFAULT_PH))

        ki_eg = params_EG.get("Ki", config.KI_CELLOBIOSE_MM)
        ki_cbh = params_CBH.get("Ki", config.KI_CELLOBIOSE_MM)
        ki_bg = params_BG.get("Ki", config.KI_GLUCOSE_MM)

        model = f"""
        model Cellulolysis
            species Cel, C2, G;
            Cel = {Cel0};
            C2 = 0.0;
            G = 0.0;
            E_EG = {conc_EG};
            E_CBH = {conc_CBH};
            E_BG = {conc_BG};
            kcat_EG = {kcat_EG};  Km_EG = {params_EG['Km']};   Ki_EG = {ki_eg};
            kcat_CBH = {kcat_CBH}; Km_CBH = {params_CBH['Km']}; Ki_CBH = {ki_cbh};
            kcat_BG = {kcat_BG};   Km_BG = {params_BG['Km']};   Ki_BG = {ki_bg};
            alpha = {alpha};
            bio = {bio_factor};
            Cel0 = {Cel0};
            X := 1 - Cel/Cel0;
            Phi := exp(-alpha * X);
            # Cellulose attack -> cellobiose (1 cellobiose = 2 glucose units).
            # `bio` = lignin-inhibition x geometric-accessibility (1.0 if no biomass given);
            # applied to the solid-attack enzymes only (BG acts on soluble cellobiose).
            J_EG:  Cel -> 0.5 C2; kcat_EG  * E_EG  * bio * Phi * Cel/(Km_EG  + Cel) / (1 + C2/Ki_EG);
            J_CBH: Cel -> 0.5 C2; kcat_CBH * E_CBH * bio * Phi * Cel/(Km_CBH + Cel) / (1 + C2/Ki_CBH);
            # Soluble cellobiose -> 2 glucose (classical MM, glucose inhibition)
            J_BG:  C2 -> 2 G;     kcat_BG  * E_BG  * C2/(Km_BG*(1 + G/Ki_BG) + C2);
        end
        """
        try:
            r = te.loada(model)
            result = r.simulate(0, duration, steps)
            t = np.asarray(result["time"])
            return (t / 3600.0,
                    np.asarray(result["[Cel]"]),
                    np.asarray(result["[C2]"]),
                    np.asarray(result["[G]"]))
        except Exception as e:  # pragma: no cover
            print(f"Cellulolytic simulation error: {e}")
            return None, None, None, None
