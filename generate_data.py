"""
generate_data.py
----------------
Fetches Nifty 50 historical daily data using yfinance and writes data.json
for the Volatility Atlas dashboard.

Requirements:
    pip install yfinance pandas

Usage:
    python generate_data.py
"""

import json
import sys
from datetime import datetime, timedelta

try:
    import yfinance as yf
    import pandas as pd
    import pandas_market_calendars as mcal
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install with:  pip install yfinance pandas pandas_market_calendars")
    sys.exit(1)


# ── Config ────────────────────────────────────────────────────────────────────
TICKER      = "^NSEI"
START_DATE  = "2008-01-01"
END_DATE    = datetime.today().strftime("%Y-%m-%d")
OUTPUT_FILE = "data.json"
# ──────────────────────────────────────────────────────────────────────────────
# ── Expiry regime constants ───────────────────────────────────────────────────
from datetime import date

WEEKLY_OPTIONS_START = date(2019, 2, 1)   # Nifty weekly options launched
TUESDAY_EXPIRY_START = date(2025, 9, 1)   # SEBI shift: Thursday → Tuesday
EXPIRY_WEEKDAY_OLD   = 3                  # Thursday (0=Mon)
EXPIRY_WEEKDAY_NEW   = 1                  # Tuesday  (0=Mon)

# ── NSE holiday set ───────────────────────────────────────────────────────────
_nse = mcal.get_calendar("NSE")
_schedule = _nse.schedule(start_date="2008-01-01", end_date="2026-12-31")
NSE_TRADING_DAYS = set(_schedule.index.date)


def days_to_monthly_expiry(d):
    """How many calendar days until the next monthly expiry (holiday-adjusted)?"""
    y, m = d.year, d.month
    expiry = get_monthly_expiry(y, m)
    if d > expiry:
        # Roll to next month
        if m == 12:
            expiry = get_monthly_expiry(y + 1, 1)
        else:
            expiry = get_monthly_expiry(y, m + 1)
    return (expiry - d).days

def get_monthly_expiry(year, month):
    """Return the correct monthly expiry date, shifted back if it falls on a holiday."""
    # Determine which weekday is the expiry day for this date
    ref = date(year, month, 1)
    if date(year, month, 1) >= TUESDAY_EXPIRY_START:
        target_weekday = EXPIRY_WEEKDAY_NEW  # Tuesday
    else:
        target_weekday = EXPIRY_WEEKDAY_OLD  # Thursday

    # Find last occurrence of that weekday in the month
    if month == 12:
        last_day = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(year, month + 1, 1) - timedelta(days=1)

    while last_day.weekday() != target_weekday:
        last_day -= timedelta(days=1)

    # Shift back if it's a holiday
    while last_day not in NSE_TRADING_DAYS:
        last_day -= timedelta(days=1)

    return last_day


def get_weekly_expiry(d):
    """
    Return the next weekly expiry date on or after date d.
    Returns None if weekly options didn't exist yet (before Feb 2019).
    """
    if d < WEEKLY_OPTIONS_START:
        return None

    target_weekday = EXPIRY_WEEKDAY_NEW if d >= TUESDAY_EXPIRY_START else EXPIRY_WEEKDAY_OLD

    candidate = d
    # Find the next occurrence of the target weekday
    days_ahead = (target_weekday - d.weekday()) % 7
    candidate = d + timedelta(days=days_ahead)

    # Shift back if it's a holiday
    while candidate not in NSE_TRADING_DAYS:
        candidate -= timedelta(days=1)

    return candidate

def classify_bucket(r):
    """Return the gain-bucket label for a daily return (in %)."""
    if   r >  5:  return ">+5%"
    elif r >  4:  return "+4-5%"
    elif r >  3:  return "+3-4%"
    elif r >  2:  return "+2-3%"
    elif r >  1:  return "+1-2%"
    elif r >= 0:  return "0-+1%"
    elif r > -1:  return "-1-0%"
    elif r > -2:  return "-2--1%"
    elif r > -3:  return "-3--2%"
    else:          return "<-3%"


