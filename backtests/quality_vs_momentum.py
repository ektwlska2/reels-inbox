"""Checks the Josh Answers reel "flight to high quality" (shared 2026-10-13).

Claims: the 3-month spread between quality and momentum is the widest since 2020; the last
time investors piled into quality was just before COVID; and when it unwinds, it does so
dramatically. Goldman's own baskets are not public, so the iShares factor ETFs stand in:
QUAL (MSCI USA Sector Neutral Quality) and MTUM (MSCI USA Momentum), both from mid-2013.

1. The 63-trading-day return of QUAL minus MTUM: today's value against its history.
2. Event study: after the spread first enters its top 5% (no new signal for 63 days), what
   do SPY, QUAL and MTUM do over the next 1, 3 and 6 months, against all days?
3. The names he suggests (PEP, MCD, HD, LOW, WMT): moves over 2 months, and valuation.
"""
import numpy as np
import pandas as pd
import yfinance as yf

pd.set_option("display.width", 200)
px = yf.download(["QUAL", "MTUM", "SPY", "PEP", "MCD", "HD", "LOW", "WMT"], start="2013-07-01",
                 auto_adjust=True, progress=False)["Close"]
print("Data through", px.index[-1].date())

r63 = px.pct_change(63)
spread = (r63["QUAL"] - r63["MTUM"]).dropna() * 100
print("\n1. QUAL minus MTUM, 63-day return spread (percentage points)")
print(f"  latest {spread.iloc[-1]:+.1f}  (percentile vs history {(spread < spread.iloc[-1]).mean()*100:.0f}%)")
print(f"  max since 2020-06 {spread.loc['2020-06':].max():+.1f} on {spread.loc['2020-06':].idxmax().date()}")
print(f"  max in Jan-Mar 2020 {spread.loc['2020-01':'2020-03'].max():+.1f} on {spread.loc['2020-01':'2020-03'].idxmax().date()}")
print(f"  max in Jan-Feb 2020 (pre-crash) {spread.loc['2020-01':'2020-02-19'].max():+.1f}")
print("  largest readings by year:")
print(spread.groupby(spread.index.year).agg(["max", "min"]).round(1).T.to_string())

thr = spread.quantile(0.95)
hits, last = [], None
for d, v in spread.items():
    if v >= thr and (last is None or (spread.index.get_loc(d) - spread.index.get_loc(last)) > 63):
        hits.append(d)
        last = d
print(f"\n2. Event study: spread >= {thr:.1f}pp (top 5%), {len(hits)} episodes:",
      [h.date().isoformat() for h in hits])
rows = []
for h in [21, 63, 126]:
    fwd = px[["SPY", "QUAL", "MTUM"]].shift(-h) / px[["SPY", "QUAL", "MTUM"]] - 1
    ev = fwd.loc[[d for d in hits if d in fwd.index]].dropna()
    rows.append({"horizon_days": h, "n": len(ev),
                 **{f"{t} after%": round(ev[t].mean() * 100, 1) for t in ["SPY", "QUAL", "MTUM"]},
                 "QUAL-MTUM after pp": round((ev["QUAL"] - ev["MTUM"]).mean() * 100, 1),
                 "SPY all-days%": round(fwd["SPY"].mean() * 100, 1),
                 "SPY negative share%": round((ev["SPY"] < 0).mean() * 100, 0)})
print(pd.DataFrame(rows).to_string(index=False))
print("  per episode, SPY next 63 days %:")
f63 = px["SPY"].shift(-63) / px["SPY"] - 1
for d in hits:
    v = f63.get(d)
    print(f"   {d.date()}  {'' if pd.isna(v) else f'{v*100:+.1f}'}")

print("\n3. Suggested names")
for t in ["PEP", "MCD", "HD", "LOW", "WMT"]:
    s = px[t].dropna()
    info = {}
    try:
        info = yf.Ticker(t).info
    except Exception:
        pass
    print(f"  {t}: 2-month {(s.iloc[-1]/s.iloc[-43]-1)*100:+.1f}%  3-month {(s.iloc[-1]/s.iloc[-64]-1)*100:+.1f}%  "
          f"YTD {(s.iloc[-1]/s.loc[:'2025-12-31'].iloc[-1]-1)*100:+.1f}%  "
          f"trailing P/E {info.get('trailingPE', float('nan')):.1f}  forward P/E {info.get('forwardPE', float('nan')):.1f}")
