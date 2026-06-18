"""taxgap — compare the sales-tax cost of a purchase across two ZIP codes.

Rates come from a bundled, offline dataset covering every US ZIP (real
state/county/city/district breakdown per ZIP). No API key, no network — it never
falls back to a state average, so an uncovered ZIP simply reports no rate.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from taxgap import providers
from taxgap.tax_data import CATEGORIES, apply_category

st.set_page_config(
    page_title="taxgap — sales tax difference calculator",
    page_icon="🧾",
    layout="centered",
)

# ---------------------------------------------------------------- styling -----
st.markdown(
    """
    <style>
      .block-container { max-width: 880px; padding-top: 2.2rem; }
      #MainMenu, footer { visibility: hidden; }

      .tg-hero h1 {
        font-size: 2.4rem; font-weight: 800; letter-spacing: -0.03em;
        margin-bottom: .2rem;
      }
      .tg-hero h1 .grad {
        background: linear-gradient(90deg, #4f46e5, #06b6d4);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        background-clip: text;
      }
      .tg-hero p { color: #6b7280; font-size: 1.02rem; margin-top: 0; }

      .tg-badge { display: inline-block; padding: .12rem .6rem; border-radius: 999px;
                  font-size: .76rem; font-weight: 600; margin-bottom: .4rem; }
      .tg-badge.live { background: rgba(16,185,129,.15); color: #059669; }

      .tg-card {
        border: 1px solid rgba(128,128,128,.18); border-radius: 16px;
        padding: 1.15rem 1.3rem; background: rgba(127,127,127,.04); height: 100%;
      }
      .tg-card .loc { font-size: 1.12rem; font-weight: 700; margin-bottom: .12rem; }
      .tg-card .sub { color: #6b7280; font-size: .82rem; margin-bottom: .85rem; }
      .tg-row { display: flex; justify-content: space-between;
                padding: .26rem 0; font-size: .95rem; }
      .tg-row .lbl { color: #6b7280; }
      .tg-row .val { font-weight: 600; }
      .tg-break { display: flex; justify-content: space-between; font-size: .8rem;
                  color: #9ca3af; padding: .08rem 0; }
      .tg-total { border-top: 1px dashed rgba(128,128,128,.3);
                  margin-top: .5rem; padding-top: .5rem; }
      .tg-total .val { font-size: 1.25rem; font-weight: 800; }

      .tg-verdict { border-radius: 16px; padding: 1.1rem 1.3rem; margin: .4rem 0 .2rem;
                    text-align: center; color: #fff;
                    background: linear-gradient(90deg, #059669, #10b981); }
      .tg-verdict.tie { background: linear-gradient(90deg, #6b7280, #9ca3af); }
      .tg-verdict .big { font-size: 1.9rem; font-weight: 800; line-height: 1.1; }
      .tg-verdict .small { opacity: .92; font-size: .95rem; }
      .tg-note { color: #9ca3af; font-size: .78rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="tg-hero"><h1>🧾 <span class="grad">taxgap</span></h1>'
    "<p>See exactly how much sales tax changes the price of a purchase "
    "between two ZIP codes — with real county &amp; city rates.</p></div>",
    unsafe_allow_html=True,
)

# --------------------------------------------------------------- data mode ----
st.markdown('<span class="tg-badge live">● All US ZIPs · offline rates</span>',
            unsafe_allow_html=True)


# ----------------------------------------------------------------- inputs -----
with st.form("inputs"):
    top = st.columns([1.3, 1])
    with top[0]:
        price = st.number_input("Item price ($)", min_value=0.0, value=999.00,
                                step=10.0, format="%.2f")
    with top[1]:
        qty = st.number_input("Quantity", min_value=1, value=1, step=1)

    category = st.selectbox("Item category", list(CATEGORIES.keys()))
    st.caption(CATEGORIES[category])

    zips = st.columns(2)
    with zips[0]:
        zip_a = st.text_input("ZIP code A", value="97201", max_chars=10,
                              help="e.g. 97201 (Portland, OR — no sales tax)")
    with zips[1]:
        zip_b = st.text_input("ZIP code B", value="98101", max_chars=10,
                              help="e.g. 98101 (Seattle, WA)")

    submitted = st.form_submit_button("Compare", use_container_width=True,
                                      type="primary")


def render_card(label: str, result, jur, price: float, qty: int, category: str):
    subtotal = price * qty
    eff_rate, note = apply_category(jur.state_code, jur.combined_rate, category)
    tax = subtotal * eff_rate / 100.0
    total = subtotal + tax
    where = (jur.city.title() if jur.city else jur.state_name)
    src = "estimated · Avalara ZIP rate"

    rows = [("State", jur.state_rate), ("County", jur.county_rate),
            ("City", jur.city_rate), ("Special", jur.special_rate)]
    breakdown = "".join(
        f'<div class="tg-break"><span>{n}</span><span>{v:.3f}%</span></div>'
        for n, v in rows if v
    )

    st.markdown(
        f"""
        <div class="tg-card">
          <div class="loc">{label} · {where}</div>
          <div class="sub">{jur.zip_code} · {jur.state_name} ({jur.state_code}) · {src}</div>
          <div class="tg-row"><span class="lbl">Subtotal</span><span class="val">${subtotal:,.2f}</span></div>
          <div class="tg-row"><span class="lbl">Combined tax rate</span><span class="val">{eff_rate:.3f}%</span></div>
          {breakdown}
          <div class="tg-row"><span class="lbl">Sales tax</span><span class="val">${tax:,.2f}</span></div>
          <div class="tg-row tg-total"><span class="lbl">Total</span><span class="val">${total:,.2f}</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if note:
        st.caption("ℹ️ " + note)
    if len(result.jurisdictions) > 1:
        others = ", ".join(j.label for j in result.jurisdictions[1:])
        st.caption(f"⚠️ {len(result.jurisdictions)} jurisdictions overlap this ZIP; "
                   f"showing **{jur.label}**. Others: {others}")
    return {"subtotal": subtotal, "tax": tax, "total": total, "where": where,
            "label": label, "state_code": jur.state_code}


if submitted:
    res_a = providers.lookup(zip_a)
    res_b = providers.lookup(zip_b)

    problems = []
    if res_a is None:
        problems.append(f"No rate found for ZIP A (“{zip_a}”). "
                        "Check it's a valid US ZIP code.")
    if res_b is None:
        problems.append(f"No rate found for ZIP B (“{zip_b}”). "
                        "Check it's a valid US ZIP code.")

    if problems:
        for p in problems:
            st.error(p)
    else:
        st.write("")
        jur_a, jur_b = res_a.primary, res_b.primary
        cols = st.columns(2)
        with cols[0]:
            a = render_card("A", res_a, jur_a, price, qty, category)
        with cols[1]:
            b = render_card("B", res_b, jur_b, price, qty, category)

        tax_diff = abs(a["tax"] - b["tax"])
        total_diff = abs(a["total"] - b["total"])

        if total_diff < 0.005:
            st.markdown(
                '<div class="tg-verdict tie"><div class="big">It\'s a wash</div>'
                '<div class="small">Both ZIPs cost the same on this purchase.</div></div>',
                unsafe_allow_html=True,
            )
        else:
            cheaper = a if a["total"] < b["total"] else b
            pct = total_diff / max(a["total"], b["total"]) * 100
            st.markdown(
                f"""
                <div class="tg-verdict">
                  <div class="big">Save ${total_diff:,.2f} in {cheaper['label']} · {cheaper['where']}</div>
                  <div class="small">${tax_diff:,.2f} less sales tax &nbsp;·&nbsp;
                  {pct:.1f}% lower total &nbsp;·&nbsp; on {qty} item{'s' if qty > 1 else ''}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        chart_df = pd.DataFrame(
            {
                "Location": [f"A · {a['where']}", f"B · {b['where']}"],
                "Subtotal": [a["subtotal"], b["subtotal"]],
                "Sales tax": [a["tax"], b["tax"]],
            }
        ).set_index("Location")
        st.markdown("###### Cost breakdown")
        st.bar_chart(chart_df, color=["#a5b4fc", "#4f46e5"], height=240)

        st.markdown(
            '<p class="tg-note">Rates from bundled Avalara ZIP-level tables '
            "(state + county + city + special district). A ZIP can span multiple "
            "tax jurisdictions; address-level lookup is more precise. Category "
            "exemptions are simplified. For estimates only.</p>",
            unsafe_allow_html=True,
        )
else:
    st.info("Enter a price and two ZIP codes, then hit **Compare**.")
