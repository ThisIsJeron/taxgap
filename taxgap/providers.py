"""Sales-tax rate providers for taxgap.

Primary source is the **zip.tax** REST API (https://docs.zip.tax), which returns
real jurisdiction-level rates for a ZIP — state, county, city and special
district — instead of a useless state-wide average.

The client is pure Python (no Streamlit) and raises typed errors so the UI can
react. A small offline sample provider backs "demo mode" when no API key is
configured; it only serves the ~45 ZIPs we have *exact* local rates for and
returns ``None`` for anything else (we never fall back to a state average).
"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass, field
from typing import List, Optional

import requests

from taxgap.tax_data import STATE_NAMES, _zip_overrides, normalize_zip

ZIPTAX_ENDPOINT = "https://api.zip-tax.com/request/v60"
_TIMEOUT = 12


# ----------------------------------------------------------------- errors -----
class ProviderError(Exception):
    """Base class for provider failures."""


class MissingKeyError(ProviderError):
    """No API key configured."""


class RateLimitError(ProviderError):
    """API quota exhausted (HTTP 429)."""


class AuthError(ProviderError):
    """API key rejected (HTTP 401/403)."""


class ApiError(ProviderError):
    """Any other API/transport failure."""


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
    source: str  # "live" or "sample"
    extras: dict = field(default_factory=dict)

    @property
    def primary(self) -> Jurisdiction:
        return self.jurisdictions[0]


# --------------------------------------------------------------- helpers ------
def get_api_key(explicit: Optional[str] = None) -> Optional[str]:
    """Resolve an API key from arg, env, or Streamlit secrets (in that order)."""
    if explicit:
        return explicit.strip()
    env = os.environ.get("ZIPTAX_API_KEY")
    if env:
        return env.strip()
    try:  # st.secrets only available inside a Streamlit run
        import streamlit as st

        if "ZIPTAX_API_KEY" in st.secrets:
            return str(st.secrets["ZIPTAX_API_KEY"]).strip()
    except Exception:
        pass
    return None


def _pct(value) -> float:
    """zip.tax returns rates as decimals (0.0775); convert to percent."""
    try:
        return round(float(value) * 100.0, 4)
    except (TypeError, ValueError):
        return 0.0


# -------------------------------------------------------------- live API ------
def fetch_live(zip_code: str, api_key: str) -> Optional[RateResult]:
    """Query zip.tax for a ZIP. Returns None if the ZIP has no rates."""
    if not api_key:
        raise MissingKeyError("No zip.tax API key configured.")

    try:
        resp = requests.get(
            ZIPTAX_ENDPOINT,
            params={"postalcode": zip_code},
            headers={"X-API-Key": api_key},
            timeout=_TIMEOUT,
        )
    except requests.RequestException as exc:  # DNS, timeout, connection reset
        raise ApiError(f"Could not reach zip.tax ({exc}).") from exc

    if resp.status_code == 429:
        raise RateLimitError("zip.tax rate limit reached — out of free requests.")
    if resp.status_code in (401, 403):
        raise AuthError("zip.tax rejected the API key (check it's valid).")
    if resp.status_code >= 400:
        raise ApiError(f"zip.tax returned HTTP {resp.status_code}.")

    try:
        data = resp.json()
    except ValueError as exc:
        raise ApiError("zip.tax returned a non-JSON response.") from exc

    # rCode 100 == success. Anything else (e.g. 101 no results) -> no data.
    if data.get("rCode") != 100:
        return None

    rows = data.get("results") or []
    jurisdictions = []
    for r in rows:
        jurisdictions.append(
            Jurisdiction(
                zip_code=str(r.get("geoPostalCode") or zip_code),
                city=str(r.get("geoCity") or "").strip(),
                county=str(r.get("geoCounty") or "").strip(),
                state_code=str(r.get("geoState") or "").strip().upper(),
                combined_rate=_pct(r.get("taxSales")),
                state_rate=_pct(r.get("rateState")),
                county_rate=_pct(r.get("rateCounty")),
                city_rate=_pct(r.get("rateCity")),
                special_rate=_pct(r.get("rateAdditional")),
            )
        )
    if not jurisdictions:
        return None
    return RateResult(zip_code, jurisdictions, source="live")


# ------------------------------------------------------------ offline demo ----
def fetch_sample(zip_code: str) -> Optional[RateResult]:
    """Offline fallback: only the ZIPs we have *exact* local rates for.

    Returns None for any other ZIP — we never invent a state-average number.
    """
    overrides = _zip_overrides()
    o = overrides.get(zip_code)
    if not o:
        return None
    jur = Jurisdiction(
        zip_code=zip_code,
        city=o["city"],
        county="",
        state_code=o["state_code"],
        combined_rate=o["combined_rate"],
        state_rate=0.0,
        county_rate=0.0,
        city_rate=0.0,
        special_rate=0.0,
    )
    return RateResult(zip_code, [jur], source="sample")


def lookup(zip_code: str, api_key: Optional[str]) -> Optional[RateResult]:
    """Resolve a ZIP via the live API when keyed, else the offline sample.

    Raises ProviderError subclasses on API failures; returns None when the ZIP
    itself is unknown/invalid.
    """
    z = normalize_zip(zip_code)
    if z is None:
        return None
    if api_key:
        return fetch_live(z, api_key)
    return fetch_sample(z)
