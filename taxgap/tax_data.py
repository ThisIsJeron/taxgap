"""Offline sales-tax lookup for taxgap.

Everything here works without a network connection or API key:

* ``state_tax_rates.csv``  – combined state + average-local rate for every
  state (Tax Foundation, 2024 figures).
* ``zip_overrides.csv``    – exact combined rates for ~45 major-city ZIPs so
  that comparing two ZIPs inside the same state still shows a real difference.
* ``ZIP3_RANGES``          – maps a ZIP's first three digits to a state, so any
  valid US ZIP resolves to *some* rate even without an explicit override.

Resolution order for a ZIP:
    1. exact match in ``zip_overrides.csv``      -> precise local rate
    2. ZIP3 prefix -> state -> state combined avg -> approximate rate
"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
_STATE_CSV = os.path.join(_DATA_DIR, "state_tax_rates.csv")
_ZIP_CSV = os.path.join(_DATA_DIR, "zip_overrides.csv")

# Tax year the bundled figures correspond to (shown in the UI).
DATA_YEAR = 2024

# (low_prefix, high_prefix, state_code) for the first three ZIP digits.
# Ranges follow the USPS ZIP-prefix-to-state assignments. Approximate at the
# edges of a few prefixes, which is fine for a comparison tool.
ZIP3_RANGES = [
    (5, 5, "NY"), (6, 9, "PR"), (10, 27, "MA"), (28, 29, "RI"),
    (30, 38, "NH"), (39, 49, "ME"), (50, 54, "VT"), (55, 59, "MA"),
    (60, 69, "CT"), (70, 89, "NJ"), (90, 99, "AE"), (100, 149, "NY"),
    (150, 196, "PA"), (197, 199, "DE"), (200, 205, "DC"), (206, 219, "MD"),
    (220, 246, "VA"), (247, 268, "WV"), (270, 289, "NC"), (290, 299, "SC"),
    (300, 319, "GA"), (320, 339, "FL"), (340, 342, "FL"), (344, 349, "FL"),
    (350, 369, "AL"), (370, 385, "TN"), (386, 397, "MS"), (398, 399, "GA"),
    (400, 427, "KY"), (430, 459, "OH"), (460, 479, "IN"), (480, 499, "MI"),
    (500, 528, "IA"), (530, 549, "WI"), (550, 567, "MN"), (570, 577, "SD"),
    (580, 588, "ND"), (590, 599, "MT"), (600, 629, "IL"), (630, 658, "MO"),
    (660, 679, "KS"), (680, 693, "NE"), (700, 714, "LA"), (716, 729, "AR"),
    (730, 732, "OK"), (733, 733, "TX"), (734, 749, "OK"), (750, 799, "TX"),
    (800, 816, "CO"), (820, 831, "WY"), (832, 838, "ID"), (840, 847, "UT"),
    (850, 865, "AZ"), (870, 884, "NM"), (885, 885, "TX"), (889, 898, "NV"),
    (900, 961, "CA"), (962, 966, "AE"), (967, 968, "HI"), (969, 969, "GU"),
    (970, 979, "OR"), (980, 994, "WA"), (995, 999, "AK"),
]

# Item categories and a short description shown in the UI.
CATEGORIES = {
    "General merchandise": "Standard taxable goods (electronics, furniture, etc.).",
    "Groceries": "Unprepared food. Exempt or reduced in most states.",
    "Clothing": "Apparel. Exempt in a few states (NJ, PA, MN).",
    "Prescription drugs": "Exempt from sales tax in essentially every state.",
}

# States that fully tax groceries at the normal combined rate. Everywhere else
# we treat groceries as exempt (simplified — a handful of states use reduced
# rates, which we approximate as exempt).
_GROCERY_TAXED_STATES = {
    "AL", "AR", "HI", "ID", "IL", "KS", "MS", "MO", "OK", "SD", "TN", "UT", "VA",
}

# States where clothing is exempt from sales tax.
_CLOTHING_EXEMPT_STATES = {"NJ", "PA", "MN"}


@dataclass
class TaxInfo:
    """Resolved tax data for a single ZIP code."""

    zip_code: str
    city: Optional[str]
    state_code: str
    state_name: str
    combined_rate: float          # headline rate before category rules (%)
    effective_rate: float         # rate actually applied after category (%)
    is_exact: bool                # True if from an explicit ZIP override
    note: str = ""                # human-readable explanation of adjustments


@lru_cache(maxsize=1)
def _state_table() -> dict:
    table = {}
    with open(_STATE_CSV, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            table[row["state_code"]] = {
                "state_name": row["state_name"],
                "combined_rate": float(row["combined_rate"]),
            }
    return table


@lru_cache(maxsize=1)
def _zip_overrides() -> dict:
    table = {}
    with open(_ZIP_CSV, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            table[row["zip"].zfill(5)] = {
                "city": row["city"],
                "state_code": row["state_code"],
                "combined_rate": float(row["combined_rate"]),
            }
    return table


def normalize_zip(raw: str) -> Optional[str]:
    """Return a clean 5-digit ZIP string, or None if it isn't one."""
    if raw is None:
        return None
    digits = "".join(ch for ch in str(raw).strip() if ch.isdigit())
    if len(digits) == 5:
        return digits
    if len(digits) == 9:  # ZIP+4
        return digits[:5]
    return None


def zip_to_state(zip_code: str) -> Optional[str]:
    """Map a 5-digit ZIP to a state code using its first three digits."""
    try:
        prefix = int(zip_code[:3])
    except (TypeError, ValueError):
        return None
    for low, high, state in ZIP3_RANGES:
        if low <= prefix <= high:
            return state
    return None


def _apply_category(state_code: str, base_rate: float, category: str):
    """Return (effective_rate, note) after applying simple category rules."""
    if category == "Prescription drugs":
        return 0.0, "Prescription drugs are tax-exempt."
    if category == "Groceries" and state_code not in _GROCERY_TAXED_STATES:
        return 0.0, "Groceries are tax-exempt in this state."
    if category == "Clothing" and state_code in _CLOTHING_EXEMPT_STATES:
        return 0.0, "Clothing is tax-exempt in this state."
    return base_rate, ""


def lookup(zip_code: str, category: str = "General merchandise") -> Optional[TaxInfo]:
    """Resolve a ZIP (and optional category) to tax info, or None if invalid."""
    z = normalize_zip(zip_code)
    if z is None:
        return None

    overrides = _zip_overrides()
    states = _state_table()

    if z in overrides:
        o = overrides[z]
        state_code = o["state_code"]
        state_name = states.get(state_code, {}).get("state_name", state_code)
        base = o["combined_rate"]
        eff, note = _apply_category(state_code, base, category)
        return TaxInfo(z, o["city"], state_code, state_name, base, eff, True, note)

    state_code = zip_to_state(z)
    if state_code is None or state_code not in states:
        return None

    info = states[state_code]
    base = info["combined_rate"]
    eff, note = _apply_category(state_code, base, category)
    extra = " (state average — no city-level data for this ZIP)"
    return TaxInfo(
        z, None, state_code, info["state_name"], base, eff, False,
        (note + extra).strip(),
    )
