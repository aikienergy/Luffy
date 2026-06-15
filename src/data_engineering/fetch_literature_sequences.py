"""
Purpose: Populate the `sequence` column of data/curated/literature_kinetics.csv
         with canonical protein sequences fetched from UniProt by accession.

Overview:
    The literature ledger (literature_kinetics.csv) is hand-curated with each
    enzyme's UniProt `accession` and full provenance, but the `sequence` field is
    left empty so that sequences are pulled reproducibly from the authoritative
    source rather than pasted by hand. This script fetches each missing sequence
    from the UniProt REST API and writes it back into the CSV.

    Design rule: FAIL LOUD (consistent with src/data_engineering/units.py). A row
    that has an accession but whose sequence cannot be retrieved raises, rather
    than silently leaving a blank that would later become a zero ESM embedding.

    Requires network access to rest.uniprot.org. Re-running is idempotent: rows
    that already carry a sequence are skipped unless --force is given.
"""
import argparse
import sys
import time
from urllib.request import urlopen
from urllib.error import URLError, HTTPError

import pandas as pd

CURATED_FILE = "data/curated/literature_kinetics.csv"
UNIPROT_FASTA = "https://rest.uniprot.org/uniprotkb/{acc}.fasta"


def fetch_sequence(accession, retries=4):
    """Return the one-letter amino-acid sequence for a UniProt accession."""
    url = UNIPROT_FASTA.format(acc=accession.strip())
    last_err = None
    for attempt in range(retries):
        try:
            with urlopen(url, timeout=30) as resp:
                text = resp.read().decode("utf-8")
            lines = [ln.strip() for ln in text.splitlines() if ln and not ln.startswith(">")]
            seq = "".join(lines)
            if len(seq) < 10:
                raise ValueError(f"UniProt returned an empty/short sequence for {accession!r}")
            return seq
        except (URLError, HTTPError, ValueError) as exc:  # transient network or empty body
            last_err = exc
            time.sleep(2 ** attempt)
    raise RuntimeError(f"Failed to fetch sequence for {accession!r}: {last_err}")


def fetch_literature_sequences(force=False):
    df = pd.read_csv(CURATED_FILE)
    if "sequence" not in df.columns:
        df["sequence"] = ""
    # An all-empty column is inferred as float64 (NaN); force object so we can
    # store sequence strings without a dtype clash.
    df["sequence"] = df["sequence"].astype("object")

    n_fetched = 0
    for i, row in df.iterrows():
        acc = row.get("accession")
        have = isinstance(row.get("sequence"), str) and len(str(row.get("sequence"))) >= 10
        if have and not force:
            continue
        if not isinstance(acc, str) or not acc.strip():
            raise RuntimeError(
                f"Row {row.get('id')} has no UniProt accession; cannot fetch a sequence "
                f"(fail-loud rather than store a blank that becomes a zero embedding).")
        seq = fetch_sequence(acc)
        df.at[i, "sequence"] = seq
        n_fetched += 1
        print(f"  fetched {row.get('id'):16s} {acc:12s} len={len(seq)}")

    # Verify no literature row is left without a usable sequence.
    missing = [r["id"] for _, r in df.iterrows()
               if not (isinstance(r.get("sequence"), str) and len(str(r.get("sequence"))) >= 10)]
    if missing:
        raise RuntimeError(f"Sequences still missing after fetch: {missing}")

    df.to_csv(CURATED_FILE, index=False)
    print(f"Updated {CURATED_FILE}: {n_fetched} sequence(s) fetched, "
          f"{len(df)} rows now all have sequences.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true",
                    help="re-fetch even rows that already have a sequence")
    args = ap.parse_args()
    fetch_literature_sequences(force=args.force)
