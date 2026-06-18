"""Sales-tax rate providers for taxgap.

Rates come from a bundled, offline dataset covering every US ZIP — real
jurisdiction-level rates (state, county, city, special district) keyed by ZIP,
not a useless state-wide average. No API key, no network, fully offline.

The dataset (``data/us_zip_rates.csv.gz``) is built from Avalara's free
ZIP-level rate tables; regenerate it with ``scripts/build_rates.py``. An
uncovered/invalid ZIP returns ``None`` — we never fall back to a state average.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from taxgap.tax_data import STATE_NAMES, _zip_rates, normalize_zip


# ------------------------------------------------------------- data types -----
@dataclass
class Jurisdiction:
    """One taxing jurisdiction that applies to a ZIP."""

    zip_code: str
    city: str
    county: str
    state_code: str
    combined_rate: float   # percent, e.g. 7.75
    state_rate: float      # percent
    county_rate: float     # percent
    city_rate: float       # percent
    special_rate: float    # percent (special districts)

    @property
    def state_name(self) -> str:
        return STATE_NAMES.get(self.state_code, self.state_code)

    @property
    def label(self) -> str:
        parts = [p for p in (self.city.title() if self.city else "", self.county.title()) if p]
        where = " / ".join(dict.fromkeys(parts)) or self.state_name
        return f"{where} — {self.combined_rate:.3f}%"


@dataclass
class RateResult:
    """All jurisdictions that overlap a queried ZIP, plus where it came from."""

    zip_code: str
    jurisdictions: List[Jurisdiction]
    source: str  # "bundled"
    extras: dict = field(default_factory=dict)

    @property
    def primary(self) -> Jurisdiction:
        return self.jurisdictions[0]


# ------------------------------------------------------------ bundled data ----
def fetch_bundled(zip_code: str) -> Optional[RateResult]:
    """Look up a ZIP in the bundled offline dataset (all US ZIPs).

    Returns None for an uncovered ZIP — we never invent a state-average number.
    """
    rec = _zip_rates().get(zip_code)
    if not rec:
        return None
    jur = Jurisdiction(
        zip_code=zip_code,
        city=rec["region"],   # Avalara TaxRegionName (region/place label)
        county="",
        state_code=rec["state_code"],
        combined_rate=rec["combined_rate"],
        state_rate=rec["state_rate"],
        county_rate=rec["county_rate"],
        city_rate=rec["city_rate"],
        special_rate=rec["special_rate"],
    )
    return RateResult(zip_code, [jur], source="bundled")


def lookup(zip_code: str) -> Optional[RateResult]:
    """Resolve a ZIP from the bundled dataset.

    Returns None when the ZIP is invalid or not in the dataset.
    """
    z = normalize_zip(zip_code)
    if z is None:
        return None
    return fetch_bundled(z)
