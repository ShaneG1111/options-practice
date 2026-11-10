"""Plain-vanilla interest rate swap pricing.

Single-curve setup: one zero curve is used both to discount cash flows and to
project the floating leg. Rates are annual, continuously compounded zero rates.
Good enough for learning; real desks use separate OIS discounting and forward curves.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def zero_rate(t, tenors, rates):
    """Interpolate the zero rate at time t (years), flat beyond the curve ends."""
    return np.interp(t, tenors, rates)


def discount_factor(t, tenors, rates):
    """Discount factor P(0, t) = exp(-r(t) * t)."""
    t = np.asarray(t, dtype=float)
    return np.exp(-zero_rate(t, tenors, rates) * t)


def payment_times(maturity: float, freq: int) -> np.ndarray:
    """Payment dates in years, e.g. maturity 2, freq 2 -> [0.5, 1.0, 1.5, 2.0]."""
    if maturity <= 0 or freq <= 0:
        raise ValueError("maturity and freq must be positive")
    n = int(round(maturity * freq))
    return np.arange(1, n + 1) / freq


def annuity(maturity, freq, tenors, rates):
    """Sum of accrual * discount factor over the fixed-leg dates (the 'PV01 per 1 notional')."""
    times = payment_times(maturity, freq)
    return float(np.sum(discount_factor(times, tenors, rates) / freq))


def par_swap_rate(maturity, freq, tenors, rates):
    """Fixed rate that makes the swap worth zero today: (1 - P(T)) / annuity."""
    p_t = float(discount_factor(maturity, tenors, rates))
    return (1.0 - p_t) / annuity(maturity, freq, tenors, rates)


def swap_value(notional, fixed_rate, maturity, freq, tenors, rates, pay_fixed=True):
    """Value to the holder. Pay-fixed (payer swap) gains when rates rise."""
    a = annuity(maturity, freq, tenors, rates)
    float_leg = notional * (1.0 - float(discount_factor(maturity, tenors, rates)))
    fixed_leg = notional * fixed_rate * a
    value = float_leg - fixed_leg
    return value if pay_fixed else -value


def dv01(notional, fixed_rate, maturity, freq, tenors, rates, pay_fixed=True):
    """Change in value for a +1 basis point parallel shift in the zero curve."""
    bumped = np.asarray(rates, dtype=float) + 0.0001
    return swap_value(notional, fixed_rate, maturity, freq, tenors, bumped, pay_fixed) - swap_value(
        notional, fixed_rate, maturity, freq, tenors, rates, pay_fixed
    )


def cashflow_table(notional, fixed_rate, maturity, freq, tenors, rates, pay_fixed=True):
    """Period-by-period fixed and expected floating cash flows, from the holder's side."""
    times = payment_times(maturity, freq)
    dfs = discount_factor(times, tenors, rates)
    prev = np.concatenate(([1.0], dfs[:-1]))
    fwd = (prev / dfs - 1.0) * freq  # simple forward rate for each period
    fixed_cf = notional * fixed_rate / freq
    float_cf = notional * fwd / freq
    sign = 1.0 if pay_fixed else -1.0
    net = sign * (float_cf - fixed_cf)
    return pd.DataFrame(
        {
            "Time (yrs)": times,
            "Forward rate": fwd,
            "Fixed payment": np.full_like(times, fixed_cf),
            "Expected floating": float_cf,
            "Net to holder": net,
            "Discount factor": dfs,
            "PV of net": net * dfs,
        }
    )
