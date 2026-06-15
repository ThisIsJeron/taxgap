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

Rates come from the **[zip.tax](https://www.zip.tax/) API**, which returns the
real taxing jurisdictions for a ZIP — state, county, city, and special district
— not a misleading state-wide average. ([`taxgap/providers.py`](taxgap/providers.py))

| Mode | What it covers |
| --- | --- |
| **Live** (with API key) | Every US ZIP, current rates, full jurisdiction breakdown. Responses are cached for a day to conserve your free quota. |
| **Demo** (no key) | Only the ~45 major-city ZIPs in [`data/zip_overrides.csv`](data/zip_overrides.csv), with their exact local rates. Any other ZIP returns a clear "add a key" message. |

This tool **never falls back to a state-average rate** — a state-wide number is
the wrong answer for a ZIP-level comparison, so an uncovered ZIP simply reports
that no rate was found.

### Add an API key (free)

1. Get a free key at [zip.tax](https://www.zip.tax/) (100 calls to start).
2. Provide it any one of these ways:
   - paste it into the **🔑 API key** expander in the app, or
   - `export ZIPTAX_API_KEY=...`, or
   - copy [`.streamlit/secrets.toml.example`](.streamlit/secrets.toml.example)
     to `.streamlit/secrets.toml` and fill in the key (gitignored).

> ⚠️ A ZIP can span multiple tax jurisdictions; address-level lookup is more
> precise. Category exemptions are simplified. Use for estimates, not filing.

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
app.py                  # Streamlit UI
taxgap/providers.py     # zip.tax API client + offline demo provider
taxgap/tax_data.py      # ZIP normalization, category rules, demo sample data
data/zip_overrides.csv  # exact rates for ~45 major-city ZIPs (demo mode)
requirements.txt
```

## Ideas / TODO

- [ ] Address-level lookup (rooftop-precise) when a full address is entered.
- [ ] Annual-spend projection ("buy this monthly → save $X/yr").
- [ ] Shareable result URLs.
- [ ] Jurisdiction picker when a ZIP overlaps several tax areas.

## License

MIT
