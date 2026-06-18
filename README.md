# 🧾 taxgap

A tiny [Streamlit](https://streamlit.io) app that shows how much **sales tax**
changes the cost of a purchase between two US ZIP codes. Enter a price and two
ZIPs, and taxgap tells you the price difference, the tax difference, and which
ZIP is cheaper.

![passion project](https://img.shields.io/badge/passion-project-7c3aed)
![python](https://img.shields.io/badge/python-3.9%2B-blue)
![license](https://img.shields.io/badge/license-MIT-green)

## Features

- **Item price, quantity, category, and two ZIP codes** as inputs.
- Side-by-side breakdown of subtotal, **combined rate with its state / county /
  city / special-district components**, sales tax, and total.
- A clear verdict: *"Save $X in B · Seattle"* plus the percentage difference.
- **Category-aware**: groceries, clothing, and prescription drugs apply
  simplified exemption rules per state.
- A bar chart comparing the two locations.

## Where the tax data comes from

Rates come from a **bundled, offline dataset covering every US ZIP** —
[`data/us_zip_rates.csv.gz`](data/us_zip_rates.csv.gz) (~41k ZIPs). Each ZIP
carries its real taxing jurisdictions — state, county, city, and special
district — not a misleading state-wide average.
([`taxgap/providers.py`](taxgap/providers.py))

**No API key, no network, no rate limits** — every ZIP works out of the box.
This tool **never falls back to a state-average rate**; an uncovered or invalid
ZIP simply reports that no rate was found.

The dataset is built from **[Avalara's free ZIP-level rate tables](https://www.avalara.com/taxrates/en/download-tax-tables.html)**.

> ⚠️ ZIP-level rates are estimates — a ZIP can span multiple tax jurisdictions,
> and address-level lookup is more precise. Category exemptions are simplified.
> Use for estimates, not filing.

### Refreshing the rates (Avalara updates monthly)

1. Download the free state rate tables from
   [Avalara](https://www.avalara.com/taxrates/en/download-tax-tables.html)
   (select every state, submit the form). Files are named
   `TAXRATES_ZIP5_<ST><YYYYMM>.csv`.
2. Drop the CSVs into `data/raw/` (gitignored).
3. Run `python scripts/build_rates.py` to regenerate
   `data/us_zip_rates.csv.gz`, then commit it.

## Run it locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Then open http://localhost:8501.

## Project layout

```
app.py                    # Streamlit UI
taxgap/providers.py       # bundled-dataset lookup + result types
taxgap/tax_data.py        # ZIP normalization, category rules, dataset loader
scripts/build_rates.py    # rebuild the bundle from Avalara CSVs in data/raw/
data/us_zip_rates.csv.gz  # bundled rates for every US ZIP (committed)
requirements.txt
```

## Ideas / TODO

- [ ] Address-level lookup (rooftop-precise) when a full address is entered.
- [ ] Annual-spend projection ("buy this monthly → save $X/yr").
- [ ] Shareable result URLs.
- [ ] Jurisdiction picker when a ZIP overlaps several tax areas.

## License

MIT
