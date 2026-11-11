# Leveraged Single-Stock ETF Explorer

Companion app to the "Leveraged Single-Stock ETFs" presentation (Shane Gorman & Aiden Shay).
Models a 2x (or 1.5x, -1x, -2x) single-stock fund as a total return swap that resets every day.

## Files
- `lev_etf.py`: the math (one-day swap settlement, rebalancing, price paths, many-path simulation)
- `lev_etf_app.py`: the Streamlit app
- `tests/test_lev_etf.py`: 8 tests that reproduce the numbers on slides 3, 4 and 6

## Run it (VS Code terminal, with `(.venv)` showing)
```
pytest
streamlit run lev_etf_app.py
```

## The three tabs
1. **One day: the swap.** Pick a stock move and follow the money: swap settles in cash, new NAV,
   swap resized to L x NAV, and the rebalancing trade. Checks the L x (L - 1) x return x NAV shortcut.
   Shows what investors, the issuer and the bank each earn.
2. **A price path.** Choppy, trending, or random stock path. Compares the fund to the stock and to
   "L x the stock's return," and charts the swap notional and the daily rebalancing trades.
3. **Trend vs. volatility.** Simulates many paths of the same stock to show how often the daily reset
   costs the fund, and how drag grows with leverage x volatility squared.

## How the model works
- Investor money (NAV) sits in T-bills earning SOFR.
- Swap notional = L x NAV. The bank pays the fund the stock's return on that notional; the fund pays
  SOFR plus a spread on it. Settled in cash daily, then resized.
- Inverse funds (negative L) receive SOFR minus the spread on the short.
- NAV floors at zero: investors can't lose more than they put in.
- Costs are off by default so the app matches the slides; turn them on in the sidebar.

## Simplifications
- Dividends are folded into the stock's daily return
- No intraday moves, tracking error, or trading costs on the bank's hedge
- Random paths use a lognormal (geometric Brownian motion) model with constant volatility
