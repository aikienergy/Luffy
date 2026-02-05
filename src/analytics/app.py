"""
Purpose: EnzyFlow AI Dashboard (Infinite Cycle Edition).
Overview: 
    Tab 1: Auto-Discovery (vHTS) -> Select Hit.
    Tab 2: AI Engineering (Mutate Hit) -> Deploy.
    Tab 3: Digital Twin (Simulate & Feedback) -> Augment Data.
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os
import sys
from sklearn.decomposition import PCA

# Add root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.ai_model import design_engine
import importlib
importlib.reload(design_engine)
from src.ai_model.design_engine import DesignEngine
from src.ai_model.screening import SmartSampler
from src.data_engineering.dataset_manager import DatasetManager
from src.validation.validator import EnzymeValidator
from src.resources.materials import BIOMASS_DATA
from src.shared.components import load_css, stats_card, section_header, vertical_spacer, CardContainer, card_begin, card_end
from src.shared.constants import BIOMASS_PRESETS, PRETREATMENT_PRESETS

# Page Config
st.set_page_config(page_title="Cellulose Devourer Design | LUFFY", layout="wide", page_icon="🧬")

# Open Graph Meta Tags for Social Media / Blog Embeds
OG_TITLE = "LUFFY - Cellulose Devourer Design"
OG_DESCRIPTION = "AI-powered enzyme inverse design platform for biomass-to-ethanol conversion. Discover, engineer, and validate high-performance cellulases."
OG_IMAGE = "https://raw.githubusercontent.com/aikienergy/Luffy/main/assets/og_image.png"
OG_URL = "https://enzyme-inverse-design.streamlit.app"

st.markdown(f"""
    <meta property="og:title" content="{OG_TITLE}">
    <meta property="og:description" content="{OG_DESCRIPTION}">
    <meta property="og:image" content="{OG_IMAGE}">
    <meta property="og:url" content="{OG_URL}">
    <meta property="og:type" content="website">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{OG_TITLE}">
    <meta name="twitter:description" content="{OG_DESCRIPTION}">
    <meta name="twitter:image" content="{OG_IMAGE}">
