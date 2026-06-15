"""
Purpose: EnzyFlow AI Dashboard (Infinite Cycle Edition).
Overview:
    Tab 1: Auto-Discovery (vHTS) -> select a cellulase cocktail (EG+CBH+BG).
    Tab 2: AI Engineering (mutate the endoglucanase) -> deploy.
    Tab 3: Digital Twin (cellulolytic cascade simulation & feedback) -> augment.

    Kinetic values shown to the user are provenance-tagged: a "Literature" badge
    plus a citations panel (paper + DOI + measured value + assay conditions) for
    literature-sourced enzymes, and an "Estimated" badge for sequence-heuristic
    values. The simulated glucose curve is overlaid with the literature
    reaction-rate band so users can see the result sitting inside the cited range.
"""
import os
import sys

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src import config
from src.ai_model.design_engine import DesignEngine
from src.ai_model.screening import SmartSampler
from src.data_engineering.dataset_manager import DatasetManager
from src.validation.validator import (EnzymeValidator, enzyme_mM,
                                       cellulose_gpl_to_glucose_equiv_mM)
from src.resources.materials import BIOMASS_DATA
from src.shared.components import (load_css, stats_card, section_header,
                                   vertical_spacer, CardContainer, source_badge)

st.set_page_config(page_title="Cellulose Devourer Design | LUFFY", layout="wide", page_icon="🧬")

OG_TITLE = "LUFFY - Cellulose Devourer Design"
OG_DESCRIPTION = "AI-powered enzyme inverse design platform for biomass-to-ethanol conversion."
OG_IMAGE = "https://raw.githubusercontent.com/aikienergy/Luffy/main/assets/og_image.png"
OG_URL = "https://enzyme-inverse-design.streamlit.app"
st.markdown(f"""
    <meta property="og:title" content="{OG_TITLE}">
    <meta property="og:description" content="{OG_DESCRIPTION}">
    <meta property="og:image" content="{OG_IMAGE}">
    <meta property="og:url" content="{OG_URL}">
    <meta property="og:type" content="website">
    <meta name="twitter:card" content="summary_large_image">
""", unsafe_allow_html=True)

load_css()

# -------------------------------------------------------------------------
# STATE
# -------------------------------------------------------------------------
for key, default in [('target_enzyme', None), ('digital_twin_config', None),
                     ('screen_results', None), ('generated_enzymes', []),
                     ('ai_variant', None)]:
    if key not in st.session_state:
        st.session_state[key] = default


@st.cache_data
def get_static_data():
    return DatasetManager().load_static()


df_base = get_static_data()
if st.session_state['generated_enzymes']:
    df_enz = pd.concat([df_base, pd.DataFrame(st.session_state['generated_enzymes'])],
                       ignore_index=True)
else:
    df_enz = df_base


# -------------------------------------------------------------------------
# HELPERS
# -------------------------------------------------------------------------
def enzyme_params(eid):
    row = df_enz[df_enz['id'] == eid].iloc[0]
    return {'kcat': float(row['kcat']), 'Km': float(row['Km']),
            'Ki': float(row.get('Ki', config.KI_CELLOBIOSE_MM)),
            't_opt': float(row.get('t_opt', config.DEFAULT_TEMP_C)),
            'ph_opt': float(row.get('ph_opt', config.DEFAULT_PH))}


def run_cocktail(eg_id, cbh_id, bg_id, fracs, cellulose_g_L, duration_h=None):
    """Run the 3-enzyme cellulolytic cascade for a cocktail. Returns (t_h, Cel, C2, G, Cel0)."""
    validator = EnzymeValidator()
    Cel0 = cellulose_gpl_to_glucose_equiv_mM(cellulose_g_L)
    load = config.ENZYME_LOADING_MG_PER_G_GLUCAN
    e_eg = enzyme_mM(load * fracs[0], cellulose_g_L, config.ENZYME_MW_DA['EG'])
    e_cbh = enzyme_mM(load * fracs[1], cellulose_g_L, config.ENZYME_MW_DA['CBH'])
    e_bg = enzyme_mM(load * fracs[2], cellulose_g_L, config.ENZYME_MW_DA['BG'])
    dur = (duration_h or config.DEFAULT_DURATION_H) * 3600.0
    t, Cel, C2, G = validator.run_cellulolytic_simulation(
        enzyme_params(eg_id), enzyme_params(cbh_id), enzyme_params(bg_id),
        substrate_conc_init=Cel0, conc_EG=e_eg, conc_CBH=e_cbh, conc_BG=e_bg,
        duration=dur, temp=config.DEFAULT_TEMP_C, ph=config.DEFAULT_PH)
    return t, Cel, C2, G, Cel0


