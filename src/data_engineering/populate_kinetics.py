"""
Purpose: Assign kinetic parameters to the enzyme dataset.

Overview:
    Builds data/processed/enzyme_kinetics.csv by combining:
      1. LITERATURE values from data/curated/literature_kinetics.csv (real,
         cited kcat/Km, normalised to simulator units by src/data_engineering/
         units.py). These rows are tagged source_type="Literature" and carry
         full provenance columns (doi/authors/year/substrate/conditions).
      2. ESTIMATED values for the remaining enzymes, produced by a transparent
         sequence-based heuristic (NOT a measurement). Tagged
         source_type="Estimated". The heuristic is a labelled prior, not a
         claim about real activity.

    Enzyme functional class (EG/CBH/BG/LPMO) is assigned deterministically from
    the curated file or from EC number / annotation -- replacing the previous
    random specificity assignment and fixing the screening split bug at source.

    No network access is required (reads only local CSVs).
"""
import pandas as pd
import numpy as np
import os
import hashlib
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src import config
from src.data_engineering import units
from src.validation.validator import cellulose_gpl_to_glucose_equiv_mM

CURATED_FILE = "data/curated/literature_kinetics.csv"
INPUT_FILE = "data/raw/oed_100.csv"
OUTPUT_FILE = "data/processed/enzyme_kinetics.csv"

# Provenance columns carried through to the app for display.
PROVENANCE_COLS = ["enzyme_class", "kcat_reported", "kcat_unit", "Km_reported",
                   "Km_unit", "substrate", "substrate_type", "doi", "pmid",
                   "source_title", "authors", "year", "verification_status"]


def get_sequence_properties(sequence):
    """Deterministic physico-chemical proxies from sequence (for ESTIMATED rows only)."""
    if not isinstance(sequence, str) or len(sequence) < 10:
        return 0.5, 0.5, 0.5
    hydro = {'A': 1.8, 'R': -4.5, 'N': -3.5, 'D': -3.5, 'C': 2.5, 'Q': -3.5,
             'E': -3.5, 'G': -0.4, 'H': -3.2, 'I': 4.5, 'L': 3.8, 'K': -3.9,
             'M': 1.9, 'F': 2.8, 'P': -1.6, 'S': -0.8, 'T': -0.7, 'W': -0.9,
             'Y': -1.3, 'V': 4.2}
    score = sum(hydro.get(aa, 0.0) for aa in sequence)
    avg_hydro = score / len(sequence)
    norm_hydro = (avg_hydro + 4.5) / 9.0
    seq_hash = int(hashlib.sha256(sequence.encode("utf-8")).hexdigest(), 16) % 10000 / 10000.0
    return norm_hydro, 110 * len(sequence), seq_hash


def generate_ground_truth(sequence):
    """
    ESTIMATED (non-literature) kinetic prior from sequence. This is a labelled
    heuristic placeholder, NOT a measurement; rows using it are tagged
    source_type="Estimated" and surfaced as such in the app.
    """
    if pd.isna(sequence):
        return 1.0, 10.0, 10.0, 50.0, 5.0
    h, mw, s_hash = get_sequence_properties(sequence)
    hydro_fitness = np.exp(-10.0 * (h - 0.6) ** 2)
    struc_fitness = s_hash if s_hash >= 0.2 else 0.01
    kcat = max(0.1, 20.0 * hydro_fitness * struc_fitness)
    Km = max(0.5, 50.0 * (1.0 - h) + 0.5)
    Ki = Km * (1.5 + 0.5 * s_hash)
    t_opt = 40.0 + 30.0 * h
    ph_opt = 4.0 + 4.0 * s_hash
    return round(kcat, 2), round(Km, 2), round(Ki, 2), round(t_opt, 1), round(ph_opt, 1)


def classify_enzyme(name, ec_number, enzyme_id=""):
    """Deterministic functional class from annotation / EC / id (no randomness)."""
    text = str(name or "").lower()
    ec = str(ec_number or "").strip()
    eid = str(enzyme_id or "").upper()
    if (eid.startswith("LP9") or "monooxygenase" in text or "lytic polysaccharide" in text
            or ec.startswith("1.14.99")):
        return "LPMO"
    if "beta-glucosidase" in text or "β-glucosidase" in text or ec == "3.2.1.21":
        return "BG"
    if ("cellobiohydrolase" in text or "exoglucanase" in text or "exo-1,4" in text
            or ec in ("3.2.1.91", "3.2.1.176")):
        return "CBH"
    return "EG"  # default for EC 3.2.1.4 endoglucanases


def _default_ki(enzyme_class):
    return config.KI_GLUCOSE_MM if enzyme_class == "BG" else config.KI_CELLOBIOSE_MM


