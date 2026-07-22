# SOXL Playbook - Fast Response Alerts

## Purpose

This file holds alerts and a playbook for fast, correct responses to large or rapid SOXL price movements. Use it to list alert [triggers](../stages/OPERATIONS.md#trigger), data sources, and step-by-step response actions (e.g., size adjustments, stop updates, order templates).

These are high-conviction moves requiring intraday or multi-day monitoring and rapid [execution](../stages/OPERATIONS.md#execution-and-execution-models) decisions. See `alerts/README.md` for the full alerts directory structure.

## Alert Template

Each alert should include:

- **Trigger:** What condition activates the alert (e.g., >5% intraday move, gap > X%, volume > Y)
- **Data sources:** Ticker, current price, intraday range, recent news, options flow, volume, short/long MA, support/resistance
- **Immediate response:** Concrete actions (e.g., reduce position to X%, set limit/stop orders, alert team)
- **Follow-up:** Re-[evaluation](../stages/OPERATIONS.md#evaluation-plans) timing and resumption criteria (e.g., re-evaluate after N minutes/hours, resume normal monitoring)
- **Responsible party:** Who executes the response
- **Status:** Active, triggered, or resolved

## Position Context

- **Current Holdings:** 81 shares SOXL @ $184.04 avg cost
- **Base ETF Firepower:** 10 SOXX + 10 SMH (worth ~$11,485)
- **Settled Cash Ready:** $5,000
- **Target Position After Accumulation:** 200 shares @ $156.60 avg cost
- **Total Cash If All Tiers Hit:** $52,900 | Net Profit Target: +$21,580

---

## Active Alerts

### ACCUMULATION PHASE (Downside Triggers)

**Alert 1: Capitulation Floor - SOXX Index**
- **Trigger:** SOXX price ≤ $476.00
- **Signal:** Semiconductor sector capitulation reached
- **Immediate Action:** 
  1. Liquidate 10 SOXX units (~$4,760 value)
  2. Liquidate 10 SMH units (~$6,725 value)
  3. Deploy $11,485 + $5,000 cash = $16,485 into SOXL
  4. Expected result: Scale position to ~200 shares, avg cost drops to $156.60
- **Data Required:** SOXX price, account buying power, SOXL real-time price for execution
- **Status:** Monitoring
- **Responsible:** Execute immediately upon alert

**Alert 2: SOXL Leveraged Target**
- **Trigger:** SOXL price ≤ $140.00 (or near $138–$140 zone)
- **Signal:** Maximum accumulation opportunity within leveraged vehicle
- **Immediate Action:**
  1. Verify SOXX has also dropped (cascading signal)
  2. Execute conversion strategy (see Alert 1 if not already done)
  3. Do NOT set a tight stop immediately after buying.
- **Data Required:** SOXL intraday range, VIX level, volume
- **Status:** Monitoring
- **Responsible:** Execute or confirm accumulation phase underway
- **Note:** Watch VIX; if VIX > 20, monitor for leverage decay risk

---

### PROFIT-TAKING PHASE (Upside Triggers)

**Alert 3: Tier 1 Breakeven Defense**
- **Trigger:** SOXL price ≥ $195.00
- **Action:** Sell 40 shares
- **Capital Recovered:** $7,800
- **Purpose:** Reclaim initial entry capital, defend downside
- **Order Type:** Use GTC limit order pre-staged at $195.00
- **Status:** Order ready
- **Responsible:** Auto-execute via GTC order

**Alert 4: Tier 2 Major Resistance**
- **Trigger:** SOXL price ≥ $235.00
- **Action:** Sell 60 shares
- **Capital Recovered:** $14,100
- **Cumulative Cash:** $21,900
- **Purpose:** Extract bulk of initial capital, lock in core gains
- **Order Type:** Use GTC limit order pre-staged at $235.00
- **Remaining Position:** 100 shares (from 200)
- **Status:** Order ready
- **Responsible:** Auto-execute via GTC order

**Alert 5: Tier 3 All-Time High Zone**
- **Trigger:** SOXL price ≥ $290.00
- **Action:** Sell 60 shares
- **Capital Recovered:** $17,400
- **Cumulative Cash:** $39,300
- **Purpose:** Harvest core windfall gains
- **Order Type:** Use GTC limit order pre-staged at $290.00
- **Remaining Position:** 40 shares (from 200)
- **Status:** Order ready
- **Responsible:** Auto-execute via GTC order

**Alert 6: Tier 4 Moon Shot (Trailing Stop)**
- **Trigger:** SOXL price ≥ $340.00+ (with trailing stop)
- **Action:** Sell final 40 shares
- **Capital Recovered:** $13,600
- **Total Cumulative:** $52,900
- **Net Profit:** +$21,580
- **Purpose:** Liquidate remainder using trailing stop into new ATH
- **Order Type:** Trailing Stop $ Amount (e.g., $15.00 to $20.00 trail) or Trailing Stop % (e.g., 7% to 10% trail).
- **ATR Reference:** Adjust trailing stop % based on recent volatility
- **Status:** Manual discretion (not auto GTC)
- **Responsible:** Monitor intraday and execute with discipline

---

## Operational Guardrails

- **VIX Threshold:** If VIX > 20.00 and stays elevated, watch for 3x leverage decay on horizontal moves
- **GTC Pre-staging:** Tiers 1–3 can be pre-entered as Good-Til-Canceled limit orders today
- **Emotional Discipline:** Pre-staged orders prevent emotion from blocking profit-taking
- **Liquidity Check:** Verify SOXL volume at alert prices; ensure fills are achievable
- **Margin Check:** Monitor available margin if using leverage during accumulation phase

---

## Catalyst Watch

- **Late-July Big Tech Earnings:** Expected catalyst for market reversal (Google, Microsoft, Meta, Amazon CapEx announcements)
- **AI Capital Expenditure Trends:** Monitor for strong guidance to drive semiconductor upside
- **Semiconductor Sector Health:** Track breadth signals alongside SOXL price action
