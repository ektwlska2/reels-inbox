"""Checks the claims in the Josh Answers reel "TLT is a psyop" (shared 2026-10-13).

1. Long-run: TLT and IEF against SPY, a dividend-stock fund (SCHD, VYM) and XLU.
2. After bond-volatility spikes (MOVE index, or TLT's own realized volatility), what do
   TLT and SPY do over the next day, week, month and quarter? Does volatility fall back
   (which hurts option buyers)?
3. Recent prices for TLT, XLU, DKS and HD, to check the "last week" XLU claim and the
   "multi-year lows" claim.
"""
import numpy as np
import pandas as pd
import yfinance as yf

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 20)


def closes(tickers, start="2002-07-30"):
    df = yf.download(tickers, start=start, auto_adjust=True, progress=False)["Close"]
    return df if isinstance(df, pd.DataFrame) else df.to_frame(tickers)


def stats(series):
    s = series.dropna()
    r = s.pct_change().dropna()
    years = (s.index[-1] - s.index[0]).days / 365.25
    cagr = (s.iloc[-1] / s.iloc[0]) ** (1 / years) - 1
    dd = (s / s.cummax() - 1).min()
    sharpe = r.mean() / r.std() * np.sqrt(252)
    return {"start": s.index[0].date(), "CAGR%": round(cagr * 100, 2), "MaxDD%": round(dd * 100, 1),
            "Sharpe(rf=0)": round(sharpe, 2), "Vol%": round(r.std() * np.sqrt(252) * 100, 1)}


print("=" * 80, "\n1. BUY AND HOLD (total return, dividends reinvested)\n")
px = closes(["TLT", "IEF", "SPY", "XLU", "SCHD", "VYM"])
print("Data through", px.index[-1].date())
for start in ["2002-07-30", "2011-10-21", "2016-10-13", "2021-10-13"]:
    sub = px.loc[start:]
    rows = {t: stats(sub[t]) for t in sub.columns if sub[t].dropna().index[0] <= pd.Timestamp(start) + pd.Timedelta(days=10)}
    print(f"\nFrom {start}:")
    print(pd.DataFrame(rows).T)

print("\nRolling 10-year CAGR, SPY minus TLT (percentage points):")
r10 = (px[["SPY", "TLT"]] / px[["SPY", "TLT"]].shift(2520)) ** (1 / 10) - 1
d = (r10["SPY"] - r10["TLT"]).dropna() * 100
print(f"  share of 10y windows where SPY beat TLT: {(d > 0).mean()*100:.1f}%  median gap {d.median():.1f}pp  worst {d.min():.1f}pp")

print("\nCorrelation of daily returns (whole period):")
print(px[["TLT", "SPY", "XLU", "VYM"]].pct_change().corr().round(2))

print("\n" + "=" * 80, "\n2. AFTER BOND-VOLATILITY SPIKES\n")
tlt = px["TLT"].dropna()
spy = px["SPY"].dropna()
ret = tlt.pct_change()
rv21 = ret.rolling(21).std() * np.sqrt(252)

move = closes("^MOVE", start="2002-01-01")
move = move.iloc[:, 0].dropna() if not move.empty else pd.Series(dtype=float)
print("MOVE index rows:", len(move), "" if move.empty else f"({move.index[0].date()} to {move.index[-1].date()}, last {move.iloc[-1]:.1f})")


def spikes(signal, window=252, q=0.95, gap=21):
    thr = signal.rolling(window).quantile(q)
    hit = signal > thr
    days, last = [], None
    for dt in signal.index[hit.fillna(False).values]:
        if last is None or (signal.index.get_loc(dt) - signal.index.get_loc(last)) > gap:
            days.append(dt)
        last = dt if last is None or (signal.index.get_loc(dt) - signal.index.get_loc(last)) > gap else last
    return pd.DatetimeIndex(days)


