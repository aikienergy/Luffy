"""
Purpose: Auditable unit conversions for literature kinetic parameters.

Overview:
    Literature reports cellulase kinetics in heterogeneous units: kcat as 1/s
    or 1/min, "activity" as IU/mg or umol/min/mg, and Km in mM or mg/mL or g/L.
    The simulator works in mM and 1/s. These pure functions perform the
    conversions ONCE, in one place, so that the normalized values stored in
    data/curated/literature_kinetics.csv are reproducible and reviewable.

    Design rule: FAIL LOUD. An unrecognised unit raises ValueError rather than
    silently guessing -- a wrong silent conversion is worse than a crash.

    Scientific caveat: kcat (1/s) and Km (mM) are only well-defined for SOLUBLE
    substrates (cellobiose, pNP-cellobioside, pNP-glucoside, cello-oligomers).
    For insoluble cellulose (Avicel/CMC/PASC) the molar mass is undefined, so
    km_to_mM returns None for mass-concentration units unless a molar mass for a
    defined soluble species is supplied. Callers must keep such values as
    apparent (g/L) constants, not pretend they are mM.
"""

# Molar masses (g/mol) of common DEFINED soluble substrates, for mg/mL <-> mM.
SOLUBLE_SUBSTRATE_MW = {
    "cellobiose": 342.30,
    "pnpg": 301.25,            # p-nitrophenyl-beta-D-glucopyranoside
    "pnp-glucoside": 301.25,
    "pnpc": 463.39,            # p-nitrophenyl-beta-D-cellobioside
    "pnp-cellobioside": 463.39,
    "cellotriose": 504.44,
    "cellotetraose": 666.58,
    "cellopentaose": 828.72,
    "glucose": 180.16,
}

# Substrates with NO defined molar mass (polymeric / insoluble).
POLYMERIC_SUBSTRATES = {"avicel", "cmc", "carboxymethylcellulose", "pasc",
                        "filter paper", "cellulose", "bmcc", "bacterial cellulose"}


def kcat_to_per_s(value, unit, mw_kda=None):
    """
    Convert a reported kcat / turnover / specific activity to 1/s.

    Supported units (case-insensitive):
        - "1/s", "s-1", "/s"            -> identity
        - "1/min", "min-1", "/min"      -> value / 60
        - "umol/min/mg", "iu/mg", "u/mg" (specific activity)
              -> requires mw_kda; kcat = SA * MW / 60
                 SA [umol/min/mg] * MW [kDa = mg/umol] / 60 [s/min] = 1/s
    Raises ValueError on unknown units or missing MW where required.
    """
    if value is None:
        return None
    u = str(unit).strip().lower().replace(" ", "")
    if u in ("1/s", "s-1", "s^-1", "/s", "persecond"):
        return float(value)
    if u in ("1/min", "min-1", "min^-1", "/min", "perminute"):
        return float(value) / 60.0
    if u in ("umol/min/mg", "u/mg", "iu/mg", "units/mg", "u/mgprotein"):
        if mw_kda is None:
            raise ValueError(
                f"Specific activity '{unit}' needs mw_kda to convert to 1/s")
        # SA [umol/min/mg] ; MW [kDa] = [mg/umol]; /60 -> 1/s
        return float(value) * float(mw_kda) / 60.0
    raise ValueError(f"Unrecognised kcat unit: {unit!r}")


def km_to_mM(value, unit, mw_g_per_mol=None, substrate=None):
    """
    Convert a reported Km to mM.

    Supported units (case-insensitive):
        - "mM"                          -> identity
        - "uM", "um"                    -> value / 1000
        - "M"                           -> value * 1000
        - "g/l", "mg/ml", "kg/m3"       -> needs a defined molar mass
              (either mw_g_per_mol, or a `substrate` present in
               SOLUBLE_SUBSTRATE_MW). For polymeric substrates returns None.

    Returns float (mM) or None when the value cannot be expressed in mM
    (e.g. apparent Km on insoluble cellulose). Raises ValueError on unknown unit.
    """
    if value is None:
        return None
    u = str(unit).strip().lower().replace(" ", "")
    if u in ("mm",):
        return float(value)
    if u in ("um", "µm"):
        return float(value) / 1000.0
    if u in ("m", "mol/l"):
        return float(value) * 1000.0
    if u in ("g/l", "mg/ml", "kg/m3"):
        # g/L and mg/mL are numerically identical mass concentrations.
        mw = mw_g_per_mol
        if mw is None and substrate is not None:
            key = str(substrate).strip().lower()
            if key in POLYMERIC_SUBSTRATES:
                return None  # no molar mass -> keep as apparent g/L
            mw = SOLUBLE_SUBSTRATE_MW.get(key)
        if mw is None:
            return None  # undefined molar mass -> cannot express in mM
        # (g/L) / (g/mol) = mol/L ; * 1000 -> mM
        return float(value) / float(mw) * 1000.0
    raise ValueError(f"Unrecognised Km unit: {unit!r}")
