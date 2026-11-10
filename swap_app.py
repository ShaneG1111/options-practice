"""Interest rate swap pricer. Run with: streamlit run swap_app.py"""

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from swaps import cashflow_table, dv01, par_swap_rate, swap_value, zero_rate

st.set_page_config(page_title="Interest Rate Swap Pricer", layout="wide")
st.title("Interest Rate Swap Pricer")
st.caption("Plain-vanilla fixed-for-floating swap, single zero curve, continuous compounding.")

# ---- Inputs ---------------------------------------------------------------
with st.sidebar:
    st.header("Swap terms")
    notional = st.number_input("Notional ($)", value=10_000_000, step=1_000_000, min_value=1)
    maturity = st.slider("Maturity (years)", 1, 30, 5)
    freq = st.selectbox("Payments per year", [1, 2, 4], index=1)
    side = st.radio("Position", ["Pay fixed", "Receive fixed"])
    pay_fixed = side == "Pay fixed"

    st.header("Zero curve (%)")
    default_curve = pd.DataFrame(
        {"Tenor (yrs)": [0.5, 1, 2, 5, 10, 30], "Zero rate (%)": [4.20, 4.00, 3.80, 3.70, 3.90, 4.30]}
    )
    curve = st.data_editor(default_curve, num_rows="dynamic", hide_index=True)
    curve = curve.dropna().sort_values("Tenor (yrs)")
    shift_bp = st.slider("Parallel shift (bp)", -200, 200, 0, step=5)

tenors = curve["Tenor (yrs)"].to_numpy(dtype=float)
rates = curve["Zero rate (%)"].to_numpy(dtype=float) / 100 + shift_bp / 10_000

if len(tenors) < 2:
    st.error("Enter at least two curve points.")
    st.stop()

par = par_swap_rate(maturity, freq, tenors, rates)
fixed_pct = st.sidebar.number_input(
    "Fixed rate (%)", value=round(par * 100, 4), step=0.05, format="%.4f",
    help="Defaults to today's par rate, so the swap starts at zero value.",
)
fixed = fixed_pct / 100

value = swap_value(notional, fixed, maturity, freq, tenors, rates, pay_fixed)
risk = dv01(notional, fixed, maturity, freq, tenors, rates, pay_fixed)

# ---- Headline numbers -----------------------------------------------------
c1, c2, c3 = st.columns(3)
c1.metric("Par swap rate", f"{par:.3%}")
c2.metric("Value to you", f"${value:,.0f}")
c3.metric("DV01 (value per +1bp)", f"${risk:,.0f}")

# ---- Charts ---------------------------------------------------------------
left, right = st.columns(2)

with left:
    st.subheader("Zero curve and par swap curve")
    grid = np.linspace(0.5, max(30, maturity), 60)
    par_grid = [par_swap_rate(m, freq, tenors, rates) for m in grid]
    curve_df = pd.DataFrame(
        {"Maturity": np.concatenate([grid, grid]),
         "Rate (%)": np.concatenate([zero_rate(grid, tenors, rates), par_grid]) * 100,
         "Curve": ["Zero rate"] * len(grid) + ["Par swap rate"] * len(grid)}
    )
    st.altair_chart(
        alt.Chart(curve_df).mark_line().encode(x="Maturity:Q", y=alt.Y("Rate (%):Q", scale=alt.Scale(zero=False)), color="Curve:N"),
        width="stretch",
    )

with right:
    st.subheader("Value vs. parallel rate shift")
    shifts = np.arange(-200, 201, 10)
    vals = [swap_value(notional, fixed, maturity, freq, tenors, rates + s / 10_000, pay_fixed) for s in shifts]
    shift_df = pd.DataFrame({"Shift (bp)": shifts, "Value ($)": vals})
    st.altair_chart(
        alt.Chart(shift_df).mark_line().encode(x="Shift (bp):Q", y="Value ($):Q"),
        width="stretch",
    )

# ---- Cash flows -----------------------------------------------------------
st.subheader("Cash flows")
cf = cashflow_table(notional, fixed, maturity, freq, tenors, rates, pay_fixed)
st.dataframe(
    cf.style.format({
        "Time (yrs)": "{:.2f}", "Forward rate": "{:.3%}", "Fixed payment": "${:,.0f}",
        "Expected floating": "${:,.0f}", "Net to holder": "${:,.0f}",
        "Discount factor": "{:.4f}", "PV of net": "${:,.0f}",
    }),
    hide_index=True, width="stretch",
)
st.caption(f"Sum of PV of net cash flows: ${cf['PV of net'].sum():,.0f} (matches the value above).")