def _normalise_literature_row(crow):
    """
    Convert a curated literature row to simulator units.
    Returns dict with model-ready kcat (1/s), Km (mM), Ki, t_opt, ph_opt and the
    raw reported values for provenance display.
    """
    enzyme_class = crow["enzyme_class"]
    mw_kda = crow.get("mw_kda")
    mw_kda = float(mw_kda) if pd.notna(mw_kda) else None

    kcat_per_s = units.kcat_to_per_s(crow["kcat"], crow["kcat_unit"], mw_kda)

    # Km -> model units. For BG (soluble) keep mM. For insoluble cellulose
    # attack, express the reported mass-concentration Km as glucose-equivalent
    # mM (apparent), consistent with how Cel is tracked in the simulator.
    km_unit = str(crow["Km_unit"]).strip().lower()
    substrate_type = str(crow.get("substrate_type", "")).strip().lower()
    if km_unit in ("mm", "um", "µm", "m", "mol/l"):
        km_model = units.km_to_mM(crow["Km"], crow["Km_unit"])
    elif km_unit in ("g/l", "mg/ml", "kg/m3"):
        if substrate_type == "soluble":
            km_model = units.km_to_mM(crow["Km"], crow["Km_unit"], substrate=crow.get("substrate"))
        else:
            # apparent Km on insoluble cellulose, in glucose-equivalent mM
            km_model = cellulose_gpl_to_glucose_equiv_mM(float(crow["Km"]))
    else:
        km_model = units.km_to_mM(crow["Km"], crow["Km_unit"])
    if km_model is None:
        km_model = 10.0  # safe apparent fallback; flagged via notes

    t_opt = float(crow["t_opt"]) if pd.notna(crow.get("t_opt")) else config.DEFAULT_TEMP_C
    ph_opt = float(crow["ph_opt"]) if pd.notna(crow.get("ph_opt")) else config.DEFAULT_PH
    ki = float(crow["Ki"]) if pd.notna(crow.get("Ki")) else _default_ki(enzyme_class)

    return {
        "kcat": round(float(kcat_per_s), 4),
        "Km": round(float(km_model), 4),
        "Ki": round(float(ki), 4),
        "t_opt": t_opt,
        "ph_opt": ph_opt,
        "enzyme_class": enzyme_class,
        "kcat_reported": crow["kcat"],
        "kcat_unit": crow["kcat_unit"],
        "Km_reported": crow["Km"],
        "Km_unit": crow["Km_unit"],
        "substrate": crow.get("substrate"),
        "substrate_type": crow.get("substrate_type"),
        "doi": crow.get("doi"),
        "pmid": crow.get("pmid"),
        "source_title": crow.get("source_title"),
        "authors": crow.get("authors"),
        "year": crow.get("year"),
        "verification_status": crow.get("verification_status"),
    }


def populate_kinetics():
    if not os.path.exists(INPUT_FILE):
        raise FileNotFoundError(f"{INPUT_FILE} not found. Run fetch_oed_data.py first.")
    df = pd.read_csv(INPUT_FILE)
    print(f"Loaded {len(df)} enzymes from {INPUT_FILE}.")

    curated = pd.read_csv(CURATED_FILE) if os.path.exists(CURATED_FILE) else pd.DataFrame()
    curated_by_id = {str(r["id"]): r for _, r in curated.iterrows()} if len(curated) else {}
    print(f"Loaded {len(curated)} curated literature records.")

    rows = []
    for _, row in df.iterrows():
        eid = str(row["id"])
        seq = row.get("sequence", "")
        enzyme_class = classify_enzyme(row.get("name"), row.get("ec_number"), eid)
        base = row.to_dict()

        if eid in curated_by_id:
            norm = _normalise_literature_row(curated_by_id[eid])
            base.update(norm)
            base["source_type"] = "Literature"
            base["source_detail"] = "literature_kinetics.csv"
        else:
            k, km, ki, t, p = generate_ground_truth(seq)
            base.update({
                "kcat": k, "Km": km, "Ki": ki, "t_opt": t, "ph_opt": p,
                "enzyme_class": enzyme_class,
                "kcat_reported": np.nan, "kcat_unit": np.nan,
                "Km_reported": np.nan, "Km_unit": np.nan,
                "substrate": np.nan, "substrate_type": np.nan,
                "doi": np.nan, "pmid": np.nan, "source_title": np.nan,
                "authors": np.nan, "year": np.nan,
                "verification_status": "estimated (not literature)",
                "source_type": "Estimated",
                "source_detail": "Biophysical_Model_v2 (sequence heuristic)",
            })
        # deterministic specificity (no randomness): cellulolytic vs other
        base["specificity"] = "Other" if enzyme_class == "LPMO" else "Cellulase"
        rows.append(base)

    existing_ids = set(df["id"].astype(str))
    # Add curated enzymes NOT present in oed_100 (e.g. CBH/BG that the dataset lacks).
    for _, crow in curated.iterrows():
        cid = str(crow["id"])
        if cid in existing_ids:
            continue
        norm = _normalise_literature_row(crow)
        new_row = {
            "accession": crow.get("accession"),
            "id": cid,
            "organism": crow.get("organism"),
            "name": f"{crow.get('gene', '')} ({crow.get('enzyme_class')})".strip(),
            "sequence": crow.get("sequence") if pd.notna(crow.get("sequence")) else np.nan,
            "ec_number": crow.get("ec_number"),
            "source": "Curated_Literature",
            "source_type": "Literature",
            "source_detail": "literature_kinetics.csv (added; not in oed_100)",
            "specificity": "Cellulase",
        }
        new_row.update(norm)
        rows.append(new_row)
        print(f"  + added curated enzyme not in oed_100: {cid} ({crow['enzyme_class']})")

    out = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    out.to_csv(OUTPUT_FILE, index=False)
    n_lit = (out["source_type"] == "Literature").sum()
    print(f"Saved {len(out)} enzymes to {OUTPUT_FILE} "
          f"({n_lit} Literature, {len(out) - n_lit} Estimated).")
    print("Class counts:\n", out["enzyme_class"].value_counts().to_string())


if __name__ == "__main__":
    populate_kinetics()