def add_literature_band(fig, cel0):
    """Shade the literature conversion envelope (glucose mM) on a kinetics chart."""
    lo, hi = config.LIT_RATE_BAND
    fig.add_hrect(y0=lo * cel0, y1=hi * cel0, line_width=0,
                  fillcolor="#10B981", opacity=0.08,
                  annotation_text="Literature range", annotation_position="top left")
    fig.add_hline(y=config.CALIB_TARGET_CONVERSION * cel0, line_dash="dot",
                  line_color="#10B981", opacity=0.5,
                  annotation_text=f"Lit. target {int(config.CALIB_TARGET_CONVERSION*100)}%",
                  annotation_position="bottom right")


def render_sources_panel(entries):
    """entries: list of (role, enzyme_id). Shows provenance + citations expander."""
    with st.expander("📚 Provenance & Citations — verify against the papers"):
        rows = []
        for role, eid in entries:
            r = df_enz[df_enz['id'] == eid]
            if r.empty:
                continue
            r = r.iloc[0]
            st_type = r.get('source_type', 'Estimated')
            if str(st_type) == 'Literature':
                doi = r.get('doi')
                doi_md = f"[{doi}](https://doi.org/{doi})" if pd.notna(doi) and doi else "—"
                reported = "—"
                if pd.notna(r.get('kcat_reported')):
                    reported = (f"{r.get('kcat_reported')} {r.get('kcat_unit')}, "
                                f"Km {r.get('Km_reported')} {r.get('Km_unit')} "
                                f"on {r.get('substrate')}")
                rows.append({
                    "Role": role, "Enzyme": eid, "Source": "Literature",
                    "Organism": r.get('organism'),
                    "Reported (as in paper)": reported,
                    "Simulator (kcat 1/s, Km mM)": f"{r['kcat']:.3g} / {r['Km']:.3g}",
                    "Paper": r.get('source_title'),
                    "Authors (Year)": f"{r.get('authors')} ({r.get('year')})",
                    "DOI": doi_md,
                    "Status": r.get('verification_status'),
                })
            else:
                rows.append({
                    "Role": role, "Enzyme": eid, "Source": "Estimated",
                    "Organism": r.get('organism'),
                    "Reported (as in paper)": "— (sequence heuristic, not a measurement)",
                    "Simulator (kcat 1/s, Km mM)": f"{r['kcat']:.3g} / {r['Km']:.3g}",
                    "Paper": "—", "Authors (Year)": "—", "DOI": "—",
                    "Status": "estimated (not literature)",
                })
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        st.caption("Literature values are normalised to simulator units (kcat 1/s, Km mM); "
                   "click the DOI to confirm the reported value. Full verbatim quotes: "
                   "data/curated/PROVENANCE.md.")


# -------------------------------------------------------------------------
# NAV
# -------------------------------------------------------------------------
PAGES = ["vHTS Screening", "Inverse Design", "Process Verification"]
if 'page_index' not in st.session_state:
    st.session_state['page_index'] = 0


def nav_change():
    st.session_state['page_index'] = PAGES.index(st.session_state['nav_radio'])


def set_page(index):
    st.session_state['page_index'] = index
    st.session_state['nav_radio'] = PAGES[index]


page = st.radio("Pipeline Stage", PAGES, horizontal=True, key="nav_radio",
                index=st.session_state['page_index'], on_change=nav_change,
                label_visibility="collapsed")
st.markdown("---")

