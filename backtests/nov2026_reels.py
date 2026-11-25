"""Checks two reels shared in November 2026.

A. usstockupdates, "Crash or playbook?" (2026-11-22): Washington lets stocks fall so the
   10-year yield drops and $11 trillion of debt is refinanced cheaply.
   1. The 10-year path this autumn (5.31% in early October to 4.92% "Friday") and the
      S&P 500 / Nasdaq on the crash day.
   2. Is "yields fall when stocks crash" the normal pattern? Big down days for SPY,
      2002 to today, split before and after 2021 (the stock-bond correlation turned
      positive in 2022).
B. Macro Optics, "Has CoreWeave bottomed?" (2026-11-12).
   3. CRWV price claims: all-time high, drawdown, bounce since the 5 November low;
      Eli Lilly's 15-month gain.
   4. Stand-in for the "trend model": hold an asset only above its 200-day average
      (decided at the close, traded next day, 5 bp per switch), against buy-and-hold.
   5. "In disinflation tech does very poorly": regimes from FRED CPI and industrial
      production since 1960, average monthly returns of Nasdaq, S&P 500 and sectors.
"""
import numpy as np
import pandas as pd
import yfinance as yf

pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 30)


def dl(t, start):
    df = yf.download(t, start=start, auto_adjust=True, progress=False)["Close"]
    return df if isinstance(df, pd.DataFrame) else df.to_frame(t)


print("=" * 80, "\n1. AUTUMN 2026: 10-YEAR YIELD AND STOCKS\n")
a = dl(["^TNX", "^GSPC", "^IXIC", "SPY", "TLT"], "2026-09-15")
print("Data through", a.index[-1].date())
print(a.round(2).to_string())
t = a["^TNX"].dropna()
print(f"\n10y high since Oct 1: {t.loc['2026-10-01':].max():.2f} on {t.loc['2026-10-01':].idxmax().date()}")
print(f"10y low since Oct 1: {t.loc['2026-10-01':].min():.2f} on {t.loc['2026-10-01':].idxmin().date()}")
d = a.pct_change() * 100
worst = d["^GSPC"].loc["2026-10-01":].nsmallest(5)
print("\nWorst S&P 500 days since Oct 1 (%), with Nasdaq % and 10y change (bp):")
for dt, v in worst.items():
    print(f"  {dt.date()}  S&P {v:.2f}  Nasdaq {d.loc[dt,'^IXIC']:.2f}  10y {(t.loc[dt]-t.shift(1).loc[dt])*100:+.0f}bp")
print("Correlation since Oct 1, daily S&P % vs 10y change:",
      round(d["^GSPC"].loc["2026-10-01":].corr(t.diff().loc["2026-10-01":]), 2))

print("\n" + "=" * 80, "\n2. DO YIELDS FALL ON BIG DOWN DAYS? (SPY daily, 10y change in bp)\n")
b = dl(["SPY", "^TNX"], "2002-01-01").dropna()
r = b["SPY"].pct_change() * 100
dy = b["^TNX"].diff() * 100
for lo, hi in [("2002", "2020"), ("2021", "2026")]:
    rr, yy = r.loc[lo:hi], dy.loc[lo:hi]
    print(f"{lo}-{hi}: corr(SPY %, 10y bp) {rr.corr(yy):+.2f}")
    for th in [-2, -3]:
        m = rr <= th
        print(f"   SPY <= {th}%: {m.sum()} days, mean 10y change {yy[m].mean():+.1f}bp, yield fell on {(yy[m] < 0).mean()*100:.0f}% of them")
print("\nYearly corr(SPY %, 10y bp):")
print(pd.DataFrame({"r": r, "y": dy}).groupby(r.index.year).apply(lambda g: g["r"].corr(g["y"])).round(2).to_string())

print("\n" + "=" * 80, "\n3. COREWEAVE AND ELI LILLY PRICES\n")
c = dl(["CRWV", "NVDA", "LLY"], "2025-03-01")
cw = c["CRWV"].dropna()
print(f"CRWV first close {cw.index[0].date()} {cw.iloc[0]:.2f}; ATH close {cw.max():.2f} on {cw.idxmax().date()}")
print(f"CRWV last {cw.index[-1].date()} {cw.iloc[-1]:.2f}  ({(cw.iloc[-1]/cw.max()-1)*100:.1f}% from ATH)")
for day in ["2025-10-13", "2026-11-05", "2026-11-11", "2026-11-12"]:
    s = cw.loc[:day]
    print(f"  close on/before {day}: {s.iloc[-1]:.2f} ({s.index[-1].date()})")
low = cw.loc["2026-10-25":"2026-11-08"]
print(f"  low near Nov 5: {low.min():.2f} on {low.idxmin().date()}; Nov 11 vs low {(cw.loc[:'2026-11-11'].iloc[-1]/low.min()-1)*100:+.1f}%")
print(f"  low since 2025-10-13: {cw.loc['2025-10-13':].min():.2f} on {cw.loc['2025-10-13':].idxmin().date()}; "
      f"drop from 2025-10-13 close {(cw.loc['2025-10-13':].min()/cw.loc[:'2025-10-13'].iloc[-1]-1)*100:.1f}%")
