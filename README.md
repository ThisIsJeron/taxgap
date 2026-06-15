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
- Side-by-side breakdown of subtotal, tax rate, sales tax, and total.
- A clear verdict: *"Save $X in B · Seattle"* plus the percentage difference.
- **Category-aware**: groceries, clothing, and prescription drugs apply
  simplified exemption rules per state.
- A bar chart comparing the two locations.

## Where the tax data comes from

Everything runs **offline — no API key, no signup**:

| Source | What it covers |
| --- | --- |
| `data/state_tax_rates.csv` | Combined state + average-local sales tax rate for every state + DC (Tax Foundation, 2024). |
| `data/zip_overrides.csv` | Exact combined rates for ~45 major-city ZIPs, so two ZIPs *in the same state* still show a real difference. |
| ZIP3 prefix table (`taxgap/tax_data.py`) | Maps any valid ZIP's first three digits to a state, so every ZIP resolves to at least a state-average rate. |

A ZIP resolves to its **exact** override rate when available, otherwise to the
**state average**. The app labels which one was used.

> ⚠️ Rates are approximations for the 2024 tax year and category exemptions are
> simplified. Use for ballpark estimates, not for filing taxes. To make it
> precise, swap in a live rate API (TaxJar, Avalara, Zip-Tax) in
> `taxgap/tax_data.py`.

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
taxgap/tax_data.py      # offline ZIP -> rate lookup + category rules
data/                   # bundled CSV rate tables
requirements.txt
```

## Ideas / TODO

- [ ] Live rate API as an optional backend (keyed via `st.secrets`).
- [ ] More city-level ZIP overrides.
- [ ] Annual-spend projection ("buy this monthly → save $X/yr").
- [ ] Shareable result URLs.

## License

MIT
