"""Leveraged single-stock ETF explorer. Run with: streamlit run lev_etf_app.py"""

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from lev_etf import (
    TRADING_DAYS, choppy_returns, many_paths, one_day, random_returns,
    rebalance_shortcut, simulate_path, trending_returns, volatility_drag,
)

st.set_page_config(page_title="Leveraged Single-Stock ETFs", layout="wide")
st.title("Leveraged Single-Stock ETFs")
st.caption("A total return swap in an ETF wrapper, reset every day.")

# ---- Sidebar: the fund ------------------------------------------------------
with st.sidebar:
    st.header("The fund")
    leverage = st.selectbox(
        "Daily leverage target", [2.0, 1.5, -1.0, -2.0], index=0,
        format_func=lambda x: f"{x:+g}x" if x < 0 else f"{x:g}x",
        help="2x is the current SEC ceiling for new funds (Rule 18f-4).",
    )
    include_costs = st.checkbox("Include costs", value=False,
                                help="Off reproduces the slide examples exactly.")
    rf = st.number_input("SOFR / T-bill rate (%)", value=4.30, step=0.25, disabled=not include_costs) / 100
    spread = st.number_input("Swap spread over SOFR (%)", value=0.50, step=0.10, disabled=not include_costs) / 100
    expense = st.number_input("Expense ratio (%)", value=1.00, step=0.05, disabled=not include_costs) / 100
    if not include_costs:
        rf = spread = expense = 0.0

lev_label = f"{leverage:g}x"
tab1, tab2, tab3 = st.tabs(["One day: the swap", "A price path", "Trend vs. volatility"])

# ---- Tab 1: one day ---------------------------------------------------------
with tab1:
    st.subheader("Follow the money for one day")
    c1, c2 = st.columns(2)
    nav = c1.number_input("Starting NAV ($)", value=100.0, step=10.0, min_value=1.0)
    move = c2.slider("Stock move today (%)", -30.0, 30.0, 10.0, step=0.5) / 100

    d = one_day(nav, leverage, move, rf, spread, expense)
    trade = d["rebalance_trade"]
    action = "BUY" if trade > 0 else "SELL" if trade < 0 else "NO TRADE"

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Swap payment to fund", f"{'-' if d['swap_pnl'] < 0 else ''}${abs(d['swap_pnl']):,.2f}")
    m2.metric("New NAV", f"${d['new_nav']:,.2f}", f"{d['new_nav'] / nav - 1:+.2%}")
    m3.metric("New swap notional", f"{'Short' if leverage < 0 else 'Long'} ${abs(d['target_exposure']):,.2f}")
    m4.metric("Rebalance trade", f"{action} ${abs(trade):,.2f}")

    steps = pd.DataFrame({
        "Step": ["1. Starting exposure", f"2. Stock moves {move:+.1%}", "3. Swap settles in cash",
                 "4. New NAV", f"5. Target = {lev_label} x new NAV", "6. Trade to get back on target"],
        "Amount": [f"${d['start_exposure']:,.2f}", f"Exposure becomes ${d['exposure_after_move']:,.2f}",
                   f"Bank pays fund ${d['swap_pnl']:,.2f}" if d["swap_pnl"] >= 0 else f"Fund pays bank ${-d['swap_pnl']:,.2f}",
                   f"${d['new_nav']:,.2f}", f"${d['target_exposure']:,.2f}",
                   f"{action} ${abs(trade):,.2f} of stock"],
    })
    st.table(steps.set_index("Step"))

    if not include_costs:
        st.info(f"Shortcut check: L x (L - 1) x return x NAV = "
                f"{leverage:g} x {leverage - 1:g} x {move:.1%} x ${nav:,.0f} = "
                f"${rebalance_shortcut(nav, leverage, move):,.2f}")
    st.markdown(
        "L x (L - 1) is positive for every leveraged and inverse fund, so on an up day they all buy "
        "and on a down day they all sell. The flow always trades with the move."
    )

    st.subheader("Who earns what today")
    w1, w2, w3 = st.columns(3)
    w1.metric("Investors", f"{'-' if d['new_nav'] < nav else ''}${abs(d['new_nav'] - nav):,.2f}", help="All of the market risk.")
    w2.metric("Issuer (expense ratio)", f"${d['issuer_fee']:,.4f}")
    w3.metric("Bank (financing spread)", f"${d['bank_spread_income']:,.4f}",
              help="Bank hedges by holding the stock, so it keeps the spread.")
    if not include_costs:
        st.caption("Turn on 'Include costs' in the sidebar to see the issuer and bank income.")