print(f"  from 74 back to the ATH close: {(cw.max()/74-1)*100:+.0f}%")
l = c["LLY"].dropna()
print(f"LLY {l.loc[:'2025-08-11'].iloc[-1]:.2f} (2025-08-11) -> {l.loc[:'2026-11-09'].iloc[-1]:.2f} (2026-11-09): "
      f"{(l.loc[:'2026-11-09'].iloc[-1]/l.loc[:'2025-08-11'].iloc[-1]-1)*100:+.1f}%")
print("CRWV last 15 closes:", cw.tail(15).round(2).to_dict())

print("\n" + "=" * 80, "\n4. 200-DAY TREND FILTER vs BUY-AND-HOLD (next-day execution, 5bp per switch)\n")


def stats(eq):
    eq = eq.dropna()
    rr = eq.pct_change().dropna()
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    return {"CAGR%": round(((eq.iloc[-1] / eq.iloc[0]) ** (1 / yrs) - 1) * 100, 1),
            "MaxDD%": round((eq / eq.cummax() - 1).min() * 100, 1),
            "Sharpe": round(rr.mean() / rr.std() * np.sqrt(252), 2)}


rows = {}
for tk, start, w in [("SPY", "1995-01-01", 200), ("QQQ", "1999-03-10", 200), ("NVDA", "2000-01-01", 200),
                     ("CRWV", "2025-03-28", 50)]:
    p = dl(tk, start).iloc[:, 0].dropna()
    sma = p.rolling(w).mean()
    sig = (p > sma).astype(float).shift(1)  # decided at close, held from next day
    ret = p.pct_change()
    cost = sig.diff().abs().fillna(0) * 0.0005
    strat = (1 + (sig * ret - cost).fillna(0)).cumprod()
    bh = (1 + ret.fillna(0)).cumprod()
    first = sma.first_valid_index()
    rows[f"{tk} buy&hold"] = {**stats(bh.loc[first:] / bh.loc[first]), "switches": "-"}
    rows[f"{tk} {w}d filter"] = {**stats(strat.loc[first:] / strat.loc[first]), "switches": int(sig.diff().abs().sum())}
    print(f"{tk}: from {first.date()}, in market {sig.loc[first:].mean()*100:.0f}% of days, today {'above' if p.iloc[-1] > sma.iloc[-1] else 'below'} its {w}d average ({sma.iloc[-1]:.2f})")
print(pd.DataFrame(rows).T.to_string())

print("\n" + "=" * 80, "\n5. MACRO REGIMES (FRED CPIAUCSL, INDPRO), monthly, 1960-\n")
try:
    fred = {}
    for s in ["CPIAUCSL", "INDPRO"]:
        f = pd.read_csv(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={s}", index_col=0, parse_dates=True)
        fred[s] = pd.to_numeric(f.iloc[:, 0], errors="coerce")
    m = pd.DataFrame(fred).loc["1959":]
    yoy = m.pct_change(12) * 100
    acc = yoy.diff(3)  # change in the YoY rate over 3 months
    regime = np.select([(acc.INDPRO > 0) & (acc.CPIAUCSL <= 0), (acc.INDPRO > 0) & (acc.CPIAUCSL > 0),
                        (acc.INDPRO <= 0) & (acc.CPIAUCSL > 0), (acc.INDPRO <= 0) & (acc.CPIAUCSL <= 0)],
                       ["goldilocks", "reflation", "stagflation", "disinflation/deflation"], "na")
    reg = pd.Series(regime, index=m.index).shift(1)  # use last month's known data (ignores publication lag)
    print("Share of months by regime since 1960:", reg.loc["1960":].value_counts(normalize=True).round(2).to_dict())
    print("Latest regime reading:", reg.dropna().index[-1].date(), reg.dropna().iloc[-1])
    mk = dl(["^GSPC", "^IXIC", "XLK", "XLV", "XLU", "XLP", "TLT"], "1960-01-01").resample("MS").last().pct_change() * 100
    tab = mk.join(reg.rename("regime")).dropna(subset=["regime"])
    out = tab.groupby("regime").mean().round(2)
    out["months(S&P)"] = tab.groupby("regime")["^GSPC"].count()
    print("Average monthly return % by regime (each column uses its own available history):")
    print(out.to_string())
    tab["NASDAQ-S&P"] = tab["^IXIC"] - tab["^GSPC"]
    tab["XLK-S&P"] = tab["XLK"] - tab["^GSPC"]
    print("\nNasdaq minus S&P (1971-) and XLK minus S&P (1999-), mean monthly pp:")
    print(tab.groupby("regime")[["NASDAQ-S&P", "XLK-S&P"]].mean().round(2).to_string())
except Exception as e:
    print("FRED step failed:", e)