# =========================================================================
# TAB 1: vHTS SCREENING
# =========================================================================
if page == "vHTS Screening":
    col_l, col_r = st.columns([3, 7], gap="large")

    with col_l:
        vertical_spacer(5)
        section_header("Substrate & Screening", "Define material and run vHTS")
        with CardContainer():
            mat_name = st.selectbox("Material Class", list(BIOMASS_DATA.keys()))
            load = st.slider("Solid Loading (g/L)", 10.0, 300.0, 100.0)
            pct_cel = BIOMASS_DATA[mat_name]['composition'].get('Cellulose', 0)
            cellulose_g_L = load * (pct_cel / 100.0)
            conc_mM = cellulose_gpl_to_glucose_equiv_mM(cellulose_g_L)
            st.session_state['cellulose_g_L'] = cellulose_g_L
            st.session_state['substrate_name'] = mat_name
            stats_card("Target Cellulose", f"{conc_mM:.0f}", "mM (glucose-equiv)")
            st.divider()
            st.markdown("**Plate Format**")
            plate_format = int(st.selectbox("Format", ["96-well", "384-well", "1536-well"],
                                            label_visibility="collapsed").split('-')[0])
            st.markdown(f"**Database Size:** {len(df_enz)}")
            if st.session_state['generated_enzymes']:
                st.caption(f"(+{len(st.session_state['generated_enzymes'])} variants)")
            vertical_spacer(1)
            if st.button("Start Screening >", type="primary", use_container_width=True):
                with st.spinner(f"Screening {plate_format} cocktails..."):
                    st.session_state['screen_results'] = SmartSampler(df_enz).sample_plate(size=plate_format)
                    st.rerun()

    with col_r:
        has_results = st.session_state['screen_results'] is not None
        best_hit = None
        if has_results:
            df_res = pd.DataFrame(st.session_state['screen_results'])
            df_res = df_res.merge(df_enz[['id', 'kcat', 'Km', 'source_type']],
                                  left_on='eg_id', right_on='id', how='left')
            df_res['Efficiency'] = df_res['Predicted_Score'].round(3)
            df_res = df_res.sort_values(by=['Efficiency', 'kcat'], ascending=[False, False])
            best_hit = df_res.iloc[0]

        tb1, tb2 = st.columns([4, 1])
        with tb2:
            st.button("Use Top Hit >", type="primary", disabled=not has_results,
                      on_click=lambda: (st.session_state.update({
                          'target_enzyme': {
                              'eg_id': best_hit['eg_id'], 'cbh_id': best_hit['cbh_id'],
                              'bg_id': best_hit['bg_id'],
                              'fracs': [best_hit['ratio_eg'], best_hit['ratio_cbh'], best_hit['ratio_bg']]},
                          'page_index': 1, 'nav_radio': "Inverse Design"}),
                          st.toast("Hit loaded to Design Engine", icon="🚀")),
                      use_container_width=True)
        vertical_spacer(0.5)

        if has_results:
            section_header(f"Top Hit: {best_hit['eg_id']} + {best_hit['cbh_id']} + {best_hit['bg_id']}",
                           f"Efficiency Score: {best_hit['Efficiency']}")
            with CardContainer():
                cel_g_L = st.session_state.get('cellulose_g_L', 35.0)
                t, Cel, C2, G, Cel0 = run_cocktail(
                    best_hit['eg_id'], best_hit['cbh_id'], best_hit['bg_id'],
                    [best_hit['ratio_eg'], best_hit['ratio_cbh'], best_hit['ratio_bg']], cel_g_L)
                fig = px.line(pd.DataFrame({"Time (h)": t, "Glucose": G}), x="Time (h)", y="Glucose",
                              title=f"Cellulolytic Cascade ({int(config.DEFAULT_DURATION_H)}h)",
                              color_discrete_sequence=["#10B981"])
                add_literature_band(fig, Cel0)
                fig.update_layout(margin=dict(l=0, r=0, t=30, b=0),
                                  paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                                  font=dict(family='Inter, sans-serif'),
                                  yaxis=dict(showgrid=True, gridcolor='#F3F4F6', title="Glucose (mM)"))
                st.plotly_chart(fig, use_container_width=True)
                final_conv = float(G[-1]) / Cel0 if Cel0 else 0.0

                vertical_spacer(1)
                m1, m2, m3 = st.columns(3)
                with m1:
                    stats_card("Final Conversion", f"{final_conv*100:.0f}", "% glucose", "success")
                with m2:
                    stats_card("EG Turnover (kcat)", f"{best_hit['kcat']:.2g}", "/s")
                    source_badge(best_hit.get('source_type', 'Estimated'))
                with m3:
                    stats_card("EG Affinity (Km)", f"{best_hit['Km']:.2g}", "mM")
            render_sources_panel([("EG", best_hit['eg_id']), ("CBH", best_hit['cbh_id']),
                                  ("BG", best_hit['bg_id'])])
            st.divider()
            st.subheader("Candidate Cocktail Rankings")
            show = df_res[['eg_id', 'cbh_id', 'bg_id', 'Efficiency', 'ratio_eg', 'ratio_cbh', 'ratio_bg']]
            st.dataframe(show, use_container_width=True, height=240, hide_index=True,
                         column_config={"Efficiency": st.column_config.ProgressColumn(
                             "Efficiency Score", format="%.3f", min_value=0, max_value=1.0)})
        else:
            with CardContainer():
                st.markdown('<div style="padding:4rem;text-align:center;color:#9CA3AF;">'
                            '<h3>Ready/Idle</h3><p>Select parameters and start screening.</p></div>',
                            unsafe_allow_html=True)

