import os
import json
import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import execute_values

load_dotenv()

database_url = os.getenv("DATABASE_URL")

if not database_url:
    raise RuntimeError("DATABASE_URL was not found. Check your .env file.")

conn = psycopg2.connect(database_url, connect_timeout=30, sslmode='require')
cur = conn.cursor()

with open("data.json") as f:
    data = json.load(f)

rows = []
for year_records in data["years"].values():
    for r in year_records:
        rows.append((
            r["date"], r["year"], r["month"], r["day_of_week"],
            r["return"], r["gap"], r["intraday"], r["day_range"],
            r["next_return"], r["volume"], r["bucket"],
            r["dte_monthly"], r["dte_weekly"],
            r["is_monthly_expiry"], r["is_weekly_expiry"], r["is_expiry_week"],
            r["gap_dominated"], r["expiry_regime"]
        ))
        
print(f"Inserting {len(rows)} rows...")

execute_values(cur, """
    INSERT INTO nifty50
    (date, year, month, day_of_week, return_pct, gap, intraday, day_range,
     next_return, volume, bucket, dte_monthly, dte_weekly,
     is_monthly_expiry, is_weekly_expiry, is_expiry_week,
     gap_dominated, expiry_regime)
    VALUES %s
""", rows)

conn.commit()
print(f"Inserted {len(rows)} rows — done!")
cur.close()
conn.close()
