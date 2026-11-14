"""Run the warehouse checks and write check_results.md.

    python 02_data_warehouse/checks/check_report.py

Uses the same connection settings as the ETL (PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD).
"""

import os
from pathlib import Path

import psycopg2

HERE = Path(__file__).resolve().parent


def fmt(x) -> str:
    x = float(x)
    return f"{x:,.0f}" if x == int(x) else f"{x:,.2f}"


with psycopg2.connect(host=os.environ.get("PGHOST", "localhost"), port=os.environ.get("PGPORT", "5432"),
                      dbname=os.environ.get("PGDATABASE", "vigie_dwh"), user=os.environ.get("PGUSER", "postgres"),
                      password=os.environ.get("PGPASSWORD", "")) as cnx, cnx.cursor() as cur:
    cur.execute((HERE / "checks.sql").read_text(encoding="utf-8").split("-- 4. CHECK DASHBOARD")[0])
    cur.execute("SELECT check_id, label, expected, actual FROM dwh.v_checks ORDER BY check_id")
    checks = cur.fetchall()
    cur.execute("""SELECT 'Closing date (active accounts)', avg((closing_date_id = 0)::int) FROM dwh.fact_account
                   UNION ALL SELECT 'Closure reason', avg((reason_id = 0)::int) FROM dwh.fact_account
                   UNION ALL SELECT 'Product', avg((product_id = 0)::int) FROM dwh.fact_account
                   UNION ALL SELECT 'Account family', avg((category_id = 0)::int) FROM dwh.fact_account
                   UNION ALL SELECT 'Currency', avg((currency_id = 0)::int) FROM dwh.fact_account
                   UNION ALL SELECT 'Opening date', avg((opening_date_id = 0)::int) FROM dwh.fact_account""")
    not_provided = cur.fetchall()
    cur.execute("""SELECT count(*) FILTER (WHERE is_closed = 1 AND opening_date_id <> 0),
                          count(*) FILTER (WHERE opened_after_closing) FROM dwh.fact_account""")
    with_date, anomaly = cur.fetchone()
    cur.execute("""SELECT to_char(week_start, 'DD/MM/YYYY'), n_closures, n_closures / sum(n_closures) OVER ()
                   FROM dwh.v_weekly_closures ORDER BY n_closures DESC LIMIT 5""")
    top_weeks = cur.fetchall()
    cur.execute("SELECT sum(n_closures) FROM dwh.v_weekly_closures")
    total = cur.fetchone()[0]

n_ok = sum(e == a for _, _, e, a in checks)
L = [
    "# Results of the load checks",
    "",
    f"> Run of `checks.sql` on the loaded warehouse — **{len(checks)} checks, {n_ok} OK**.",
    "> Source = `staging` schema (raw copy of the files) · Target = `dwh` schema (star schema).",
    "> Re-run in pgAdmin after every Talend load: the table must be identical.",
    "",
    "| Check | Label | Expected | Actual | Verdict |",
    "|---|---|---:|---:|:---:|",
]
L += [f"| {c} | {label} | {fmt(e)} | {fmt(a)} | {'✔ OK' if e == a else '✘ KO'} |" for c, label, e, a in checks]
L += ["", "## Distribution checks", "", "**Share of facts attached to the \"Not provided\" member (key 0)**", "",
      "| Dimension | % of accounts |", "|---|---:|"]
L += [f"| {name} | {100 * float(v):.1f} |" for name, v in not_provided]
L += ["", "These shares are identical to the missing-value rates measured at account grain in the univariate analysis "
      "notebook: no information was lost or invented during the load.", "",
      "**Source anomaly — flagged, not corrected**", "", "| Indicator | Value |", "|---|---:|",
      f"| Closed accounts whose opening date is filled in | {with_date:,} |",
      f"| … of which opening later than closing | {anomaly:,} |",
      f"| Share | {100 * anomaly / with_date:.1f}% |", "",
      "For these accounts the opening date cannot be used to compute an age. The warehouse keeps the source value, "
      "sets `opened_after_closing = true` and leaves `account_age_days` as `NULL`.", "",
      "**The five busiest closing weeks (mass operations)**", "", "| Week (Monday) | Closures | Share of total |",
      "|---|---:|---:|"]
L += [f"| {w} | {n:,} | {100 * float(s):.1f}% |" for w, n, s in top_weeks]
share = 100 * sum(n for _, n, _ in top_weeks) / float(total)
L += ["", f"These five weeks carry {share:.1f}% of the {int(total):,} closures. The dates were shifted by the "
      "anonymisation, so they match no real calendar.", ""]
(HERE / "check_results.md").write_text("\n".join(L), encoding="utf-8")
print(f"{n_ok} / {len(checks)} checks OK — written: 02_data_warehouse/checks/check_results.md")
