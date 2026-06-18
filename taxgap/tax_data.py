"""Shared helpers for taxgap: ZIP normalization, category rules, and the loader
for the bundled all-ZIP rate table.

Rate *sourcing* lives in ``taxgap/providers.py``, which builds results from the
bundled dataset loaded here. This module is deliberately free of any
state-average fallback — a state-wide rate is the wrong answer for a ZIP-level
tool, so an uncovered ZIP simply reports no rate.
"""

from __future__ import annotations

import csv
import gzip
import os
from functools import lru_cache
from typing import Optional

_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
_ZIP_RATES_CSV = os.path.join(_DATA_DIR, "us_zip_rates.csv.gz")

# State/territory code -> display name (for labeling API results).
STATE_NAMES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "DC": "District of Columbia", "FL": "Florida", "GA": "Georgia",
    "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana",
    "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana",
    "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan",
    "MN": "Minnesota", "MS": "Mississippi", "MO": "Missouri", "MT": "Montana",
    "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey",
    "NM": "New Mexico", "NY": "New York", "NC": "North Carolina",
    "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon",
    "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington",
    "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
    "PR": "Puerto Rico", "GU": "Guam", "VI": "U.S. Virgin Islands",
}

# Item categories and a short description shown in the UI.
CATEGORIES = {
    "General merchandise": "Standard taxable goods (electronics, furniture, etc.).",
    "Groceries": "Unprepared food. Exempt or reduced in most states.",
    "Clothing": "Apparel. Exempt in a few states (NJ, PA, MN).",
    "Prescription drugs": "Exempt from sales tax in essentially every state.",
}

# States that fully tax groceries at the normal combined rate. Everywhere else
# we treat groceries as exempt (simplified — a few states use reduced rates,
# which we approximate as exempt).
_GROCERY_TAXED_STATES = {
    "AL", "AR", "HI", "ID", "IL", "KS", "MS", "MO", "OK", "SD", "TN", "UT", "VA",
}

# States where clothing is exempt from sales tax.
_CLOTHING_EXEMPT_STATES = {"NJ", "PA", "MN"}


def normalize_zip(raw) -> Optional[str]:
    """Return a clean 5-digit ZIP string, or None if it isn't one."""
    if raw is None:
        return None
    digits = "".join(ch for ch in str(raw).strip() if ch.isdigit())
    if len(digits) == 5:
        return digits
    if len(digits) == 9:  # ZIP+4
        return digits[:5]
    return None


def apply_category(state_code: str, combined_rate: float, category: str):
    """Return (effective_rate, note) after applying simple category rules.

    The API gives the general-merchandise rate; category exemptions are a
    simplified layer applied on top and clearly labeled as such in the UI.
    """
    if category == "Prescription drugs":
        return 0.0, "Prescription drugs are tax-exempt."
    if category == "Groceries" and state_code not in _GROCERY_TAXED_STATES:
        return 0.0, "Groceries are tax-exempt in this state."
    if category == "Clothing" and state_code in _CLOTHING_EXEMPT_STATES:
        return 0.0, "Clothing is tax-exempt in this state."
    return combined_rate, ""


@lru_cache(maxsize=1)
def _zip_rates() -> dict:
    """Bundled offline rates for every US ZIP, keyed by 5-digit ZIP.

    Regenerate the underlying ``data/us_zip_rates.csv.gz`` with
    ``scripts/build_rates.py`` (see that script for the refresh procedure).
    """
    table = {}
    with gzip.open(_ZIP_RATES_CSV, "rt", newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            table[row["zip"]] = {
                "region": row["region"],
                "state_code": row["state_code"],
                "combined_rate": float(row["combined_rate"]),
                "state_rate": float(row["state_rate"]),
                "county_rate": float(row["county_rate"]),
                "city_rate": float(row["city_rate"]),
                "special_rate": float(row["special_rate"]),
            }
    return table
