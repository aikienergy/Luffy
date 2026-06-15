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

## Background model references (also cited in docs/blog_luffy.md)
- Jeoh et al. (2017) mechanistic kinetic models review, doi:10.1002/bit.26277.
- Bansal et al. (2012) cellulose accessibility limitations, PMID 22244954.
- Keller et al. (2020) cellulase kinetics review (states the ~0.02 s⁻¹ / 3–5 g/L
  Cel7A figure citing Sørensen 2015), *Biotechnol. Biofuels*, PMC7350674.
