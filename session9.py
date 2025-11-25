import psycopg2
import pandas as pd
import matplotlib.pyplot as plt

STUDENT_URI = (
    "postgresql://finmstudents:strong_password@"
    "finm32500db-uchicago-finm32500.d.aivencloud.com:16304/defaultdb?sslmode=require"
)


def run_sql_block(conn, sql):
    cur = conn.cursor()
    cur.execute(sql)
    cur.close()


def create_bar_table(conn):
    create_sql = """
    CREATE TABLE IF NOT EXISTS student_data.bar_data_cmbenello AS
    SELECT
      ticker,
      interval_start,
      (array_agg(open ORDER BY datetime ASC))[1] AS open,
      max(high) AS high,
      min(low) AS low,
      (array_agg(close ORDER BY datetime DESC))[1] AS close,
      sum(volume) AS volume
    FROM (
      SELECT
        ticker,
        datetime,
        open,
        high,
        low,
        close,
        volume,
        date_trunc('hour', datetime)
          + floor(date_part('minute', datetime) / 10)::int * interval '10 minutes' AS interval_start
      FROM public.intraday_prices
    ) s
    GROUP BY ticker, interval_start
    ORDER BY ticker, interval_start;
    """
    run_sql_block(conn, create_sql)

    alter_sql = """
    ALTER TABLE student_data.bar_data_cmbenello
      ADD COLUMN IF NOT EXISTS id BIGSERIAL PRIMARY KEY;

    CREATE UNIQUE INDEX IF NOT EXISTS bar_data_cmbenello_ticker_interval_uix
      ON student_data.bar_data_cmbenello (ticker, interval_start);

    CREATE INDEX IF NOT EXISTS bar_data_cmbenello_interval_idx
      ON student_data.bar_data_cmbenello (interval_start);
    """
    run_sql_block(conn, alter_sql)


def create_mapped_events(conn):
    sql = """
    CREATE TABLE IF NOT EXISTS student_data.mapped_events_cmbenello AS
    SELECT
      a.id AS article_id,
      a.ticker,
      a.title,
      a.link,
      a.published,
      b.interval_start
    FROM public.news_articles a
    JOIN LATERAL (
      SELECT interval_start
      FROM student_data.bar_data_cmbenello
      WHERE ticker = a.ticker
      ORDER BY abs(EXTRACT(EPOCH FROM (student_data.bar_data_cmbenello.interval_start - a.published))) ASC
      LIMIT 1
    ) b ON true
    WHERE a.published IS NOT NULL;
    """
    run_sql_block(conn, sql)


def create_bar_returns(conn):
    sql = """
    CREATE TABLE IF NOT EXISTS student_data.bar_returns_cmbenello AS
    SELECT
      id,
      ticker,
      interval_start,
      close,
      lag(close) OVER (PARTITION BY ticker ORDER BY interval_start) AS prev_close,
      CASE
        WHEN lag(close) OVER (PARTITION BY ticker ORDER BY interval_start) IS NULL
          THEN NULL
        ELSE ln(close / lag(close) OVER (PARTITION BY ticker ORDER BY interval_start))
      END AS log_return
    FROM student_data.bar_data_cmbenello;
    """
    run_sql_block(conn, sql)


def create_event_window_returns(conn):
    sql = """
    CREATE TABLE IF NOT EXISTS student_data.event_window_returns_cmbenello AS
    SELECT
      e.article_id,
      e.ticker,
      e.published,
      e.interval_start AS event_interval,
      r.interval_start,
      r.log_return,
      EXTRACT(EPOCH FROM (r.interval_start - e.interval_start)) / 600 AS rel_bar_index
    FROM student_data.mapped_events_cmbenello e
    JOIN student_data.bar_returns_cmbenello r
      ON r.ticker = e.ticker
      AND r.interval_start BETWEEN e.interval_start - interval '60 minutes'
                               AND e.interval_start + interval '60 minutes';
    """
    run_sql_block(conn, sql)


def create_event_study_results(conn):
    sql = """
    CREATE TABLE IF NOT EXISTS student_data.event_study_results_cmbenello AS
    SELECT
      rel_bar_index::int AS rel_bar,
      count(log_return) AS n_events,
      avg(log_return) AS mean_log_return,
      stddev_pop(log_return) / sqrt(count(log_return)) AS stderr_mean
    FROM student_data.event_window_returns_cmbenello
    GROUP BY rel_bar_index::int
    ORDER BY rel_bar;
    """
    run_sql_block(conn, sql)


def plot_event_study(conn):
    query = """
    SELECT rel_bar, n_events, mean_log_return, stderr_mean
    FROM student_data.event_study_results_cmbenello
    ORDER BY rel_bar;
    """

    df = pd.read_sql(query, conn)

    if df.empty:
        print("event_study_results_cmbenello is empty; nothing to plot.")
        return

    df["mean_pct"] = df["mean_log_return"] * 100
    df["stderr_pct"] = df["stderr_mean"] * 100

    plt.figure(figsize=(10, 6))
    plt.plot(df["rel_bar"], df["mean_pct"], marker="o", label="Average log return (%)")
    plt.fill_between(
        df["rel_bar"],
        df["mean_pct"] - 1.96 * df["stderr_pct"],
        df["mean_pct"] + 1.96 * df["stderr_pct"],
        alpha=0.3,
        label="95% CI",
    )
    plt.axvline(0, linestyle="--", label="Event time")
    plt.xlabel("Relative bar index (10-minute bars)")
    plt.ylabel("Average log return (%)")
    plt.title("Event Study: Average 10-min Returns Around News")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig("event_study_returns_cmbenello.png", dpi=300)
    plt.show()
    print("Saved figure to event_study_returns_cmbenello.png")


def main():
    conn = psycopg2.connect(STUDENT_URI)
    conn.autocommit = True

    print("Creating 10-minute bar table...")
    create_bar_table(conn)
    print("Done bar_data_cmbenello.")

    print("Mapping news events to nearest bars...")
    create_mapped_events(conn)
    print("Done mapped_events_cmbenello.")

    print("Creating bar returns...")
    create_bar_returns(conn)
    print("Done bar_returns_cmbenello.")

    print("Creating event window returns...")
    create_event_window_returns(conn)
    print("Done event_window_returns_cmbenello.")

    print("Creating event study results...")
    create_event_study_results(conn)
    print("Done event_study_results_cmbenello.")

    print("Plotting event study...")
    plot_event_study(conn)

    conn.close()
    print("All done.")


if __name__ == "__main__":
    main()