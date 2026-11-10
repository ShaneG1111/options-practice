import numpy as np
import pytest

from swaps import cashflow_table, dv01, par_swap_rate, payment_times, swap_value

TENORS = np.array([0.5, 1, 2, 5, 10, 30])
RATES = np.array([0.042, 0.040, 0.038, 0.037, 0.039, 0.043])


def test_payment_times():
    assert list(payment_times(2, 2)) == [0.5, 1.0, 1.5, 2.0]


def test_par_swap_is_worth_zero():
    par = par_swap_rate(5, 2, TENORS, RATES)
    assert swap_value(1e7, par, 5, 2, TENORS, RATES) == pytest.approx(0, abs=1e-6)


def test_flat_curve_par_rate_matches_closed_form():
    # Flat continuous rate r, annual pay: par rate = e^r - 1
    r = 0.05
    flat = np.array([r, r])
    assert par_swap_rate(5, 1, np.array([1, 30]), flat) == pytest.approx(np.exp(r) - 1)


def test_payer_and_receiver_offset():
    pay = swap_value(1e7, 0.035, 5, 2, TENORS, RATES, pay_fixed=True)
    rec = swap_value(1e7, 0.035, 5, 2, TENORS, RATES, pay_fixed=False)
    assert pay == pytest.approx(-rec)


def test_dv01_signs():
    assert dv01(1e7, 0.037, 5, 2, TENORS, RATES, pay_fixed=True) > 0
    assert dv01(1e7, 0.037, 5, 2, TENORS, RATES, pay_fixed=False) < 0


def test_cashflows_sum_to_value():
    cf = cashflow_table(1e7, 0.035, 5, 2, TENORS, RATES)
    assert cf["PV of net"].sum() == pytest.approx(swap_value(1e7, 0.035, 5, 2, TENORS, RATES))