# =========================================================================
# TAB 2: INVERSE DESIGN
# =========================================================================
elif page == "Inverse Design":
    col_l, col_r = st.columns([3, 7], gap="large")
    if st.session_state['target_enzyme'] is None:
        with col_l:
            st.info("No target selected. Find a hit in Tab 1 first.")
    else:
        target = st.session_state['target_enzyme']
        with col_l:
            vertical_spacer(5)
            section_header("Target Enzyme", "Evolutionary parametrization")
            with CardContainer():
                st.code(f"EG: {target['eg_id']}\nCBH: {target['cbh_id']}\nBG: {target['bg_id']}")
                enz_data = df_enz[df_enz['id'] == target['eg_id']].iloc[0]
                c1, c2 = st.columns(2)
                with c1:
                    stats_card("Base kcat (EG)", f"{enz_data['kcat']:.2g}", "/s")
                with c2:
                    stats_card("Base Km (EG)", f"{enz_data['Km']:.2g}", "mM")
                source_badge(enz_data.get('source_type', 'Estimated'))
                vertical_spacer(1)
                if st.button("Generate Variant", type="primary", use_container_width=True):
                    with st.spinner("Folding & optimizing (ESM-2)..."):
                        try:
                            de = DesignEngine(df_enz)
                            st.session_state['ai_variant'] = de.propose_optimization(
                                target['eg_id'], config.DEFAULT_TEMP_C, config.DEFAULT_PH)
                            st.toast("Variant generated!", icon="🧬")
                        except RuntimeError as e:
                            st.session_state['ai_variant'] = None
                            st.error(f"Design unavailable: {e}")
                        st.rerun()

        with col_r:
            has_variant = st.session_state.get('ai_variant') is not None
            res_for_btn = st.session_state.get('ai_variant')
            _, tb2 = st.columns([3, 1])
            with tb2:
                st.button("Deploy to Verification >", disabled=not has_variant,
                          on_click=lambda: (st.session_state.update({
                              'digital_twin_config': {'wt': target, 'mutant': res_for_btn},
                              'page_index': 2, 'nav_radio': "Process Verification"}),
                              st.toast("Deployed to Digital Twin!", icon="✅")),
                          use_container_width=True)
            vertical_spacer(0.5)
            if has_variant:
                res = st.session_state['ai_variant']
                section_header("Evolutionary Analysis", "Structural & kinetic predictions")
                with CardContainer():
                    left, right = st.columns([1, 1])
                    with left:
                        st.markdown(f"**Structural Delta**: {res['mutation']}")
                        st.caption(res['mechanism'])
                        vertical_spacer(1)
                        p_y, b_y = res.get('predicted_yield', 0), res.get('baseline_yield', 0)
                        rel = (p_y - b_y) / b_y * 100 if b_y else 0
                        # GP predictive uncertainty propagated to the relative gain.
                        std = res.get('predicted_yield_std', 0) + res.get('baseline_yield_std', 0)
                        rel_std = std / b_y * 100 if b_y else 0
                        stats_card("Predicted Improvement", f"{'+' if rel >= 0 else ''}{rel:.1f}%",
                                   f"± {rel_std:.1f}% (GP 1σ) vs baseline {b_y*100:.1f}%",
                                   variant="success" if rel >= 0 else "default")
                        st.caption("Confidence from the Gaussian-Process predictive variance.")
                    with right:
                        try:
                            de = DesignEngine(df_enz)
                            wt_row = df_enz[df_enz['id'] == target['eg_id']].iloc[0]
                            wt_seq = wt_row.get('sequence', '')
                            if (pd.isna(wt_seq) or not isinstance(wt_seq, str) or not wt_seq):
                                raise ValueError("Sequence not found for radar chart")
                            mut_seq = de.apply_mutation(wt_seq, res['mutation'])
                            res['mutant_sequence'] = mut_seq
                            wt_p = de.calculate_properties(wt_seq)
                            mut_p = de.calculate_properties(mut_seq)
                            cats = list(wt_p.keys())
                            fig = go.Figure()
                            fig.add_trace(go.Scatterpolar(r=list(wt_p.values()), theta=cats,
                                          fill='toself', name='Wild Type', line_color='#9CA3AF'))
                            fig.add_trace(go.Scatterpolar(r=list(mut_p.values()), theta=cats,
                                          fill='toself', name='Mutant (AI)', line_color='#10B981'))
                            fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 5],
                                              showticklabels=False), bgcolor='rgba(0,0,0,0)'),
                                              showlegend=True, height=300,
                                              margin=dict(l=20, r=20, t=20, b=20),
                                              paper_bgcolor='rgba(0,0,0,0)',
                                              legend=dict(orientation="h", y=-0.1))
                            st.plotly_chart(fig, use_container_width=True)
                        except Exception as e:
                            st.warning(f"Radar chart unavailable: {e}")

