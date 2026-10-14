"""Checks the 건디와 너드들 reel "AI로 주식 자동매매 시스템" (shared 2026-10-13).

The reel's on-screen rules (written by Cursor from a 2020 to June 2026 backtest):
  Buy when all hold: RSI(14) <= 45; volume >= 1.5x its 20-day average;
                     close >= 80% of the 52-week high; S&P 500 above its 200-day average.
  Sell: +15% profit, or RSI >= 60; stop loss -5%.
The reel claims +181.1% (about 17.5% a year) with 0.88 trades a month and a 64.7% win rate.

Test: one position at a time, all-in, over a fixed list of 30 US mega-caps (survivorship
bias flatters the result). Signals on the close, entry at the next open. The stop and target
are checked against each day's low and high (the stop first if both are hit). An RSI exit
fills at the next open. Costs are per side.
In-sample: 2020-01 to 2026-06 (the creator's window). Out-of-sample: 2010 to 2019.
"""
import numpy as np
import pandas as pd
import yfinance as yf

UNIVERSE = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "AVGO", "TSLA", "BRK-B", "JPM",
            "V", "MA", "UNH", "XOM", "LLY", "JNJ", "PG", "HD", "COST", "WMT",
            "ORCL", "NFLX", "KO", "PEP", "MRK", "ABBV", "CVX", "BAC", "ADBE", "CRM"]

raw = yf.download(UNIVERSE + ["SPY"], start="2008-06-01", auto_adjust=True, progress=False)
O, H, L, C, V = (raw[k] for k in ["Open", "High", "Low", "Close", "Volume"])
print("Data through", C.index[-1].date())


def rsi(s, n=14):
    d = s.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn)


R = C.apply(rsi)
volx = V / V.rolling(20).mean()
near_high = C / C.rolling(252).max()
spy_up = C["SPY"] > C["SPY"].rolling(200).mean()
signal = (R <= 45) & (volx >= 1.5) & (near_high >= 0.80)
signal = signal[UNIVERSE].where(spy_up, False)


def run(start, end, cost):
    idx = C.loc[start:end].index
    eq, cash, pos, trades, curve = 1.0, 1.0, None, [], []
    for i, day in enumerate(idx[:-1]):
        nxt = idx[i + 1]
        if pos:
            t = pos["t"]
            lo, hi, op = L.at[nxt, t], H.at[nxt, t], O.at[nxt, t]
            stop, tgt = pos["px"] * 0.95, pos["px"] * 1.15
            exit_px = None
            if pos["rsi_exit"]:
                exit_px = op
            elif lo <= stop:
                exit_px = min(op, stop)
            elif hi >= tgt:
                exit_px = max(op, tgt)
            if exit_px is not None:
                r = exit_px / pos["px"] * (1 - cost) / (1 + cost) - 1
                cash *= 1 + r
                trades.append((pos["t"], pos["d"].date(), nxt.date(), round(r * 100, 2)))
                pos = None
            else:
                pos["rsi_exit"] = R.at[nxt, t] >= 60
        elif signal.loc[day].any():
            cands = signal.loc[day][signal.loc[day]].index
            t = R.loc[day, cands].idxmin()
            pos = {"t": t, "px": O.at[nxt, t], "d": nxt, "rsi_exit": False}
        mark = cash * (C.at[nxt, pos["t"]] / pos["px"]) if pos else cash
        curve.append((nxt, mark))
    s = pd.Series(dict(curve))
    return s, trades


def stats(s):
    r = s.pct_change().dropna()
    yrs = (s.index[-1] - s.index[0]).days / 365.25
    return {"Total%": round((s.iloc[-1] / s.iloc[0] - 1) * 100, 1),
            "CAGR%": round(((s.iloc[-1] / s.iloc[0]) ** (1 / yrs) - 1) * 100, 2),
            "MaxDD%": round((s / s.cummax() - 1).min() * 100, 1),
            "Sharpe": round(r.mean() / r.std() * np.sqrt(252), 2) if r.std() > 0 else np.nan}


for label, start, end in [("In-sample 2020-01 to 2026-06", "2020-01-01", "2026-06-30"),
                          ("Out-of-sample 2010 to 2019", "2010-01-01", "2019-12-31"),
                          ("Live window 2026-06 to now", "2026-06-01", None)]:
    print("\n" + "=" * 78 + f"\n{label}")
    spy = C["SPY"].loc[start:end].dropna()
    print("  SPY buy-and-hold:", stats(spy))
    for cost in [0.001, 0.0025]:
        s, tr = run(start, end, cost)
        rets = [t[3] for t in tr]
        months = (s.index[-1] - s.index[0]).days / 30.44
        wins = np.mean([x > 0 for x in rets]) * 100 if rets else np.nan
        print(f"  Strategy, cost {cost*100:.2f}%/side:", stats(s),
              f"trades={len(tr)} ({len(tr)/months:.2f}/month) win%={wins:.1f}")
    if label.startswith("Live"):
        print("  Trades:", tr)

# How often all four buy conditions line up, per stock-day (shows how rare the signal is).
print("\nShare of stock-days with a buy signal, 2020-2026:",
      f"{signal.loc['2020':].values.mean()*100:.2f}%")
