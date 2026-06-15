# Literature Kinetics — Provenance Ledger

This file is the evidence ledger for every literature-sourced kinetic value used
by LUFFY. Its purpose is to let a reader (and the app's users) confirm that each
`kcat`/`Km` stored in `literature_kinetics.csv` is **the value reported in the
cited paper**. `tests/test_literature_provenance.py` asserts that the CSV values
equal the figures documented here (relative error ≤ 1 %).

## Verification status & how values were obtained

- The figures below were obtained via **web search that quotes the source
  papers**. The current execution environment's network policy **blocks
  WebFetch to publishers / PMC / EBI (all return HTTP 403)**, so I could not yet
  open the full-text PDFs/tables to transcribe values verbatim.
- **Agreed next step (user decision):** re-create the session with a network
  policy that permits publisher/PMC/DOI domains, then open each DOI, transcribe
  the exact table/figure value **verbatim** into the "Verbatim quote" field, add
  a second corroborating source (BRENDA/SABIO-RK entry id), and flip
  `verification_status` to `full-text confirmed`.
- **Rule:** any value that cannot be confirmed against full text is **not
  adopted** in the frozen dataset.

Each entry records: enzyme, the reported value, units, substrate, assay
conditions, source + DOI/PMID, and a TODO for the verbatim quote.

---

## EG — Endoglucanase

### GUN2_THEFU — *Thermobifida fusca* endo-β-1,4-glucanase (Cel5A)
- **Reported:** specific activity **48.7 IU/mg** (= µmol·min⁻¹·mg⁻¹); **Km = 5.1 mg/mL** on **CMC**.
- **Conditions:** ~50 °C, pH ~6 (thermophile; t_opt ~60 °C).
- **Source:** Yang et al. (2013), "Heterologous expression and biochemical
  characterization of an endo-β-1,4-glucanase from *Thermobifida fusca*."
  **PMID 23631559**. DOI: _to confirm in full-text pass._
- **Normalization:** `kcat_per_s = SA × MW / 60 = 48.7 × 46 / 60 ≈ 37.3 s⁻¹`
  (MW ≈ 46 kDa catalytic). CMC is polymeric → reported Km kept as apparent
  (g/L); the model converts to glucose-equivalent apparent Km.
- **Verification status:** `search-sourced; full-text confirm pending`.
- **TODO (full-text):** verbatim quote of SA and Km from the paper's Results/Table.

---

## CBH — Cellobiohydrolase

### GUX1_HYPJE — *Trichoderma reesei* cellobiohydrolase Cel7A (CBH I), UniProt P62694
- **Reported:** **kcat ≈ 0.02 s⁻¹**; **apparent Km ≈ 3–5 g/L** on **Avicel
  (crystalline cellulose)** (CSV stores midpoint 3.5 g/L).
- **Source:** Kurasin & Väljamäe (2011), *J. Biol. Chem.*,
  **DOI 10.1074/jbc.M111.269134**; corroborated by Praestgaard et al. (2011),
  *FEBS J.* Both report TrCel7A turnover on crystalline cellulose ~10⁻² s⁻¹.
- **Note:** Not present in `oed_100.csv` (which holds only EC 3.2.1.4
  endoglucanases) → **added as a new enzyme**. Sequence (P62694) to be fetched
  in the network-enabled pass. Insoluble substrate → Km kept as apparent g/L.
- **Significance:** real CBH turnover on crystalline cellulose (~0.02 s⁻¹) is
  ~25–125× **lower** than the project's previous anchor kcat (0.5–2.5 s⁻¹),
  which conflated soluble and insoluble substrate kinetics.
- **Verification status:** `search-sourced; full-text confirm pending`.
- **TODO (full-text):** verbatim kcat & Km(app) from the paper.

---

## BG — β-glucosidase

### BGL1_ASPNG — *Aspergillus niger* β-glucosidase
- **Reported:** **kcat = 2589 s⁻¹**, **Km = 0.24 mM**, **kcat/Km = 10,872
  s⁻¹·mM⁻¹** on **cellobiose**.
- **Source:** "Comparative kinetic analysis of two fungal β-glucosidases,"
  *Biotechnology for Biofuels* (2010) **3:3**, **DOI 10.1186/1754-6834-3-3**,
  **PMID 20181208**.
- **Note:** Not in `oed_100.csv` → **added as new enzyme**. Sequence to fetch.
- **Verification status:** `search-sourced; full-text confirm pending`.
- **TODO (full-text):** verbatim kcat/Km/(kcat/Km) from the paper's kinetics table.

### BGL_ASPFU — *Aspergillus fumigatus* β-glucosidase
- **Reported:** **kcat = 4135 s⁻¹**, **Km = 0.26 mM**, **kcat/Km = 15,712
  s⁻¹·mM⁻¹** on **cellobiose**.
- **Source:** same paper, **DOI 10.1186/1754-6834-3-3**, **PMID 20181208**
  (the "two fungal β-glucosidases" compared).
- **Verification status:** `search-sourced; full-text confirm pending`.
- **TODO (full-text):** verbatim values from the paper.

---

## Calibration benchmark (simulation-vs-literature error standard)

- **Target:** cellulose→glucose conversion **~80 %** at ~15 mg protein/g glucan,
  50 °C, pH 5, 72 h (amorphous/pretreated substrate). Plausible envelope
  **50–92 %**; conversion falls with solids loading.
- **Source:** "Enhancing enzymatic saccharification yields of cellulose at high
  solid loadings…," *Biotechnol. Biofuels Bioprod.* (2024),
  **DOI 10.1186/s13068-024-02485-6** (PMC10924376); corroborating: PMC9985267
  (Avicel 5 FPU/g → 57 % raw / 85 % acid-treated); NREL benchmark
  DOI 10.1186/1754-6834-4-29.
- **Error criterion:** the default WT simulation must satisfy
  `|X_sim(72h) − 0.80| / 0.80 ≤ 0.15` (≤15 % relative error) and lie within the
  50–92 % band. The single accessibility coefficient `alpha` is fit to meet this.
- **TODO (full-text):** confirm the exact conversion % / loading / time used as
  the headline target and cite the specific figure.

---

## Background model references (already cited in docs/blog_luffy.md)
- Jeoh et al. (2017) mechanistic kinetic models review, DOI 10.1002/bit.26277.
- Bansal et al. (2012) cellulose accessibility limitations, PMID 22244954.