""", unsafe_allow_html=True)

# -------------------------------------------------------------------------
# DESIGN SYSTEM (CSS)
# -------------------------------------------------------------------------
load_css()

# -------------------------------------------------------------------------
# STATE MANAGEMENT
# -------------------------------------------------------------------------
if 'target_enzyme' not in st.session_state: st.session_state['target_enzyme'] = None 
if 'digital_twin_config' not in st.session_state: st.session_state['digital_twin_config'] = None
if 'screen_results' not in st.session_state: st.session_state['screen_results'] = None
if 'generated_enzymes' not in st.session_state: st.session_state['generated_enzymes'] = [] # In-Memory Storage

# Load Static Data (Cached)
@st.cache_data
def get_static_data():
    dm = DatasetManager()
    # Force load original only (ignore augmented if it exists, though we deleted it)
    df = pd.read_csv(dm.path)
    return df

df_base = get_static_data()

# Merge Static + Dynamic (Session)
if st.session_state['generated_enzymes']:
    df_new = pd.DataFrame(st.session_state['generated_enzymes'])
    df_enz = pd.concat([df_base, df_new], ignore_index=True)
else:
    df_enz = df_base

# -------------------------------------------------------------------------
# -------------------------------------------------------------------------
# TAB 1: vHTS SCREENING (Smart vHTS)
# -------------------------------------------------------------------------

# Navigation State
PAGES = ["vHTS Screening", "Inverse Design", "Process Verification"]
if 'page_index' not in st.session_state: st.session_state['page_index'] = 0

def nav_change():
    # Callback: Sync manual radio click to session state
    st.session_state['page_index'] = PAGES.index(st.session_state['nav_radio'])

def set_page(index):
    st.session_state['page_index'] = index
    st.session_state['nav_radio'] = PAGES[index]

def transfer_to_engineering(target_data):
    st.session_state['target_enzyme'] = target_data
    st.toast("Transferred to AI Lab!", icon="✅")
    set_page(1) # Go to AI Engineering



# Custom Navigation
page = st.radio("Pipeline Stage", 
    PAGES, 
    horizontal=True, 
    key="nav_radio", 
    index=st.session_state['page_index'], 
    on_change=nav_change,
    label_visibility="collapsed"
)

st.markdown("---")

# Render Content
if page == "vHTS Screening":
    # LAYOUT: 3:7 RATIO
    col_l, col_r = st.columns([3, 7], gap="large")
    
    with col_l:
        # vertical_spacer(3.5) # Align with Right Side Toolbar (Button + Gap)
        vertical_spacer(5)
        
        section_header("Biomass & Pretreatment", "Real Biomass Simulation Settings")
        
        with CardContainer():
            # Phase 3: Biomass Preset Selection
            biomass_key = st.selectbox(
                "🌾 Biomass Type",
                list(BIOMASS_PRESETS.keys()),
                format_func=lambda x: BIOMASS_PRESETS[x]['name'],
                index=0  # Rice straw is default
            )
            preset = BIOMASS_PRESETS[biomass_key]
            
            # Show literature source
            st.caption(f"📚 Reference: {preset['literature_source']}")
            
            # Auto-fill from preset (user can override)
            lignin = st.slider(
                "Lignin Content (%)", 5, 30, 
                int(preset['lignin'] * 100)
            ) / 100
            
            particle_size = st.slider(
                "Particle Size (mm)", 0.1, 5.0, 
                preset['particle_size']
            )
            
            # Pretreatment Selection
            pretreatment_key = st.selectbox(
                "🔨 Pretreatment",
                list(PRETREATMENT_PRESETS.keys()),
                format_func=lambda x: PRETREATMENT_PRESETS[x]['name']
            )
            severity = PRETREATMENT_PRESETS[pretreatment_key]['severity']
            
            st.divider()
            
            # Substrate Calculation (mM Cellulose)
            load = st.slider("Solid Loading (g/L)", 10.0, 300.0, 100.0)
            pct_cel = preset['cellulose']
            conc_mM = (load * pct_cel / 162) * 1000
            
            # Persist biomass parameters to session state
            st.session_state['substrate_conc_mM'] = conc_mM
            st.session_state['substrate_name'] = preset['name']
            st.session_state['biomass_preset'] = preset
            st.session_state['lignin_content'] = lignin
            st.session_state['particle_size'] = particle_size
            st.session_state['pretreatment_severity'] = severity
            st.session_state['biomass_type'] = preset['type']
            
            stats_card("Target Cellulose", f"{conc_mM:.0f}", "mM", variant="default")
            
            st.divider()
            
            st.markdown("**Plate Format**")
            plate_format_str = st.selectbox("Format", ["96-well", "384-well", "1536-well"], label_visibility="collapsed")
            plate_format = int(plate_format_str.split('-')[0]) # Extract number
            
            st.markdown(f"**Database Size:** {len(df_enz)}")
            if len(st.session_state['generated_enzymes']) > 0:
                st.caption(f"(+{len(st.session_state['generated_enzymes'])} variants)")
            
            vertical_spacer(1)
            
            # PRIMARY ACTION (Left Side for Context)
            if st.button("Start Screening >", type="primary", use_container_width=True):
                 with st.spinner(f"Screening {plate_format} combinations..."):
                     sampler = SmartSampler(df_enz) 
                     samples = sampler.sample_plate(size=plate_format)
                     st.session_state['screen_results'] = samples
                     st.rerun()
                    
    with col_r:
        # --- TOOLBAR (Right Aligned) ---
        has_results = st.session_state['screen_results'] is not None
        
        target_data = None
        if has_results:
             samples = st.session_state['screen_results']
             df_res_tmp = pd.DataFrame(samples)
             # df_res_tmp['Yield (%)'] = (df_res_tmp['Predicted_Score'] * 100).round(1) # OLD
             df_res_tmp['Efficiency'] = df_res_tmp['Predicted_Score'].round(3)
             
             cols_to_merge = df_enz[['id', 'kcat', 'Km']]
             df_res_tmp = df_res_tmp.merge(cols_to_merge, left_on='eg_id', right_on='id', how='left')
             df_res_tmp = df_res_tmp.sort_values(by=['Efficiency', 'kcat'], ascending=[False, False])
             best_hit = df_res_tmp.iloc[0]
             target_data = {
                 'eg_id': best_hit['eg_id'],
                 'bg_id': best_hit['bg_id'],
                 'ratio': best_hit['ratio']
             }

        # Toolbar Layout: push button to right
        tb_col1, tb_col2 = st.columns([4, 1])
        with tb_col2:
            st.button("Use Top Hit >", 
                     type="primary",
                     disabled=not has_results,
                     on_click=lambda: (
                         st.session_state.update({
                             'target_enzyme': target_data,
                             'page_index': 1,
                             'nav_radio': "Inverse Design"
                         }),
                         st.toast("Hit Loaded to Design Engine", icon="🚀")
                     ),
                     use_container_width=True
            )

        # --- RESULTS CONTENT ---
        # Spacer must match Left Side (Button Height 48px + margin ~ 16px ~= 3.5rem?)
        # Actually Button is in a row. Left side has spacer 3.5rem. 
        # Right side has Button. We need a small gap then header.
        
        vertical_spacer(0.5)

        if st.session_state['screen_results']:
            samples = st.session_state['screen_results']
            
            # 1. Setup Data
            df_res = pd.DataFrame(samples)
            df_res['Ratio (EG:BG)'] = df_res.apply(lambda x: f"{int(x['ratio']*100)}:{int((1-x['ratio'])*100)}", axis=1)
            
            # Merge EG properties
            cols_to_merge = df_enz[['id', 'kcat', 'Km']]
            df_res = df_res.merge(cols_to_merge, left_on='eg_id', right_on='id', how='left')
            
            df_res['kcat (1/s)'] = df_res['kcat'].round(1)
            df_res['Km (mM)'] = df_res['Km'].round(2)
            # df_res['Yield (%)'] = (df_res['Predicted_Score'] * 100).round(1) # OLD
            df_res['Efficiency'] = df_res['Predicted_Score'].round(3)
            
            df_res = df_res.sort_values(by=['Efficiency', 'kcat'], ascending=[False, False])
            best_hit = df_res.iloc[0]

            # 2. Results Header (OUTSIDE CARD now, aligned with Left)
            section_header(f"Top Hit: {best_hit['eg_id']}", f"Efficiency Score: {best_hit['Efficiency']}")
            
            with CardContainer():
                # Simulation Chart (Full Width)
                validator = EnzymeValidator()
                p_eg = df_enz[df_enz['id']==best_hit['eg_id']].iloc[0].to_dict()
                p_bg = df_enz[df_enz['id']==best_hit['bg_id']].iloc[0].to_dict()
                
                enz_g_L = 0.01 * load
                total_enz_mM = (enz_g_L / 50000) * 1000 
                r_eg = best_hit['ratio']
                
                t, S, C2, G = validator.run_multienzyme_simulation(
                   p_eg, p_bg, substrate_conc_init=conc_mM,
                   conc_EG=total_enz_mM*r_eg, conc_BG=total_enz_mM*(1.0-r_eg),
                   duration=48*3600, temp=50.0, ph=5.0
                )
                
                # Calculate simulated yield
                final_glucose = G[-1] if G is not None and len(G) > 0 else 0
                simulated_yield = final_glucose / conc_mM if conc_mM > 0 else 0
                
                # Literature comparison
                lit_min, lit_max = preset.get('literature_yield', (0.2, 0.4))
                lit_source = preset.get('literature_source', 'Literature')
                
                df_sim = pd.DataFrame({"Time": t/3600, "Glucose": G})
                fig = px.line(df_sim, x="Time", y="Glucose", 
                              title=f"Reaction Kinetics (48h)",
                              color_discrete_sequence=["#10B981"])
                
                # Add literature expected range as shaded area
                lit_glucose_min = conc_mM * lit_min
                lit_glucose_max = conc_mM * lit_max
                fig.add_hrect(
                    y0=lit_glucose_min, y1=lit_glucose_max, 
                    fillcolor="green", opacity=0.1,
                    annotation_text=f"Literature Range ({lit_source})",
                    annotation_position="top right"
                )
                
                fig.update_layout(
                    margin=dict(l=0, r=0, t=30, b=0),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(family='Inter, sans-serif'),
                    xaxis=dict(showgrid=False, linecolor='#E5E7EB'),
                    yaxis=dict(showgrid=True, gridcolor='#F3F4F6'),
                )
                st.plotly_chart(fig, use_container_width=True)

                vertical_spacer(1)
                
                # Literature Comparison Badge
                if lit_min <= simulated_yield <= lit_max:
                    badge_text = "✅ Within Literature Range"
                    badge_color = "#10B981"
                elif abs(simulated_yield - (lit_min + lit_max)/2) < 0.15:
                    badge_text = "⚠️ Acceptable Range"
                    badge_color = "#F59E0B"
                else:
                    badge_text = "❌ Needs Calibration"
                    badge_color = "#EF4444"
                
                st.markdown(f"""
                <div style="display: flex; align-items: center; gap: 1rem; margin-bottom: 1rem;">
                    <span style="background: {badge_color}20; color: {badge_color}; padding: 0.25rem 0.75rem; border-radius: 999px; font-size: 0.875rem; font-weight: 500;">
                        {badge_text}
                    </span>
                    <span style="color: #6B7280; font-size: 0.875rem;">
                        Simulated: {simulated_yield*100:.1f}% | Expected: {lit_min*100:.0f}-{lit_max*100:.0f}%
                    </span>
                </div>
                """, unsafe_allow_html=True)

                # Key Metrics (3 Columns below Graph)
                m_col1, m_col2, m_col3 = st.columns(3)
                with m_col1:
                    stats_card("Catalytic Efficiency", f"{best_hit['Efficiency']:.2f}", "Score (0-1)", "success")
                with m_col2:
                    stats_card("Turnover (kcat)", f"{best_hit['kcat']:.1f}", "/sec")
                with m_col3:
                    stats_card("Affinity (Km)", f"{best_hit['Km']:.2f}", "mM")
            
            st.divider()

            # 3. Hit Map Table
            st.subheader("Candidate Rankings")
            st.dataframe(
                df_res[['eg_id', 'bg_id', 'Efficiency', 'kcat (1/s)', 'Km (mM)', 'Ratio (EG:BG)']], 
                use_container_width=True,
                height=250,
                column_config={
                    "Efficiency": st.column_config.ProgressColumn(
                        "Efficiency Score",
                        format="%.3f",
                        min_value=0,
                        max_value=1.0,
                    ),
                }
            )

        else:
             with CardContainer():
                 st.markdown("""
                 <div style="padding: 4rem; text-align: center; color: #9CA3AF;">
                     <h3>Ready/Idle</h3>
                     <p>Select parameters on the left and start screening.</p>
                 </div>
                 """, unsafe_allow_html=True)

# -------------------------------------------------------------------------
# TAB 2: INVERSE DESIGN (Evolution)
# -------------------------------------------------------------------------
elif page == "Inverse Design":
    col_l, col_r = st.columns([3, 7], gap="large")
    
# TAB 2
    if st.session_state['target_enzyme'] is None:
        with col_l:
            st.info("No target selected. Please find a hit in Tab 1 first.")
    else:
        target = st.session_state['target_enzyme']
        
        with col_l:
            vertical_spacer(5)
            section_header("Target Enzyme", "Evolutionary Parametrization")
            
            with CardContainer():
                st.code(f"EG: {target['eg_id']}\nBG: {target['bg_id']}")
                
                # Retrieve properties
                enz_data = df_enz[df_enz['id'] == target['eg_id']].iloc[0]
                
                col_m1, col_m2 = st.columns(2)
                with col_m1:
                    stats_card("Base kcat", f"{enz_data['kcat']:.1f}", "/s")
                with col_m2:
                    stats_card("Base Km", f"{enz_data['Km']:.1f}", "mM")
                
                vertical_spacer(1)
                
                if st.button("Generate Variant", type="primary", use_container_width=True):
                     with st.spinner("Folding & Optimizing (ESM-2)..."):
                         de = DesignEngine(df_enz) 
                         res = de.propose_optimization(target['eg_id'], 50.0, 5.0)
                         st.session_state['ai_variant'] = res
                         st.toast("Variant Generated!", icon="🧬")
                         st.rerun()

        with col_r:
            # --- TOOLBAR ---
            has_variant = ('ai_variant' in st.session_state and st.session_state['ai_variant'] is not None)
            res_for_btn = st.session_state['ai_variant'] if has_variant else None
            
            tb_col1, tb_col2 = st.columns([3, 1])
            with tb_col2:
                # Deploy Button
                st.button("Deploy to Verification >",  
                             disabled=not has_variant,
                             on_click=lambda: (
                                   st.session_state.update({
                                       'digital_twin_config': {'wt': target, 'mutant': res_for_btn},
                                       'page_index': 2,
                                       'nav_radio': "Process Verification"
                                   }),
                                   st.toast("Deployed to Digital Twin!", icon="✅")
                             ),
                             use_container_width=True
                )
            
            vertical_spacer(0.5)
            
            # --- RESULTS ---
            if 'ai_variant' in st.session_state and st.session_state['ai_variant']:
                res = st.session_state['ai_variant']
                
                section_header("Evolutionary Analysis", "Structural & Kinetic Predictions")
                
                with CardContainer():
                    r_col_metrics, r_col_radar = st.columns([1, 1])
                    
                    with r_col_metrics:
                         st.markdown(f"**Structural Delta**: {res['mutation']}")
                         st.caption(res['mechanism'])
                         
                         vertical_spacer(1)
                         
                         # Efficiency Gain (Delta)
                         # Efficiency Gain (Delta)
                         p_yield = res.get('predicted_yield', 0)
                         b_yield = res.get('baseline_yield', 0) # Backward compatibility
                         
                         # Relative Percentage Calculation
                         if b_yield > 0:
                             relative_gain = (p_yield - b_yield) / b_yield * 100
                         else:
                             relative_gain = 0
                         
                         variant_type = "success" if relative_gain >= 0 else "default"
                         sign = "+" if relative_gain >= 0 else ""
                         
                         stats_card("Predicted Improvement", 
                                    f"{sign}{relative_gain:.1f}%", 
                                    f"vs Baseline ({b_yield*100:.1f}%)", # baseline still shown as raw yield for reference
                                    variant=variant_type)

                    with r_col_radar:
                        # REAL Radar Chart with Error Handling
                        de = DesignEngine(df_enz)
                        
                        try:
                            wt_row = df_enz[df_enz['id'] == target['eg_id']].iloc[0]
                            wt_seq = wt_row.get('sequence', '')
                            
                            if pd.isna(wt_seq) or not isinstance(wt_seq, str) or len(wt_seq) == 0:
                                import re
                                parent_match = re.search(r'^(.*)_v\d+_AI$', target['eg_id'])
                                if parent_match:
                                     parent_id = parent_match.group(1)
                                     parent_row = df_enz[df_enz['id'] == parent_id]
                                     if not parent_row.empty:
                                         wt_seq = parent_row.iloc[0]['sequence']
                            
                            if not wt_seq:
                                raise ValueError("Sequence not found")
                                
                            mut_seq = de.apply_mutation(wt_seq, res['mutation'])
                            res['mutant_sequence'] = mut_seq 
                            
                            wt_props = de.calculate_properties(wt_seq)
                            mut_props = de.calculate_properties(mut_seq)
                            
                            categories = list(wt_props.keys())
                            r_wt = list(wt_props.values())
                            r_mut = list(mut_props.values())

                            fig = go.Figure()
                            fig.add_trace(go.Scatterpolar(
                                  r=r_wt, theta=categories, fill='toself', name='Wild Type',
                                  line_color='#9CA3AF'
                            ))
                            fig.add_trace(go.Scatterpolar(
                                  r=r_mut, theta=categories, fill='toself', name='Mutant (AI)',
                                  line_color='#10B981'
                            ))
                            fig.update_layout(
                              polar=dict(
                                  radialaxis=dict(visible=True, range=[0, 5], showticklabels=False),
                                  bgcolor='rgba(0,0,0,0)'
                              ),
                              showlegend=True,
                              height=300,
                              margin=dict(l=20, r=20, t=20, b=20),
                              paper_bgcolor='rgba(0,0,0,0)',
                              plot_bgcolor='rgba(0,0,0,0)',
                              font=dict(family='Inter, sans-serif'),
                              legend=dict(orientation="h", y=-0.1)
                            )
                            st.plotly_chart(fig, use_container_width=True)
                            
                        except Exception as e:
                            st.warning(f"Radar chart unavailable: {e}")
                            # Gracefully continue without crashing

# -------------------------------------------------------------------------
# TAB 3: PROCESS VERIFICATION (Simulation)
# -------------------------------------------------------------------------
elif page == "Process Verification":
    col_l, col_r = st.columns([3, 7], gap="large")

    if st.session_state['digital_twin_config'] is None:
        with col_l:
            st.info("No prototype deployed. Please engineer a variant in Tab 2.")
    else:
        dt_config = st.session_state['digital_twin_config']

        def find_time_to_target(t_array, G_array, target_fraction=0.8):
            """
            Calculates time to reach target yield (default 80% of max possible or final).
            Here we use 80% of the FINAL WT Yield as the benchmark for fair comparison.
            Or simply 80% of theoretical max? Let's use 80% of WT Final for now to show relative speedup to same milestone.
            Actually, commonly it's "Time to 80% conversion".
            We'll use 80% of current simulation's final value of WT as the target line.
            """
            if len(G_array) == 0: return None
            
            # Target is 80% of what WT achieved at 48h (or simpler: just raw conc if we knew max)
            # Let's define target as 80% of WT's final yield.
            # But if Mutant goes much higher, it hits this earlier.
            final_conc = G_array[-1] # This is WT final if passed G_w
            target_conc = final_conc * target_fraction

            for i, g in enumerate(G_array):
                if g >= target_conc:
                    return t_array[i] / 3600  # sec -> hour
            return None

        with col_l:
            vertical_spacer(5)
            section_header("Process Verification", "Pilot Scale Simulation Settings")
            
            with CardContainer():
                conc_mM = st.session_state.get('substrate_conc_mM', 216.0)
                sub_name = st.session_state.get('substrate_name', 'Default')
                
                st.markdown("**Conditions**")
                st.caption(f"Substrate: {sub_name} @ {conc_mM:.0f} mM")
                
                col_p1, col_p2 = st.columns(2)
                with col_p1:
                    stats_card("Temp", "50.0", "°C")
                with col_p2:
                    stats_card("pH", "5.0", "")
                
                vertical_spacer(0.5)
                stats_card("Duration", "48", "Hours")
                
                vertical_spacer(1)
                
                if st.button("Run Simulation", type="primary", use_container_width=True):
                       with st.spinner("Simulating Parallel Reactors..."):
                           validator = EnzymeValidator()
                           
                           wt_eg = df_enz[df_enz['id']==dt_config['wt']['eg_id']].iloc[0].to_dict()
                           wt_bg = df_enz[df_enz['id']==dt_config['wt']['bg_id']].iloc[0].to_dict()
                           
                           mut_eg = wt_eg.copy()
                           mut_eg['kcat'] = mut_eg['kcat'] * (1 + dt_config['mutant']['predicted_yield'])
                           
                           conc_mM = st.session_state.get('substrate_conc_mM', 216.0)
                           enz_conc = 0.02
                           r_eg = dt_config['wt'].get('ratio', 0.7)
                           
                           t_w, S_w, C2_w, G_w = validator.run_multienzyme_simulation(
                               wt_eg, wt_bg, substrate_conc_init=conc_mM, 
                               conc_EG=enz_conc*r_eg, conc_BG=enz_conc*(1.0-r_eg),
                               duration=48*3600, steps=1000
                           )
                           
                           t_m, S_m, C2_m, G_m = validator.run_multienzyme_simulation(
                               mut_eg, wt_bg, substrate_conc_init=conc_mM, 
                               conc_EG=enz_conc*r_eg, conc_BG=enz_conc*(1.0-r_eg),
                               duration=48*3600, steps=1000
                           )
                           
                           # Time to 80% Calculation (Benchmarked against WT Final)
                           target_conc = G_w[-1] * 0.8
                           
                           # Helper internal
                           def get_time(t, G, tgt):
                               for i, g in enumerate(G):
                                   if g >= tgt: return t[i]/3600
                               return None
                           
                           time_wt_80 = get_time(t_w, G_w, target_conc)
                           time_mut_80 = get_time(t_m, G_m, target_conc)
                           
                           if time_wt_80 and time_mut_80 and time_wt_80 > 0:
                               time_reduction_pct = (time_wt_80 - time_mut_80) / time_wt_80 * 100
                           else:
                               time_reduction_pct = 0

                           st.session_state['val_res'] = {
                               't': t_w/3600, 
                               'G_wt': G_w, 
                               'G_mut': G_m,
                               'eff_wt': G_w[-1],
                               'eff_mut': G_m[-1],
                               'time_wt_80': time_wt_80,
                               'time_mut_80': time_mut_80,
                               'time_reduction_pct': time_reduction_pct,
                               'target_80': target_conc
                           }
                           st.rerun()

        with col_r:
             # --- TOOLBAR ---
             has_val_res = 'val_res' in st.session_state
             
             tb_col1, tb_col2 = st.columns([3, 1])
             with tb_col2:
                 def save_to_memory_callback():
                      dt_config = st.session_state['digital_twin_config']
                      base_id = dt_config['wt']['eg_id']
                      import re
                      v_match = re.search(r'_v(\d+)_AI$', base_id)
                      if v_match:
                          ver = int(v_match.group(1)) + 1
                          root = re.sub(r'_v\d+_AI$', '', base_id)
                          mutant_id = f"{root}_v{ver}_AI"
                      else:
                          mutant_id = f"{base_id}_v1_AI"
                      
                      parent_data = df_enz[df_enz['id']==dt_config['wt']['eg_id']].iloc[0].to_dict()
                      new_entry = parent_data.copy()
                      new_entry['id'] = mutant_id
                      new_entry['kcat'] = new_entry['kcat'] * (1 + dt_config['mutant']['predicted_yield'])
                      new_entry['organism'] = 'AI_Engineered'
                      new_entry['updated_at'] = pd.Timestamp.now().isoformat()
                      new_entry['sequence'] = dt_config['mutant'].get('mutant_sequence', '')
                      if 'Unnamed: 0' in new_entry: del new_entry['Unnamed: 0']
                      
                      st.session_state['generated_enzymes'].append(new_entry)
                      st.toast(f"Saved {mutant_id} to Session Memory! Tab 1 will now use it.", icon="🧠")
                      set_page(0)

                 st.button("Save & Feedback >", 
                           disabled=not has_val_res,
                           on_click=save_to_memory_callback,
                           use_container_width=True)
            
             vertical_spacer(0.5)
             
             # --- RESULTS ---
             if 'val_res' in st.session_state:
                 res = st.session_state['val_res']
                 
                 section_header("Performance Comparison", "Digital Twin vs Wild Type")
                 
                 with CardContainer():
                     df_comp = pd.DataFrame({
                         "Time (h)": res['t'],
                         "Wild Type": res['G_wt'],
                         "Mutant (AI)": res['G_mut']
                     })
                     
                     fig = px.line(df_comp, x="Time (h)", y=["Wild Type", "Mutant (AI)"],
                                  title="Glucose Production (mM)",
                                  color_discrete_map={"Wild Type": "#9CA3AF", "Mutant (AI)": "#10B981"})
                     fig.update_layout(
                        margin=dict(l=0, r=0, t=30, b=0),
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(family='Inter, sans-serif'),
                        xaxis=dict(showgrid=False, linecolor='#E5E7EB'),
                        yaxis=dict(showgrid=True, gridcolor='#F3F4F6'),
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                     )
                     
                     # Add 80% Line
                     target_80 = res.get('target_80', res['eff_wt']*0.8)
                     fig.add_hline(y=target_80, line_dash="dash", line_color="#9CA3AF", annotation_text="80% Target", annotation_position="top right")
                     
                     # Vertical Lines for Time
                     if res.get('time_wt_80'):
                         fig.add_vline(x=res['time_wt_80'], line_dash="dot", line_color="#9CA3AF", opacity=0.5)
                     if res.get('time_mut_80'):
                         fig.add_vline(x=res['time_mut_80'], line_dash="dot", line_color="#10B981", opacity=0.5)

                     st.plotly_chart(fig, use_container_width=True)
                     
                     # Final Metrics - Time Efficiency Focus
                     m_col1, m_col2, m_col3, m_col4 = st.columns(4)
                     
                     with m_col1:
                         t_val = f"{res['time_wt_80']:.1f}h" if res.get('time_wt_80') else "N/A"
                         stats_card("Time to 80% (WT)", t_val, "")
                         
                     with m_col2:
                         t_val = f"{res['time_mut_80']:.1f}h" if res.get('time_mut_80') else "N/A"
                         stats_card("Time to 80% (Mut)", t_val, "")
                         
                     with m_col3:
                         reduction = res.get('time_reduction_pct', 0)
                         variant = "success" if reduction > 0 else "default"
                         stats_card("Time Reduction", f"-{reduction:.0f}%" if reduction > 0 else "0%", "Faster", variant=variant)
                         
                     with m_col4:
                         delta = res['eff_mut'] - res['eff_wt']
                         stats_card("Yield Δ", f"+{delta:.1f}", "mM (Ref)")
