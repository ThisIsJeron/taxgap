"""taxgap — compare the sales-tax cost of a purchase across two ZIP codes."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from taxgap.tax_data import CATEGORIES, DATA_YEAR, lookup

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

      .tg-card {
        border: 1px solid rgba(128,128,128,.18); border-radius: 16px;
        padding: 1.15rem 1.3rem; background: rgba(127,127,127,.04);
        height: 100%;
      }
      .tg-card .loc { font-size: 1.15rem; font-weight: 700; margin-bottom: .15rem; }
      .tg-card .sub { color: #6b7280; font-size: .82rem; margin-bottom: .9rem; }
      .tg-row { display: flex; justify-content: space-between;
                padding: .28rem 0; font-size: .95rem; }
      .tg-row .lbl { color: #6b7280; }
      .tg-row .val { font-weight: 600; }
      .tg-total { border-top: 1px dashed rgba(128,128,128,.3);
                  margin-top: .55rem; padding-top: .55rem; }
      .tg-total .val { font-size: 1.25rem; font-weight: 800; }

      .tg-verdict {
        border-radius: 16px; padding: 1.1rem 1.3rem; margin: .4rem 0 .2rem;
        text-align: center; color: #fff;
        background: linear-gradient(90deg, #059669, #10b981);
      }
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
    "between two ZIP codes.</p></div>",
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------- inputs -----
with st.form("inputs"):
    top = st.columns([1.3, 1])
    with top[0]:
        price = st.number_input(
            "Item price ($)", min_value=0.0, value=999.00, step=10.0, format="%.2f"
        )
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

    submitted = st.form_submit_button("Compare", use_container_width=True, type="primary")


def render_card(label: str, info, price: float, qty: int):
    subtotal = price * qty
    tax = subtotal * info.effective_rate / 100.0
    total = subtotal + tax
    where = info.city or info.state_name
    rate_lbl = f"{info.effective_rate:.3f}%"
    exact = "exact local rate" if info.is_exact else "state-average rate"
    st.markdown(
        f"""
        <div class="tg-card">
          <div class="loc">{label} · {where}</div>
          <div class="sub">{info.zip_code} · {info.state_name} ({info.state_code}) · {exact}</div>
          <div class="tg-row"><span class="lbl">Subtotal</span><span class="val">${subtotal:,.2f}</span></div>
          <div class="tg-row"><span class="lbl">Tax rate</span><span class="val">{rate_lbl}</span></div>
          <div class="tg-row"><span class="lbl">Sales tax</span><span class="val">${tax:,.2f}</span></div>
          <div class="tg-row tg-total"><span class="lbl">Total</span><span class="val">${total:,.2f}</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if info.note:
        st.caption("ℹ️ " + info.note)
    return {"subtotal": subtotal, "tax": tax, "total": total}


if submitted:
    info_a = lookup(zip_a, category)
    info_b = lookup(zip_b, category)

    errs = []
    if info_a is None:
        errs.append(f"Couldn't resolve ZIP A (“{zip_a}”). Enter a valid 5-digit US ZIP.")
    if info_b is None:
        errs.append(f"Couldn't resolve ZIP B (“{zip_b}”). Enter a valid 5-digit US ZIP.")

    if errs:
        for e in errs:
            st.error(e)
    else:
        st.write("")
        cols = st.columns(2)
        with cols[0]:
            res_a = render_card("A", info_a, price, qty)
        with cols[1]:
            res_b = render_card("B", info_b, price, qty)

        tax_diff = abs(res_a["tax"] - res_b["tax"])
        total_diff = abs(res_a["total"] - res_b["total"])

        if total_diff < 0.005:
            st.markdown(
                '<div class="tg-verdict tie"><div class="big">It\'s a wash</div>'
                '<div class="small">Both ZIPs cost the same on this purchase.</div></div>',
                unsafe_allow_html=True,
            )
        else:
            cheaper_is_a = res_a["total"] < res_b["total"]
            cheaper = info_a if cheaper_is_a else info_b
            cheaper_label = "A" if cheaper_is_a else "B"
            where = cheaper.city or cheaper.state_name
            pct = total_diff / max(res_a["total"], res_b["total"]) * 100
            st.markdown(
                f"""
                <div class="tg-verdict">
                  <div class="big">Save ${total_diff:,.2f} in {cheaper_label} · {where}</div>
                  <div class="small">${tax_diff:,.2f} less sales tax &nbsp;·&nbsp;
                  {pct:.1f}% lower total &nbsp;·&nbsp; on {qty} item{'s' if qty > 1 else ''}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # comparison chart
        chart_df = pd.DataFrame(
            {
                "Location": [
                    f"A · {info_a.city or info_a.state_code}",
                    f"B · {info_b.city or info_b.state_code}",
                ],
                "Subtotal": [res_a["subtotal"], res_b["subtotal"]],
                "Sales tax": [res_a["tax"], res_b["tax"]],
            }
        ).set_index("Location")
        st.markdown("###### Cost breakdown")
        st.bar_chart(chart_df, color=["#a5b4fc", "#4f46e5"], height=240)

        st.markdown(
            f'<p class="tg-note">Rates are bundled offline figures for the {DATA_YEAR} '
            "tax year (state + average local, Tax Foundation; major-city ZIPs use exact "
            "local rates). Category exemptions are simplified. For estimates only — verify "
            "before relying on these numbers.</p>",
            unsafe_allow_html=True,
        )
else:
    st.info("Enter a price and two ZIP codes, then hit **Compare**.")