# ---- Tab 2: a price path ----------------------------------------------------
with tab2:
    st.subheader("Run the fund through a price path")
    kind = st.radio("Path", ["Choppy (+5%, -5%)", "Trending (+1% a day)", "Random"], horizontal=True)
    if kind.startswith("Choppy"):
        returns = choppy_returns(20, 0.05)
    elif kind.startswith("Trending"):
        returns = trending_returns(20, 0.01)
    else:
        r1, r2, r3, r4 = st.columns(4)
        days = r1.slider("Trading days", 10, 252, 63)
        vol = r2.slider("Stock volatility (annual %)", 10, 150, 60) / 100
        drift = r3.slider("Stock drift (annual %)", -50, 50, 0) / 100
        seed = r4.number_input("Random seed", value=7, step=1)
        returns = random_returns(days, vol, drift, seed=int(seed))

    path = simulate_path(returns, leverage, 100.0, rf, spread, expense)
    path["naive"] = 100 * (1 + leverage * (path["stock_price"] / 100 - 1))

    stock_ret = path["stock_price"].iloc[-1] / 100 - 1
    fund_ret = path["nav"].iloc[-1] / 100 - 1
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Stock return", f"{stock_ret:+.1%}")
    k2.metric(f"{lev_label} fund return", f"{fund_ret:+.1%}")
    k3.metric(f"{lev_label} the stock's return", f"{leverage * stock_ret:+.1%}")
    k4.metric("Gap from daily reset", f"{fund_ret - leverage * stock_ret:+.1%}")

    long = path.melt("day", ["stock_price", "nav", "naive"], var_name="series", value_name="value")
    long["series"] = long["series"].map({"stock_price": "Stock", "nav": f"{lev_label} ETF",
                                         "naive": f"{lev_label} x stock (no reset)"})
    st.altair_chart(
        alt.Chart(long).mark_line().encode(
            x=alt.X("day:Q", title="Trading day"),
            y=alt.Y("value:Q", title="Value (start = 100)", scale=alt.Scale(zero=False)),
            color=alt.Color("series:N", title=None),
            strokeDash=alt.condition(alt.datum.series == f"{lev_label} x stock (no reset)",
                                     alt.value([4, 4]), alt.value([0])),
        ),
        width="stretch",
    )

    left, right = st.columns(2)
    with left:
        st.markdown("**Swap notional each day** (resized to L x NAV)")
        st.altair_chart(
            alt.Chart(path).mark_area(opacity=0.6).encode(
                x=alt.X("day:Q", title="Trading day"), y=alt.Y("swap_notional:Q", title="Notional ($)")),
            width="stretch",
        )
    with right:
        st.markdown("**Rebalancing trade each day** (positive = buy at the close)")
        bars = path[path["day"] > 0].assign(side=lambda df: np.where(df["rebalance_trade"] >= 0, "Buy", "Sell"))
        st.altair_chart(
            alt.Chart(bars).mark_bar().encode(
                x=alt.X("day:Q", title="Trading day"), y=alt.Y("rebalance_trade:Q", title="Trade ($)"),
                color=alt.Color("side:N", scale=alt.Scale(domain=["Buy", "Sell"]), title=None)),
            width="stretch",
        )
    same_sign = (np.sign(path["rebalance_trade"][1:]) == np.sign(path["stock_return"][1:])).mean()
    st.caption(f"Rebalance trades went the same direction as the stock on {same_sign:.0%} of days.")

    with st.expander("Day-by-day table"):
        st.dataframe(path.drop(columns="naive"), hide_index=True, width="stretch")

# ---- Tab 3: many paths --------------------------------------------------------
with tab3:
    st.subheader("Same stock, many possible paths")
    s1, s2, s3 = st.columns(3)
    vol3 = s1.slider("Stock volatility (annual %)", 10, 150, 60, key="vol3") / 100
    days3 = s2.slider("Holding period (trading days)", 5, 252, 126, key="days3")
    n3 = s3.select_slider("Number of paths", [200, 500, 1000, 2000], value=1000)

    rets = random_returns(days3, vol3, 0.0, seed=42, n_paths=n3)
    stock_tot, fund_tot = many_paths(rets, leverage)
    df = pd.DataFrame({"Stock return": stock_tot, "Fund return": fund_tot})
    behind = (fund_tot < leverage * stock_tot).mean()
    drag = volatility_drag(leverage, vol3, days3 / TRADING_DAYS)

    t1, t2, t3 = st.columns(3)
    t1.metric(f"Paths where fund trails {lev_label} the stock", f"{behind:.0%}")
    t2.metric("Median fund return", f"{np.median(fund_tot):+.1%}")
    t3.metric("Rule-of-thumb drag (log terms)", f"{drag:+.1%}",
              help="-L(L-1)/2 x volatility squared x years")

    x_line = np.linspace(stock_tot.min(), stock_tot.max(), 50)
    line = pd.DataFrame({"Stock return": x_line, "Fund return": leverage * x_line})
    pts = alt.Chart(df).mark_circle(size=14, opacity=0.4).encode(
        x=alt.X("Stock return:Q", axis=alt.Axis(format="%")),
        y=alt.Y("Fund return:Q", axis=alt.Axis(format="%")),
    )
    ref = alt.Chart(line).mark_line(strokeDash=[4, 4], color="gray").encode(x="Stock return:Q", y="Fund return:Q")
    st.altair_chart(pts + ref, width="stretch")
    st.caption(f"Each dot is one possible path. The dashed line is {lev_label} x the stock's return. "
               "Dots near the middle (flat, choppy paths) sit below it; big trends land above it.")

    vols = np.linspace(0.1, 1.5, 30)
    drag_df = pd.DataFrame({"Volatility": vols,
                            "Drag": [volatility_drag(leverage, v, days3 / TRADING_DAYS) for v in vols]})
    st.markdown(f"**How drag grows with volatility** over {days3} trading days")
    st.altair_chart(
        alt.Chart(drag_df).mark_line().encode(
            x=alt.X("Volatility:Q", axis=alt.Axis(format="%"), title="Stock volatility (annual)"),
            y=alt.Y("Drag:Q", axis=alt.Axis(format="%"), title="Approx. drag")),
        width="stretch",
    )
