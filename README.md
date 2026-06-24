# Volatility Atlas · Nifty 50

A dark, interactive dashboard showing every day the Nifty 50 moved by each gain/loss bucket, from 2008 to today.

---

## Setup (2 steps)

### Step 1 — Install Python dependency

```bash
pip install yfinance
```

### Step 2 — Generate the data file

```bash
python generate_data.py
```

This fetches Nifty 50 daily data from Yahoo Finance and writes `data.json`
into the same folder. Takes about 10–20 seconds.

---

## Running the dashboard

Because the dashboard reads `data.json` via `fetch()`, you need a local server
(browsers block direct file reads for security).

```bash
python -m http.server 8000
```

Then open: **http://localhost:8000**

---

## Project structure

```
nifty-volatility/
├── generate_data.py   ← run this first; fetches data, writes data.json
├── data.json          ← auto-generated; don't edit manually
├── index.html         ← the entire dashboard (HTML + CSS + JS, no build step)
└── README.md          ← this file
```

---

## How to update the data

Just re-run the generator:

```bash
python generate_data.py
```

Then refresh your browser. The dashboard reads `data.json` fresh on every load.

---

## Changing the date range

Open `generate_data.py` and edit these two lines near the top:

```python
START_DATE  = "2008-01-01"   # ← change this
END_DATE    = datetime.today().strftime("%Y-%m-%d")   # ← or hardcode a date
```

---

## Gain buckets

| Bucket   | Color       |
|----------|-------------|
| > +5%    | Bright green |
| +4–5%   | Green        |
| +3–4%   | Green        |
| +2–3%   | Dark green   |
| +1–2%   | Very dark green |
| 0–+1%   | Grey         |
| -1–0%   | Dark red     |
| -2–-1%  | Red          |
| -3–-2%  | Red          |
| < -3%   | Bright red   |

---

## Dashboard features

- **Year × Gain Bucket bands** — each year is one full-width bar split by bucket share. The rightmost number shows days with > +2% gains.
- **Click any year** — drills into a scatter plot of every trading day in that year, coloured by bucket, with stem lines connecting big-move days to the zero axis.
- **Hover any dot** — shows date, exact return %, and bucket.
- **Bucket distribution cards** — overall frequency of each bucket across all years.
- **Back link** — returns to the year overview.

---

## Requirements

- Python 3.8+
- `yfinance` (for data generation only)
- Any modern browser (Chrome, Firefox, Safari, Edge)
- No npm, no build step, no other dependencies
