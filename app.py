"""
app.py
------
Flask API server for the Nifty 50 dashboard.
Reads from local PostgreSQL and serves data to index.html.

Requirements:
    pip install flask psycopg2-binary python-dotenv

Usage:
    python app.py
"""

from flask import Flask, jsonify
import psycopg2
import psycopg2.extras
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder='.', template_folder='.')

# ── DB connection ─────────────────────────────────────────────────────────────
def get_conn():
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return psycopg2.connect(database_url)
    # Fallback to local defaults
    return psycopg2.connect(
        host="localhost",
        port=5432,
        dbname="nifty_db",
        user="postgres",
        password=os.getenv("PGPASSWORD", "")
    )


# ── /api/data — everything the dashboard needs in one call ───────────────────
@app.route("/api/data")
def api_data():
    conn = get_conn()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("""
        SELECT
            TO_CHAR(date, 'YYYY-MM-DD') AS date,
            year, month, day_of_week,
            return_pct      AS return,
            gap, intraday, day_range, next_return,
            volume, bucket,
            dte_monthly, dte_weekly,
            is_monthly_expiry, is_weekly_expiry, is_expiry_week,
            gap_dominated, expiry_regime
        FROM nifty50
        ORDER BY date ASC
    """)

    rows = cur.fetchall()
    cur.close()
    conn.close()

    # Group by year (same shape as data.json so index.html needs minimal changes)
    years = {}
    for row in rows:
        y = str(row["year"])
        if y not in years:
            years[y] = []
        years[y].append(dict(row))

    all_days = list(rows)
    total    = len(all_days)

    big_gain = [r for r in all_days if float(r["return"] or 0) >=  2.0]
    big_loss = [r for r in all_days if float(r["return"] or 0) <= -2.0]
    big_both = [r for r in all_days if abs(float(r["return"] or 0)) >= 2.0]
    expiry_week_days = [r for r in all_days if r["is_expiry_week"]]
    big_expiry = [r for r in expiry_week_days if abs(float(r["return"] or 0)) >= 2.0]

    year_list = sorted(years.keys())

    meta = {
        "ticker":           "^NSEI",
        "years":            len(years),
        "trading_days":     total,
        "big_gain_days":    len(big_gain),
        "big_loss_days":    len(big_loss),
        "big_both_days":    len(big_both),
        "expiry_week_days": len(expiry_week_days),
        "big_expiry_days":  len(big_expiry),
        "date_range":       f"{all_days[0]['date']} to {all_days[-1]['date']}" if all_days else "",
        "year_list":        year_list,
    }

    return jsonify({"meta": meta, "years": years})


# ── Serve index.html at root ──────────────────────────────────────────────────
@app.route("/")
def index():
    return app.send_static_file("index.html")


if __name__ == "__main__":
    app.run(debug=True, port=5000)