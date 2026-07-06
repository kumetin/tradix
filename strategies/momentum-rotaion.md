Current strategy we’ve been testing:
Universe
Latest high-beta universe with SOXL included:
SPY, QQQ, SPMO, SPHB, TQQQ, UPRO, SOXL,
WCLD, ARKK, XLF, MSOS, XLU, XLE, SEDG,
FNGU, TECL, BULZ, LABU, WEBL, URTY,
MSTR, COIN, PLTR, CVNA, SMCI, TSLA

Capital
Initial lump sum: $5,000
Monthly contribution: $100
Fractional shares allowed
No fees, no taxes, no slippage
No selling

At the first trade month, the model invests:
$5,000 initial cash + $100 monthly contribution = $5,100
After that it invests $100 each month.

Monthly Selection Rule
At the start of each month, using data available before that month starts, rank the universe.
A ticker is eligible if:
(price > SMA200 OR SMA50 > SMA200)
AND
drawdown from 252-day high > -45%
Where:
drawdown = current adjusted close / highest adjusted close in last 252 trading days - 1
Then among eligible tickers, pick the one with the highest trailing 126-trading-day return, roughly 6 months.

If no ticker is eligible:
default to UPRO

Entry Rule
Once the ticker is selected for the month, we do not buy immediately unless the setup appears.
We wait for a 4-down setup on that ticker:
close day 1 > close day 2 > close day 3 > close day 4
When the 4th down close happens, the setup is known after market close, so the simulated buy happens at the next trading day adjusted open.
If no 4-down setup happens during that month:
buy at month-end adjusted open
That is the fallback.
Important Behavior
The strategy rotates only for new money.
It does not sell old holdings.
So if January buys SOXL, February buys XLE, and March buys SMCI, all three positions remain in the portfolio. New monthly cash just goes into the newly selected ticker.
Data Used
Raw prices:
data/stock/prices/daily/<year>/<ticker>.csv
Precomputed features:
data/stock/features/daily/<year>/<ticker>.csv
Features include adjusted open/high/low, SMA20/50/100/150/200, trailing returns, rolling highs, and drawdowns.