def main():
    print(f"Downloading {TICKER} from {START_DATE} to {END_DATE} ...")
    raw = yf.download(TICKER, start=START_DATE, end=END_DATE, progress=False)

    if raw.empty:
        print("No data returned. Check your internet connection or ticker symbol.")
        sys.exit(1)

    # Flatten multi-level columns if present
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = [col[0].lower() for col in raw.columns]
    else:
        raw.columns = [col.lower() for col in raw.columns]

    df = raw[["open", "high", "low", "close", "volume"]].copy()
    df = df.dropna()

    # ── Calculate returns ──────────────────────────────────────────────────
    df["close_return"] = df["close"].pct_change() * 100          # close-to-close
    df["gap"]          = (df["open"] / df["close"].shift(1) - 1) * 100   # overnight gap
    df["intraday"]     = (df["close"] / df["open"] - 1) * 100   # open-to-close
    df["day_range"]    = (df["high"] - df["low"]) / df["open"] * 100     # high-low range
    df["next_return"]  = df["close_return"].shift(-1)            # next day's return
    df = df.dropna(subset=["close_return"])

    # ── Calendar fields ────────────────────────────────────────────────────
    records = []
    prev_close = None

    for idx, row in df.iterrows():
        date = idx.to_pydatetime() if hasattr(idx, 'to_pydatetime') else datetime.strptime(str(idx)[:10], "%Y-%m-%d")
        date_str = date.strftime("%Y-%m-%d")

        ret         = round(float(row["close_return"]), 4)
        gap         = round(float(row["gap"]), 4) if not pd.isna(row["gap"]) else 0.0
        intraday    = round(float(row["intraday"]), 4)
        day_range   = round(float(row["day_range"]), 4)
        next_ret    = round(float(row["next_return"]), 4) if not pd.isna(row["next_return"]) else None
        volume      = int(row["volume"]) if not pd.isna(row["volume"]) else 0

        # Expiry timing
# Expiry timing
        d = date.date()
        dte_monthly       = days_to_monthly_expiry(d)
        monthly_exp       = get_monthly_expiry(d.year, d.month)
        is_monthly_expiry_day = (d == monthly_exp)
        is_expiry_week    = dte_monthly <= 7

        # Weekly expiry (None before Feb 2019)
        weekly_exp        = get_weekly_expiry(d)
        dte_weekly        = (weekly_exp - d).days if weekly_exp is not None else None
        is_weekly_expiry  = (d == weekly_exp) if weekly_exp is not None else None

        # Expiry regime
        if d >= TUESDAY_EXPIRY_START:
            expiry_regime = "tuesday"
        else:
            expiry_regime = "thursday"

        # Gap vs intraday
        gap_dominated = abs(gap) > abs(intraday)

        records.append({
            "date":               date_str,
            "return":             ret,
            "gap":                gap,
            "intraday":           intraday,
            "day_range":          day_range,
            "next_return":        next_ret,
            "volume":             volume,
            "bucket":             classify_bucket(ret),
            "month":              date.month,
            "year":               date.year,
            "day_of_week":        date.weekday(),
            "dte_monthly":        dte_monthly,
            "dte_weekly":         dte_weekly,
            "is_monthly_expiry":  is_monthly_expiry_day,
            "is_weekly_expiry":   is_weekly_expiry,
            "is_expiry_week":     is_expiry_week,
            "gap_dominated":      gap_dominated,
            "expiry_regime":      expiry_regime,
        })

    # ── Group by year ──────────────────────────────────────────────────────
    years_out = {}
    for r in records:
        y = str(r["year"])
        if y not in years_out:
            years_out[y] = []
        years_out[y].append(r)

    years_out = dict(sorted(years_out.items()))

    # ── Summary meta ───────────────────────────────────────────────────────
    all_days = records
    total    = len(all_days)

    def freq(days, threshold, direction="both"):
        if direction == "up":
            return [d for d in days if d["return"] >= threshold]
        elif direction == "down":
            return [d for d in days if d["return"] <= -threshold]
        else:
            return [d for d in days if abs(d["return"]) >= threshold]

    big = freq(all_days, 2.0)
    expiry_week_days = [d for d in all_days if d["is_expiry_week"]]
    big_expiry = freq(expiry_week_days, 2.0)

    meta = {
        "ticker":           TICKER,
        "generated_at":     datetime.now().isoformat(),
        "years":            len(years_out),
        "trading_days":     total,
        "big_gain_days":    len([d for d in all_days if d["return"] >= 2.0]),
        "big_loss_days":    len([d for d in all_days if d["return"] <= -2.0]),
        "big_both_days":    len(big),
        "expiry_week_days": len(expiry_week_days),
        "big_expiry_days":  len(big_expiry),
        "date_range":       f"{all_days[0]['date']} to {all_days[-1]['date']}",
        "year_list":        sorted(years_out.keys()),
    }

    final = {"meta": meta, "years": years_out}

    with open(OUTPUT_FILE, "w") as f:
        json.dump(final, f, separators=(",", ":"))

    pct = round(len(big) / total * 100, 1) if total else 0
    exp_pct = round(len(big_expiry) / len(expiry_week_days) * 100, 1) if expiry_week_days else 0
    print(f"Wrote {OUTPUT_FILE}")
    print(f"  {meta['years']} years · {total} trading days")
    print(f"  ±2% days: {len(big)} ({pct}% of all days)")
    print(f"  ±2% in expiry week: {len(big_expiry)} ({exp_pct}% of expiry-week days)")


if __name__ == "__main__":
    main()