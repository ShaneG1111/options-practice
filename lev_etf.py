"""Leveraged single-stock ETF mechanics.

How the fund works (matches the class deck):
- Investors' money (NAV) sits in T-bills as collateral and earns the risk-free rate.
- The fund holds a total return swap with a dealer bank on L x NAV of the stock.
  Bank pays the fund the stock's return on that notional; the fund pays the bank
  interest (risk-free rate plus a spread) on it.
- The swap settles in cash every day, then is resized to L x the new NAV.

Sign convention: leverage L can be negative for inverse funds (e.g. -1, -2).
A positive rebalance trade means the fund (via the bank's hedge) BUYS stock.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def one_day(nav, leverage, stock_return, rf=0.0, spread=0.0, expense_ratio=0.0):
    """Walk one day of the swap, step by step, the same way slide 6 does.

    rf, spread and expense_ratio are annual rates; they accrue for one trading day.
    Returns a dict with every intermediate number.
    """
    dt = 1 / TRADING_DAYS
    start_exposure = leverage * nav
    exposure_after_move = start_exposure * (1 + stock_return)
    swap_pnl = start_exposure * stock_return                 # stock leg, settled in cash
    collateral_interest = nav * rf * dt                      # T-bills earn the risk-free rate
    financing = leverage * nav * rf * dt + abs(leverage) * nav * spread * dt  # paid to bank
    fee = nav * expense_ratio * dt                           # issuer's cut
    new_nav = max(nav + swap_pnl + collateral_interest - financing - fee, 0.0)
    target_exposure = leverage * new_nav
    trade = target_exposure - exposure_after_move
    return {
        "start_nav": nav,
        "start_exposure": start_exposure,
        "exposure_after_move": exposure_after_move,
        "swap_pnl": swap_pnl,
        "collateral_interest": collateral_interest,
        "financing_paid": financing,
        "bank_spread_income": abs(leverage) * nav * spread * dt,
        "issuer_fee": fee,
        "new_nav": new_nav,
        "target_exposure": target_exposure,
        "rebalance_trade": trade,
    }


def rebalance_shortcut(nav, leverage, stock_return):
    """Slide 6 shortcut, no costs: trade = L x (L - 1) x return x NAV."""
    return leverage * (leverage - 1) * stock_return * nav


def simulate_path(stock_returns, leverage, start_nav=100.0, rf=0.0, spread=0.0, expense_ratio=0.0):
    """Run the fund through a series of daily stock returns.

    Returns a DataFrame with one row per day (day 0 is the start).
    Once NAV hits zero the fund is wiped out and stays at zero.
    """
    stock_returns = np.asarray(stock_returns, dtype=float)
    rows = [{"day": 0, "stock_return": 0.0, "stock_price": 100.0, "nav": start_nav,
             "swap_notional": leverage * start_nav, "swap_pnl": 0.0, "financing_paid": 0.0,
             "rebalance_trade": 0.0}]
    price, nav = 100.0, start_nav
    for day, r in enumerate(stock_returns, start=1):
        price *= 1 + r
        if nav > 0:
            d = one_day(nav, leverage, r, rf, spread, expense_ratio)
        else:
            d = {"new_nav": 0.0, "swap_pnl": 0.0, "financing_paid": 0.0, "rebalance_trade": 0.0}
        nav = d["new_nav"]
        rows.append({"day": day, "stock_return": r, "stock_price": price, "nav": nav,
                     "swap_notional": leverage * nav, "swap_pnl": d["swap_pnl"],
                     "financing_paid": d["financing_paid"], "rebalance_trade": d["rebalance_trade"]})
    return pd.DataFrame(rows)


def choppy_returns(days=20, move=0.05):
    """+move, -move, +move, ... (slide 4, left chart)."""
    return np.array([move if i % 2 == 0 else -move for i in range(days)])


def trending_returns(days=20, move=0.01):
    """Same move every day (slide 4, right chart)."""
    return np.full(days, move)


def random_returns(days, annual_vol, annual_drift=0.0, seed=None, n_paths=1):
    """Daily returns from a lognormal (geometric Brownian motion) model.

    Shape is (n_paths, days); a single path comes back 1-D.
    """
    rng = np.random.default_rng(seed)
    dt = 1 / TRADING_DAYS
    z = rng.standard_normal((n_paths, days))
    log_r = (annual_drift - 0.5 * annual_vol**2) * dt + annual_vol * np.sqrt(dt) * z
    r = np.expm1(log_r)
    return r[0] if n_paths == 1 else r


def many_paths(returns_2d, leverage):
    """Fast, cost-free version for many paths at once. Returns (stock_total, fund_total)."""
    stock_total = np.prod(1 + returns_2d, axis=1) - 1
    daily_fund = np.maximum(1 + leverage * returns_2d, 0.0)  # NAV can't go below zero
    fund_total = np.prod(daily_fund, axis=1) - 1
    return stock_total, fund_total


def volatility_drag(leverage, annual_vol, years):
    """Approximate drag vs. L x the stock's log return: -L(L-1)/2 x vol^2 x time.

    This is the 'leverage x volatility squared' rule of thumb from slide 4.
    """
    return -leverage * (leverage - 1) / 2 * annual_vol**2 * years
