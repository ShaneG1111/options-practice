# Interest Rate Swap Pricer (practice)

Test build, not final. Plain-vanilla fixed-for-floating swap priced off one zero curve.

## Files
- `swaps.py`: the math (discount factors, par swap rate, swap value, DV01, cash flow table)
- `swap_app.py`: the Streamlit app
- `tests/test_swaps.py`: 6 tests

## Where to put them
Drop all three into your `options-practice` folder (`tests/test_swaps.py` goes in the existing `tests` folder).
The names don't clash with the template's `app.py` / `pricing.py`, so nothing gets overwritten.

## Run it (in the VS Code terminal, with `(.venv)` showing)
```
pytest
streamlit run swap_app.py
```
`pytest` should now show 10 passed (the template's 4 plus these 6).

## What the app shows
- Par swap rate, value to you, and DV01 (dollar change per 1 basis point rise in rates)
- Zero curve vs. par swap curve chart
- Value vs. parallel rate shift chart
- Period-by-period cash flows; their present values add up to the swap value

## Simplifications
- One curve for both discounting and projecting the floating leg (real desks use OIS discounting plus a separate forward curve)
- Continuous compounding, linear interpolation of zero rates
- No day-count conventions, holidays, or accrued interest