def forward(series, days, horizons=(1, 5, 21, 63)):
    out = {}
    idx = series.index
    for h in horizons:
        vals = []
        for d in days:
            i = idx.searchsorted(d)
            if i + h < len(idx):
                vals.append(series.iloc[i + h] / series.iloc[i] - 1)
        v = pd.Series(vals)
        base = (series.shift(-h) / series - 1).dropna()
        out[f"{h}d"] = {"n": len(v), "mean%": round(v.mean() * 100, 2), "hit%": round((v > 0).mean() * 100, 0),
                        "all-days mean%": round(base.mean() * 100, 2)}
    return pd.DataFrame(out)


signals = {"TLT 21d realized vol": rv21.dropna()}
if not move.empty:
    signals["MOVE index"] = move
for name, sig in signals.items():
    ev = spikes(sig)
    print(f"\nSignal: {name} above its trailing-1y 95th percentile, first day of each episode: {len(ev)} episodes")
    print("Last 8 episodes:", [d.date().isoformat() for d in ev[-8:]])
    print("TLT forward returns:\n", forward(tlt, ev))
    print("SPY forward returns:\n", forward(spy, ev))
    # does volatility mean-revert? realized vol over next 21d vs prior 21d
    ratios = []
    for d in ev:
        i = ret.index.searchsorted(d)
        if i + 21 < len(ret) and i >= 21:
            prior = ret.iloc[i - 20:i + 1].std()
            nxt = ret.iloc[i + 1:i + 22].std()
            ratios.append(nxt / prior)
    rr = pd.Series(ratios)
    print(f"TLT realized vol next 21d / prior 21d: median {rr.median():.2f}, share below 1: {(rr < 1).mean()*100:.0f}%")
    # absolute TLT move over next 21 days vs move an option priced on trailing vol would expect
    exp_moves, act_moves = [], []
    for d in ev:
        i = tlt.index.searchsorted(d)
        if i + 21 < len(tlt):
            exp_moves.append(rv21.iloc[i] * np.sqrt(21 / 252) * np.sqrt(2 / np.pi))
            act_moves.append(abs(tlt.iloc[i + 21] / tlt.iloc[i] - 1))
    print(f"Mean |TLT 21d move| {np.mean(act_moves)*100:.2f}% vs move implied by trailing vol {np.mean(exp_moves)*100:.2f}%")

print("\n" + "=" * 80, "\n3. RECENT PRICES\n")
rec = closes(["TLT", "XLU", "DKS", "HD", "SPY", "^TNX", "^TYX"], start="2023-01-01")
last = rec.index[-1]
print("Last date:", last.date())
tbl = {}
for t in rec.columns:
    s = rec[t].dropna()
    tbl[t] = {"last": round(s.iloc[-1], 2),
              "5d%": round((s.iloc[-1] / s.iloc[-6] - 1) * 100, 2),
              "10d%": round((s.iloc[-1] / s.iloc[-11] - 1) * 100, 2),
              "1m%": round((s.iloc[-1] / s.iloc[-22] - 1) * 100, 2),
              "52w low": round(s.iloc[-252:].min(), 2), "52w high": round(s.iloc[-252:].max(), 2),
              "3y low": round(s.min(), 2),
              "pct above 3y low": round((s.iloc[-1] / s.min() - 1) * 100, 1)}
print(pd.DataFrame(tbl).T)
print("\nLast 15 closes:")
print(rec.tail(15).round(2))
for t in ["DKS", "HD", "XLU", "TLT"]:
    info = yf.Ticker(t)
    try:
        dv = info.dividends
        ttm = dv[dv.index > dv.index[-1] - pd.Timedelta(days=365)].sum()
        print(f"{t}: trailing-12m dividends {ttm:.2f}, yield {ttm / rec[t].dropna().iloc[-1] * 100:.2f}%")
    except Exception as e:
        print(t, "dividends unavailable", e)
    try:
        sp = info.splits
        print(f"  splits since 2020: {sp[sp.index > '2020-01-01'].to_dict()}")
    except Exception:
        pass
