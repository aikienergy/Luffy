# Literature Kinetics — Provenance Ledger

This file is the evidence ledger for every literature-sourced kinetic value used
by LUFFY. Its purpose is to let a reader (and the app's users) confirm that each
`kcat`/`Km` stored in `literature_kinetics.csv` is **the value reported in the
cited paper**. `tests/test_literature_provenance.py` asserts that the reported
CSV values equal the figures documented here (relative error ≤ 1 %).

## Verification status & how values were obtained

- **Status: full-text confirmed.** On **2026-06-15**, in a session whose network
  policy permits NCBI E-utilities, PMC open-access, open-access publishers
  (BMC/ASM/MDPI/Springer-OA), BRENDA and UniProt, every value below was read
  **verbatim from the open-access full text** (table/figure/sentence quoted in
  each entry) and every citation was re-derived from the eutils record (title +
  authors + DOI cross-checked). UniProt sequences were fetched by accession with
  `src/data_engineering/fetch_literature_sequences.py`.
- **Rule:** any value that cannot be confirmed against full text is **not
  adopted**. Values that failed verification were dropped or replaced (see
  "Corrections to the previous pass").
- **Unit handling:** reported values are stored in their original units in
  `literature_kinetics.csv` (`kcat`,`kcat_unit`,`Km`,`Km_unit`) and converted to
  simulator units (1/s, mM) by `src/data_engineering/units.py` (auditable, one
  place). For insoluble/polymeric substrates (Avicel, CMC) the apparent Km is
  expressed as glucose-equivalent mM via `cellulose_gpl_to_glucose_equiv_mM`.

## Corrections to the previous (network-blocked, search-sourced) pass

Full-text checking exposed **systematic citation errors** that this pass fixes:

- **β-glucosidase values were misattributed.** "A. niger kcat 2589 s⁻¹, Km 0.24
  mM" and "A. fumigatus kcat 4135 s⁻¹, Km 0.26 mM" were attributed to
  doi:10.1186/1754-6834-3-3. That paper (Chauve et al. 2010) studies **A. niger
  SP188 and T. reesei BGL1 — not A. fumigatus** — and its cellobiose values
  (Table 3) are **kcat 1897 / 2445 min⁻¹ (= 31.6 / 40.8 s⁻¹)**, i.e. ~60–100×
  lower than the fabricated s⁻¹ figures (a min⁻¹→s⁻¹ misread plus a wrong second
  organism). Replaced with the true Table 3 values.
- **The CBH DOI was wrong.** doi:10.1074/jbc.M111.269134 (cited for "Kurasin &
  Väljamäe 2011") actually indexes an **unrelated autophagy paper** (Farkas et
  al.). The real Kurasin & Väljamäe 2011 DOI is **10.1074/jbc.M110.161059**.
  The adopted steady-state CBH value now comes from Sørensen et al. 2015
  (doi:10.1074/jbc.M115.658930, free in PMC).
- **The EG citation was wrong.** The T. fusca Cel5A paper's authors are **Yan P,
  Su L, Chen J, Wu J** (not "Yang et al.") and its DOI is **10.1002/bab.1097**
  (previously blank).

## Plausibility bands (config.PLAUSIBILITY_BANDS)

The per-class kcat/Km bands in `src/config.py` were re-anchored to the verified
ranges below (BG kcat 1e1–1e4; CBH kcat 5e-3–5; EG kcat 1e-2–1e4). The previous
BG kcat band (1e2–1e4) reflected the inflated, misattributed values and is
corrected.

Each entry records: enzyme id, reported value (verbatim), units, substrate,
assay conditions, source + DOI/PMID/PMCID, and the UniProt accession of the
sequence used for ESM features.

---

## EG — Endoglucanase (EC 3.2.1.4)

### GUN2_THEFU — *Thermobifida fusca* endoglucanase Cel5A (UniProt P26222)
- **Reported (verbatim, abstract):** "Using carboxymethyl cellulose as the
  substrate, the Km and Vmax values were **5.1 mg/mL** and **48.7 IU/mg**,
  respectively." Optimum temperature **80 °C**; maximal activity at **pH 5.5**.
- **Model units:** kcat = SA·MW/60 = 48.7 × 46 kDa / 60 ≈ **37.3 s⁻¹**; CMC is
  soluble-but-polymeric → Km kept as apparent glucose-equivalent mM.
- **Source:** Yan P, Su L, Chen J, Wu J (2013), *Biotechnol. Appl. Biochem.*
  60(3):348–55. **doi:10.1002/bab.1097**, **PMID 23631559**.
- **Sequence:** UniProt **P26222** (also present in `oed_100.csv`).

### CELD_PIRFI — *Piromyces finnis* endoglucanase CelD (GH5; UniProt A0A1Y1V643)
- **Reported (verbatim, abstract & Table 3):** "kcat = **6.0 ± 0.6 s⁻¹** and
  Km = **7.6 ± 2.1 g/L CMC**." (Mesophilic anaerobic gut fungus; assay 39 °C, pH 5.5.)
- **Source:** Dementiev A, *et al.* (2023), *Appl. Microbiol. Biotechnol.*
  **doi:10.1007/s00253-023-12684-0**, **PMID 37548665**, **PMC10485095**.
- **Sequence:** UniProt **A0A1Y1V643** (full-length 1192 aa; kinetics on the GH5
  catalytic domain).

### NFEG12A_ASPFI — *Aspergillus (Neosartorya) fischeri* GH12 endoglucanase NfEG12A (UniProt A0A1L6CE30)
- **Reported (verbatim, Table 2, wild type):** on **CMC-Na** "kcat (/s) **1,721 ±
  69**", "Km (mg/ml) **6.54 ± 0.41**"; on lichenin kcat 4,389 /s, Km 1.46 mg/ml.
  Assay 65 °C, pH 5.0 (thermophilic/acidophilic; opt 65 °C/pH 5.0).
- **Source:** Yang H, *et al.* (2017), *Appl. Environ. Microbiol.*
  **doi:10.1128/AEM.03123-16**, **PMID 28039140**, **PMC5335522**.
- **Sequence:** UniProt **A0A1L6CE30** (234 aa). High soluble-substrate turnover;
  loop-engineering variants in the paper are **not** adopted.

### ACEL12B_ACICE — *Acidothermus cellulolyticus* 11B GH12 endoglucanase AcCel12B (UniProt A0LSI2)
- **Reported (verbatim):** "The Km and Vmax of AcCel12B for CMC were **25.47
  mg·mL⁻¹** and **131.75 U·mg⁻¹**, respectively." Assay 70 °C, pH 4.5 (opt 75 °C).
- **Model units:** kcat = Vmax·MW/60 = 131.75 × 38.3 kDa / 60 ≈ **84 s⁻¹**
  (derived from the reported specific-activity Vmax via `units.py`).
- **Source:** Wang J, *et al.* (2015), *Int. J. Mol. Sci.* 16(10):25080–95.
  **doi:10.3390/ijms161025080**, **PMID 26506341**, **PMC4632791**.
- **Sequence:** UniProt **A0LSI2** (403 aa). Bacterial GH12, distinct from the
  better-known Acidothermus E1/Cel5A (P54583).

---

## CBH — Cellobiohydrolase (EC 3.2.1.91)

### GUX1_TRIRF — *Trichoderma reesei* cellobiohydrolase Cel7A / CBH I (UniProt P62694)
- **Reported (verbatim, Table 1, "HjCBM"):** steady-state pVmax/E0 = **24 ± 1**
  (×10⁻³ s⁻¹) → **kcat = 0.024 s⁻¹** at 10 °C (0.080 s⁻¹ at 25 °C); pKm = **2.8 ±
  0.3 g/L** on **Avicel** (microcrystalline cellulose), 50 mM acetate pH 5.0.
- **Source:** Sørensen TH, Cruys-Bagger N, Windahl MS, Badino SF, Borch K, Westh
  P (2015), *J. Biol. Chem.* 290:22193. **doi:10.1074/jbc.M115.658930**,
  **PMID 26183777**, **PMC4571970**.
- **Context:** This is the canonical "~0.02 s⁻¹, Km a few g/L" **steady-state**
  turnover on crystalline cellulose. The *intrinsic* per-catalytic-step kcat is
  ~1.8–4 s⁻¹ (Kurasin & Väljamäe 2011, **doi:10.1074/jbc.M110.161059**,
  PMID 21051539, PMC3012971; Cruys-Bagger et al. 2012,
  doi:10.1074/jbc.M111.334946, PMID 22493488, PMC3365755), but slow dissociation
  (koff ≈ 0.022 s⁻¹) makes steady-state turnover ~10–25× lower — the simulator
  uses the steady-state value. Real CBH turnover (~0.02 s⁻¹) is ~25–125× **lower**
  than the project's original anchor (0.5–2.5 s⁻¹), which conflated soluble and
  insoluble substrate kinetics.
- **Sequence:** UniProt **P62694** (513 aa, EC 3.2.1.91).

### CBH1_RASEM — *Rasamsonia (Talaromyces) emersonii* Cel7A cellobiohydrolase (UniProt Q8TFL9)
- **Reported (verbatim, Table 1, "ReCORE"):** steady-state pVmax/E0 = **22 ± 1**
  (×10⁻³ s⁻¹) → **kcat = 0.022 s⁻¹** at 10 °C (0.067 s⁻¹ at 25 °C); pKm = **4.9 ±
  0.6 g/L** on **Avicel**, pH 5.0.
- **Source:** Sørensen TH, *et al.* (2015) — same study/table as GUX1_TRIRF
  (**doi:10.1074/jbc.M115.658930**, **PMID 26183777**, **PMC4571970**),
  directly comparable. Thermophilic, naturally CBM-less (catalytic domain only).
- **Sequence:** UniProt **Q8TFL9** (455 aa; gene *cbh1*/Cel7A, PDB 1Q9H/3PFJ;
  entry unreviewed so EC auto-annotated 3.2.1.-, function assigned 3.2.1.91).

---

## BG — β-glucosidase (EC 3.2.1.21), on cellobiose

### BGL1_ASPNG — *Aspergillus niger* β-glucosidase (SP188 / BglA; UniProt A2RAL4)
- **Reported (verbatim, Table 3, cellobiose):** kcat = **1897 ± 95 min⁻¹**
  (= **31.6 s⁻¹**), Km = **0.88 mM**, Kp (competitive glucose inhibition) =
  **3.40 mM**; 50 °C, pH 4.8.
- **Source:** Chauve M, Mathis H, Huc D, Casanave D, Monot F, Lopes Ferreira N
  (2010), *Biotechnol. Biofuels* 3:3. **doi:10.1186/1754-6834-3-3**,
  **PMID 20181208**, **PMC2847552**.
- **Sequence:** UniProt **A2RAL4** (860 aa) — A. niger reference-strain *bglA*
  ortholog (the commercial Novozymes **SP188** protein is not sequence-deposited).

### BGL1_TRIRF — *Trichoderma reesei* β-glucosidase BGL1 / Cel3A (UniProt Q12715)
- **Reported (verbatim, Table 3, cellobiose):** kcat = **2445 ± 107 min⁻¹**
  (= **40.8 s⁻¹**), Km = **1.36 mM**; 50 °C, pH 4.8.
- **Source:** Chauve et al. 2010 (**doi:10.1186/1754-6834-3-3**, **PMID 20181208**,
  **PMC2847552**) — same study as BGL1_ASPNG.
- **Sequence:** UniProt **Q12715** (744 aa, GH3 *bgl1*/cel3A).

### BGLA_ASPFU — *Aspergillus fumigatus* β-glucosidase Bgl3 / Cel3A (UniProt Q4WJJ3)
- **Reported (verbatim, Table 5, cellobiose):** native nBgl3 kcat = **80.30 s⁻¹**,
  Km = **1.75 ± 0.17 mM** (recombinant rBgl3 114.60 s⁻¹, 2.20 mM); kinetic assay
  pH 5.0 / 50 °C; opt 60 °C / pH 6.0.
- **Source:** Liu D, Zhang R, Yang X, Zhang Z, Song S, Miao Y, Shen Q (2012),
  *Microb. Cell Fact.* 11:25. **doi:10.1186/1475-2859-11-25**, **PMID 22340848**,
  **PMC3312866**.
- **Sequence:** UniProt **Q4WJJ3** (873 aa) — Af293 reference ortholog (study
  strain Z5).

### BGLA_THEMA — *Thermotoga maritima* MSB8 β-glucosidase BglA (GH1; UniProt Q08638)
- **Reported (verbatim, Table 2, cellobiose):** kcat = **55.6 s⁻¹**, Km = **22.3
  mM**, kcat/Km = 2.5 s⁻¹·mM⁻¹; 75 °C, pH 6.8.
- **Source:** ten Kate GA, Sanders P, Dijkhuizen L, van Leeuwen SS (2024),
  *Appl. Microbiol. Biotechnol.* **doi:10.1007/s00253-024-13183-6**,
  **PMID 38809317**, **PMC11136819**.
- **Sequence:** UniProt **Q08638** (446 aa). Hyperthermophile; high cellobiose Km
  is consistent with this enzyme's broader specificity.

---

## Calibration benchmark (simulation-vs-literature error standard)

- **Target:** cellulose→glucose conversion **~80 %** at ~15 mg protein/g glucan,
  50 °C, pH 5, 72 h (amorphous/pretreated substrate). Plausible envelope
  **50–92 %**; conversion falls with solids loading.
- **Source:** "Enhancing enzymatic saccharification yields of cellulose at high
  solid loadings…," *Biotechnol. Biofuels Bioprod.* (2024),
  **doi:10.1186/s13068-024-02485-6** (PMC10924376); corroborating: PMC9985267
  (Avicel 5 FPU/g → 57 % raw / 85 % acid-treated); NREL benchmark
  doi:10.1186/1754-6834-4-29.
- **Error criterion:** the default WT simulation must satisfy
  `|X_sim(72h) − 0.80| / 0.80 ≤ 0.15` (≤15 % relative error) and lie within the
  50–92 % band. The single accessibility coefficient `alpha` is fit to meet this
  (`src/data_engineering/calibrate_model.py`; result in `calibration.json`).
  Reference cocktail = first Literature EG/CBH/BG = GUN2_THEFU / GUX1_TRIRF /
  BGL1_ASPNG.

## Non-literature kinetics tiers (AI-predicted & estimated)

The enzyme universe is the balanced harvested set (EG/CBH/BG, `data/raw/
oed_harvested.csv`) plus these 10 verified literature anchors and an LPMO
control. Enzymes **not** in the literature table get kinetics from one of two
clearly-labelled lower tiers (`source_type` / `kinetics_source` columns):

- **AI-predicted** — `kcat` from **DLKcat** sequence+substrate predictions
  (`data/external/dlkcat_predictions.csv`); `Km` remains the sequence heuristic
  (CatPred Km predictions are not bundled; `scripts/run_catpred_km.py` documents
  the reproduction step, which needs the external library).
- **Estimated** — pure sequence heuristic (`Biophysical_Model_v2`) for enzymes
  DLKcat did not cover.

Only the **Literature** tier above is full-text confirmed; the AI-predicted and
estimated tiers are explicitly surfaced as such in the app (badge + provenance
panel) and are **never** treated as measurements. The calibration reference
cocktail is drawn only from the Literature tier, so the calibrated model is
anchored to verified values regardless of the AI/estimated rows.

## Background model references (also cited in docs/blog_luffy.md)
- Jeoh et al. (2017) mechanistic kinetic models review, doi:10.1002/bit.26277.
- Bansal et al. (2012) cellulose accessibility limitations, PMID 22244954.
- Keller et al. (2020) cellulase kinetics review (states the ~0.02 s⁻¹ / 3–5 g/L
  Cel7A figure citing Sørensen 2015), *Biotechnol. Biofuels*, PMC7350674.

---

# Substrate-property layer — Provenance ledger (real-biomass model)

The real-biomass model (`src/validation/validator.py`: lignin inhibition x
geometric accessibility) adds a second class of constants. A full-text audit of
this layer (2026-06-16, network-permissive session: NCBI E-utilities, PMC,
publishers, UniProt) found the same failure mode the kinetics audit found —
**"sourced" ≠ "correct"** — and applies the same discipline. Every constant is
tagged **[MEASURED]** (verbatim from full text) or **[PARAMETER]**
(structural/assumed; if fit to data, "calibrated"). A [PARAMETER] is never shown
to the user as a measurement.

## Corrections to the previous (search-sourced) pass

Full-text checking exposed **systematic citation errors** in the inhibition /
adsorption constants — every supplied DOI resolved to an unrelated paper:

- **All three inhibition-constant Ki values are NOT measurements.** `ki_phenol`,
  `ki_furfural`, `ki_hmf` had no full-text support as a Michaelis Ki in mM. The
  primary literature reports phenol/furan effects as **% deactivation or
  mg-protein ratios, not a Ki** (e.g. Ximenes 2011: phenolics "caused 20–80%
  deactivation of cellulases and/or β-glucosidases after 24 h of
  pre-incubation"). → reclassified **[PARAMETER]**.
- **Furfural/HMF were misattributed to Ximenes et al. (2010).** That paper is
  about **phenols** and does not study furans. The furan-relevant primary source
  is **Kim et al. (2011)**, which finds **phenolics — not furans — are the
  inhibitory cause**; furans are comparatively **weak** cellulase inhibitors. The
  pre-correction ordering (furfural `Ki=2` "stronger" than phenol `Ki=8`)
  **contradicted the literature**; the model now uses `ki_furfural`,`ki_hmf` >>
  `ki_phenol` (test-gated).
- **Three DOIs were wrong** (each resolved to an unrelated article) and are
  corrected below.
- **The lignin-hydrophobicity rationale was biologically inverted.** The code
  said "softwood = high syringyl content → strong adsorption". Softwood is in
  fact **guaiacyl-rich (low S/G)**, and it is **low S/G (high guaiacyl)** that
  drives strong adsorption (Yu et al. 2014: "the lower the S/G ratio, the higher
  affinity… G lignin had a higher adsorption capacity… than syringyl (S)
  lignin"). The rank order softwood > hardwood > grass is kept; the rationale is
  rewritten and the magnitudes documented as an assumed ordinal **[PARAMETER]**.

## Inhibition / adsorption / accessibility constants (`src/config.py`)

| Constant | Value | Tag | Basis |
|---|---|---|---|
| `ki_phenol` | 8.0 mM | [PARAMETER] | phenolics potent (small Ki). Mechanism: Ximenes et al. 2010, *Enzyme Microb Technol* 46(3-4):170, **doi:10.1016/j.enzmictec.2009.11.001**; 2011, 48(1):54, **doi:10.1016/j.enzmictec.2010.09.006**, PMID 22112771. No Ki in mM is reported. |
| `ki_furfural` | 50 mM | [PARAMETER] | furans weak (large Ki). Kim et al. 2011, *Enzyme Microb Technol* 48(4-5):408, **doi:10.1016/j.enzmictec.2011.01.007**, PMID 22112958. |
| `ki_hmf` | 60 mM | [PARAMETER] | HMF weaker still; same source. |
| `k_ads` | calibrated | [PARAMETER, calibrated] | Langmuir lignin-adsorption constant; fit by `calibrate_biomass.py` to literature yield bands → `biomass_calibration.json`. |
| `HYDROPHOBICITY_INDEX` (0.85/0.65/0.50) | assumed ordinal | [PARAMETER] | rank order only (softwood > hardwood > grass). Li & Zheng 2017, *Biotechnol Adv* 35(4):466, **doi:10.1016/j.biotechadv.2017.03.010**, PMID 28351654; primary Yu et al. 2014, *Biotechnol Biofuels* 7:38, **PMC3995585**. |
| `d_ref`, `exponent` (accessibility) | calibrated | [PARAMETER, calibrated] | surface-accessibility law; qualitatively per Alvira et al. 2010, **doi:10.1016/j.biortech.2009.11.093**; fit by `calibrate_biomass.py`. |

## Biomass composition (`src/resources/materials.py`) — [MEASURED]

| Biomass | Cellulose/Hemi/Lignin (rep. % dw) | Source (DOI) |
|---|---|---|
| Rice straw | 35 / 24 / 17 (ash ~14) | Binod et al. 2010, *Bioresour Technol* 101(13):4767, **doi:10.1016/j.biortech.2009.10.079**, PMID 19944601 |
| Wheat straw | 35 / 24 / 17 | Alvira et al. 2010, **doi:10.1016/j.biortech.2009.11.093** (Table 1 from Sun & Cheng 2002, doi:10.1016/S0960-8524(01)00212-7) |
| Corn stover | 37 / 21 / 18 | Templeton et al. 2010, *J Agric Food Chem* 58(16):9054, **doi:10.1021/jf100807b**, PMC2923869; NREL TP-510-32438 |
| Sugarcane bagasse | 45 / 27 / 22 | Pandey et al. 2000, *Bioresour Technol* 74(1):69, **doi:10.1016/S0960-8524(99)00142-X** |
| Spent coffee grounds | 12 / 39 / 24 (protein ~17) | Ballesteros et al. 2014, *Food Bioprocess Technol* 7(12):3493, **doi:10.1007/s11947-014-1349-z** |

## Rice-straw saccharification yield bands (`PRETREATMENT_PRESETS`) — [MEASURED], verbatim

Replaces the prior journal-name-only "sources" (unverifiable). These bands are
the calibration targets for `calibrate_biomass.py`.

- **Simple crushing / mechanical — band 0.30–0.45.** Yu et al. (2024), *Agronomy*
  14(11):2550, **doi:10.3390/agronomy14112550** (OA). Verbatim: "…the 36.24%
  yield from untreated straw… the 73.25% yield from ball milled straw."
- **Dilute acid — band 0.60–0.75.** Agrawal et al. (2018), *Front Energy Res*
  6:115, **doi:10.3389/fenrg.2018.00115** (OA). Verbatim: "the highest glucan
  conversion obtained was 66% after 30 h… improved to 70%… 72%…" (~84% at low
  solids).
- **Hydrothermal / LHW — band 0.80–0.90.** Yu G. et al. (2010), *Appl Biochem
  Biotechnol* 160(2):539, **doi:10.1007/s12010-008-8420-z**, PMID 19125228.
  Verbatim: "The glucose yield by enzymatic hydrolysis of pretreated rice straw
  was no less than 85% at 180 °C and above for 30-min pretreatment."
- **Steam explosion — band 0.85–1.00.** Wood et al. (2016), *Biotechnol Biofuels*
  9:193, **doi:10.1186/s13068-016-0599-6**, PMC5011935 (OA); Semwal et al.
  (2019), *Biomass Bioenergy* 130:105390, **doi:10.1016/j.biombioe.2019.105390**.
  Verbatim: "…steam explosion at 210 °C for 10 min… virtually all of the
  measurable glucose… was released."

## Calibration of the substrate-property model (`biomass_calibration.json`)

The three structural [PARAMETER, calibrated] constants `{k_ads, d_ref,
exponent}` are fit by `src/data_engineering/calibrate_biomass.py` so the
predicted cellulose→glucose conversion of the rice-straw pretreatment series
lands inside each band above (3 parameters vs 4 grounded bands). Because
`bio_factor ≤ 1` and the accessibility `alpha` is calibrated so `bio_factor=1.0`
→ ~0.80 conversion, the model has a ~0.79 conversion **ceiling**; the most severe
pretreatments (LHW/steam, lit. ≥85%) saturate to that ceiling, which is reported
honestly as "ceiling-limited", not gamed. Pretreatment `severity` (0–1) is a
calibrated normalised effectiveness input ordered to the verified yield series
(it is **not** a measured combined-severity factor). The fit is regenerated with
`python -m src.data_engineering.calibrate_biomass`.

## Verification status (substrate-property layer)
- **[MEASURED]:** biomass composition and the rice-straw yield bands are
  full-text confirmed with primary DOIs (above).
- **[PARAMETER]:** all inhibition Ki, lignin-hydrophobicity indices, and the
  geometric/adsorption constants are calibrated/assumed model parameters — **not
  measurements** — and are surfaced as such in the app and tests
  (`tests/test_plausibility.py`, `tests/test_biomass_calibration.py`).
