#!/usr/bin/env python3
"""Build taxgap's bundled all-ZIP sales-tax dataset.

Reads Avalara "TAXRATES_ZIP5" per-state CSVs from ``data/raw/`` and writes a
single gzipped table to ``data/us_zip_rates.csv.gz`` keyed by 5-digit ZIP. That
bundle is what the app ships and reads at runtime — no API key, fully offline.

Refreshing the data (Avalara updates rates monthly):

  1. Download the free state rate tables from Avalara:
       https://www.avalara.com/taxrates/en/download-tax-tables.html
     Select every state and submit the (email) form. Each file is named
     ``TAXRATES_ZIP5_<ST><YYYYMM>.csv``.
  2. Drop the CSVs into ``data/raw/`` (gitignored).
  3. Run:  ``python scripts/build_rates.py``
  4. Commit the regenerated ``data/us_zip_rates.csv.gz``.

Avalara's columns are parsed by header (order-independent):
  State, ZipCode, TaxRegionName, EstimatedCombinedRate, StateRate,
  EstimatedCountyRate, EstimatedCityRate, EstimatedSpecialRate, RiskLevel
Rates arrive as decimals (0.103500); we store them as percent (10.3500) to match
the rest of the app.
"""
from __future__ import annotations

import csv
import glob
import gzip
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(ROOT, "data", "raw")
OUT = os.path.join(ROOT, "data", "us_zip_rates.csv.gz")

OUT_FIELDS = ["zip", "region", "state_code", "combined_rate",
              "state_rate", "county_rate", "city_rate", "special_rate"]


def _pct(value) -> float:
    """Avalara rates are decimals (0.1035); store them as percent (10.35)."""
    try:
        return round(float(value) * 100.0, 4)
    except (TypeError, ValueError):
        return 0.0


def build() -> None:
    paths = sorted(glob.glob(os.path.join(RAW_DIR, "TAXRATES_ZIP5_*.csv")))
    if not paths:
        raise SystemExit(
            f"No Avalara CSVs found in {RAW_DIR}.\n"
            "See this script's docstring for how to download them."
        )

    rows: dict[str, dict] = {}
    dupes = 0
    for path in paths:
        # utf-8-sig strips any BOM Avalara prepends to the header.
        with open(path, newline="", encoding="utf-8-sig") as fh:
            for r in csv.DictReader(fh):
                zip_code = (r.get("ZipCode") or "").strip().zfill(5)
                if len(zip_code) != 5 or not zip_code.isdigit():
                    continue
                if zip_code in rows:  # a few ZIPs straddle a state line
                    dupes += 1
                    continue
                rows[zip_code] = {
                    "zip": zip_code,
                    "region": (r.get("TaxRegionName") or "").strip().strip('"'),
                    "state_code": (r.get("State") or "").strip().upper(),
                    "combined_rate": _pct(r.get("EstimatedCombinedRate")),
                    "state_rate": _pct(r.get("StateRate")),
                    "county_rate": _pct(r.get("EstimatedCountyRate")),
                    "city_rate": _pct(r.get("EstimatedCityRate")),
                    "special_rate": _pct(r.get("EstimatedSpecialRate")),
                }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with gzip.open(OUT, "wt", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=OUT_FIELDS)
        writer.writeheader()
        for zip_code in sorted(rows):
            writer.writerow(rows[zip_code])

    print(f"Wrote {len(rows):,} ZIPs to {OUT}")
    print(f"  ({len(paths)} state files, {dupes} cross-state duplicate ZIPs skipped)")


if __name__ == "__main__":
    build()
