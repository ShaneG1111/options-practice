"""Tests check the app against the numbers on the class slides."""

import numpy as np
import pytest

from lev_etf import (
    choppy_returns, many_paths, one_day, random_returns, rebalance_shortcut,
    simulate_path, trending_returns,
)


def test_slide3_swap_settlement():
    # $100 in, swap on $200; stock +10% -> NAV $120, stock -10% -> NAV $80
    assert one_day(100, 2, 0.10)["new_nav"] == pytest.approx(120)
    assert one_day(100, 2, -0.10)["new_nav"] == pytest.approx(80)
    assert one_day(100, 2, 0.10)["target_exposure"] == pytest.approx(240)


def test_slide6_rebalance_trades():
    assert one_day(100, 2, 0.10)["rebalance_trade"] == pytest.approx(20)    # 2x buys $20
    assert one_day(100, -2, 0.10)["rebalance_trade"] == pytest.approx(60)   # -2x buys back $60
    assert one_day(100, -2, 0.10)["new_nav"] == pytest.approx(80)


def test_shortcut_matches_full_calculation():
    for lev in [2, 1.5, -1, -2]:
        for r in [-0.07, 0.03, 0.10]:
            assert one_day(100, lev, r)["rebalance_trade"] == pytest.approx(rebalance_shortcut(100, lev, r))


def test_slide4_choppy_path():
    path = simulate_path(choppy_returns(20, 0.05), 2)
    assert path["stock_price"].iloc[-1] / 100 - 1 == pytest.approx(-0.025, abs=0.0005)
    assert path["nav"].iloc[-1] / 100 - 1 == pytest.approx(-0.096, abs=0.0005)


def test_slide4_trending_path():
    path = simulate_path(trending_returns(20, 0.01), 2)
    assert path["stock_price"].iloc[-1] / 100 - 1 == pytest.approx(0.220, abs=0.0005)
    assert path["nav"].iloc[-1] / 100 - 1 == pytest.approx(0.486, abs=0.0005)


def test_nav_never_negative():
    path = simulate_path([0.6, 0.1], -2)  # inverse fund, stock +60% wipes it out
    assert path["nav"].iloc[1] == 0 and path["nav"].iloc[2] == 0


def test_costs_reduce_nav():
    flat = one_day(100, 2, 0.0, rf=0.04, spread=0.005, expense_ratio=0.01)
    assert flat["new_nav"] < 100


def test_fast_and_slow_paths_agree():
    rets = random_returns(30, 0.5, seed=1)
    slow = simulate_path(rets, 2)["nav"].iloc[-1] / 100 - 1
    _, fast = many_paths(rets.reshape(1, -1), 2)
    assert fast[0] == pytest.approx(slow)