# =========================================================================
# TAB 3: PROCESS VERIFICATION
# =========================================================================
elif page == "Process Verification":
    col_l, col_r = st.columns([3, 7], gap="large")
    if st.session_state['digital_twin_config'] is None:
        with col_l:
            st.info("No prototype deployed. Engineer a variant in Tab 2.")
    else:
        dt = st.session_state['digital_twin_config']
        wt = dt['wt']
        fracs = wt.get('fracs', [config.DEFAULT_COCKTAIL_FRACTIONS['EG'],
                                 config.DEFAULT_COCKTAIL_FRACTIONS['CBH'],
                                 config.DEFAULT_COCKTAIL_FRACTIONS['BG']])

        with col_l:
            vertical_spacer(5)
            section_header("Process Verification", "Pilot-scale cellulolytic simulation")
            with CardContainer():
                cel_g_L = st.session_state.get('cellulose_g_L', 35.0)
                st.caption(f"Substrate: {st.session_state.get('substrate_name', 'Default')} "
                           f"@ {cellulose_gpl_to_glucose_equiv_mM(cel_g_L):.0f} mM glucose-equiv")
                c1, c2 = st.columns(2)
                with c1:
                    stats_card("Temp", f"{config.DEFAULT_TEMP_C:.0f}", "°C")
                with c2:
                    stats_card("pH", f"{config.DEFAULT_PH:.1f}", "")
                vertical_spacer(0.5)
                stats_card("Duration", f"{int(config.DEFAULT_DURATION_H)}", "Hours")
                vertical_spacer(1)
                if st.button("Run Simulation", type="primary", use_container_width=True):
                    with st.spinner("Simulating parallel reactors..."):
                        t_w, Cel_w, C2_w, G_w, Cel0 = run_cocktail(
                            wt['eg_id'], wt['cbh_id'], wt['bg_id'], fracs, cel_g_L)
                        # Mutant: improved EG kcat by the predicted relative gain.
                        mut = dt['mutant'] or {}
                        b_y = mut.get('baseline_yield', 0)
                        gain = ((mut.get('predicted_yield', 0) - b_y) / b_y) if b_y else 0.0
                        gain = float(np.clip(gain, -0.5, 2.0))
                        st.session_state['_mut_gain'] = gain
                        validator = EnzymeValidator()
                        eg_p = enzyme_params(wt['eg_id']); eg_p['kcat'] *= (1 + gain)
                        load = config.ENZYME_LOADING_MG_PER_G_GLUCAN
                        e_eg = enzyme_mM(load * fracs[0], cel_g_L, config.ENZYME_MW_DA['EG'])
                        e_cbh = enzyme_mM(load * fracs[1], cel_g_L, config.ENZYME_MW_DA['CBH'])
                        e_bg = enzyme_mM(load * fracs[2], cel_g_L, config.ENZYME_MW_DA['BG'])
                        t_m, Cel_m, C2_m, G_m = validator.run_cellulolytic_simulation(
                            eg_p, enzyme_params(wt['cbh_id']), enzyme_params(wt['bg_id']),
                            substrate_conc_init=Cel0, conc_EG=e_eg, conc_CBH=e_cbh, conc_BG=e_bg,
                            duration=config.DEFAULT_DURATION_H * 3600.0,
                            temp=config.DEFAULT_TEMP_C, ph=config.DEFAULT_PH)
                        target80 = G_w[-1] * 0.8

                        def t80(tt, GG):
                            for i, g in enumerate(GG):
                                if g >= target80:
                                    return tt[i]
                            return None
                        tw, tm = t80(t_w, G_w), t80(t_m, G_m)
                        red = ((tw - tm) / tw * 100) if (tw and tm and tw > 0) else 0
                        st.session_state['val_res'] = {
                            't': t_w, 'G_wt': G_w, 'G_mut': G_m, 'Cel0': Cel0,
                            'eff_wt': G_w[-1], 'eff_mut': G_m[-1],
                            'time_wt_80': tw, 'time_mut_80': tm,
                            'time_reduction_pct': red, 'target_80': target80}
                        st.rerun()

        with col_r:
            has_res = 'val_res' in st.session_state
            _, tb2 = st.columns([3, 1])

            def save_to_memory():
                base_id = wt['eg_id']
                import re
                m = re.search(r'_v(\d+)_AI$', base_id)
                if m:
                    root = re.sub(r'_v\d+_AI$', '', base_id)
                    mutant_id = f"{root}_v{int(m.group(1)) + 1}_AI"
                else:
                    mutant_id = f"{base_id}_v1_AI"
                parent = df_enz[df_enz['id'] == base_id].iloc[0].to_dict()
                entry = dict(parent)
                entry['id'] = mutant_id
                entry['kcat'] = float(parent['kcat']) * (1 + st.session_state.get('_mut_gain', 0))
                entry['organism'] = 'AI_Engineered'
                entry['enzyme_class'] = 'EG'
                entry['source_type'] = 'Digital_Twin_Feedback'
                entry['sequence'] = (st.session_state.get('ai_variant') or {}).get('mutant_sequence', '')
                entry.pop('Unnamed: 0', None)
                st.session_state['generated_enzymes'].append(entry)
                st.toast(f"Saved {mutant_id}! Tab 1 will now use it.", icon="🧠")
                set_page(0)

            with tb2:
                st.button("Save & Feedback >", disabled=not has_res,
                          on_click=save_to_memory, use_container_width=True)
            vertical_spacer(0.5)

            if has_res:
                r = st.session_state['val_res']
                section_header("Performance Comparison", "Digital Twin vs Wild Type")
                with CardContainer():
                    df_comp = pd.DataFrame({"Time (h)": r['t'], "Wild Type": r['G_wt'],
                                            "Mutant (AI)": r['G_mut']})
                    fig = px.line(df_comp, x="Time (h)", y=["Wild Type", "Mutant (AI)"],
                                  title="Glucose Production (mM)",
                                  color_discrete_map={"Wild Type": "#9CA3AF", "Mutant (AI)": "#10B981"})
                    add_literature_band(fig, r['Cel0'])
                    fig.update_layout(margin=dict(l=0, r=0, t=30, b=0),
                                      paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                                      font=dict(family='Inter, sans-serif'),
                                      yaxis=dict(showgrid=True, gridcolor='#F3F4F6'),
                                      legend=dict(orientation="h", yanchor="bottom", y=1.02,
                                                  xanchor="right", x=1))
                    st.plotly_chart(fig, use_container_width=True)
                    m1, m2, m3, m4 = st.columns(4)
                    with m1:
                        stats_card("Time→80% (WT)", f"{r['time_wt_80']:.1f}h" if r['time_wt_80'] else "N/A", "")
                    with m2:
                        stats_card("Time→80% (Mut)", f"{r['time_mut_80']:.1f}h" if r['time_mut_80'] else "N/A", "")
                    with m3:
                        red = r.get('time_reduction_pct', 0)
                        stats_card("Time Reduction", f"-{red:.0f}%" if red > 0 else "0%", "Faster",
                                   variant="success" if red > 0 else "default")
                    with m4:
                        stats_card("Final Conversion", f"{r['eff_mut']/r['Cel0']*100:.0f}", "% (Mut)")
                render_sources_panel([("EG", wt['eg_id']), ("CBH", wt['cbh_id']), ("BG", wt['bg_id'])])
                st.caption("Mutant is an AI-generated in-silico variant (no experimental measurement).")
