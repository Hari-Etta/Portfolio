"""Profiles raw bronze data in S3 — document the findings in the README.
This is the 'data preparation, validation, QA' part of the JD, done honestly."""
import os

import duckdb
from dotenv import load_dotenv

load_dotenv()
con = duckdb.connect()
con.execute("INSTALL httpfs; LOAD httpfs;")
con.execute(f"""
    CREATE SECRET s3_secret (
        TYPE S3,
        KEY_ID '{os.environ["AWS_ACCESS_KEY_ID"]}',
        SECRET '{os.environ["AWS_SECRET_ACCESS_KEY"]}',
        REGION '{os.environ.get("AWS_REGION", "us-east-2")}'
    );
""")
BUCKET = os.environ["S3_BUCKET"]
SRC = (f"read_parquet('s3://{BUCKET}/bronze/statcast/season=*/*.parquet', "
       "union_by_name=true, hive_partitioning=true)")
ROSTERS = f"read_parquet('s3://{BUCKET}/bronze/mlb/rosters/snapshot_date=*/*.parquet', hive_partitioning=true)"

checks = {
    "date_coverage": f"""
        SELECT MIN(game_date) AS first_date, MAX(game_date) AS last_date,
               COUNT(DISTINCT game_date) AS game_days
        FROM {SRC}""",
    "rows_by_game_type": f"SELECT game_type, COUNT(*) AS pitches FROM {SRC} GROUP BY 1 ORDER BY 2 DESC",
    "games_and_pitchers": f"SELECT COUNT(DISTINCT game_pk) games, COUNT(DISTINCT pitcher) pitchers FROM {SRC}",
    "null_rates_key_cols": f"""
        SELECT
          AVG(CASE WHEN pitch_type    IS NULL THEN 1 ELSE 0 END) AS pitch_type_null,
          AVG(CASE WHEN release_speed IS NULL THEN 1 ELSE 0 END) AS velo_null,
          AVG(CASE WHEN plate_x       IS NULL THEN 1 ELSE 0 END) AS plate_x_null,
          AVG(CASE WHEN description   IS NULL THEN 1 ELSE 0 END) AS description_null
        FROM {SRC}""",
    "duplicate_pitches": f"""
        SELECT COUNT(*) AS duplicated_keys FROM (
          SELECT game_pk, at_bat_number, pitch_number, COUNT(*) c
          FROM {SRC} GROUP BY 1,2,3 HAVING c > 1)""",
    "velocity_outliers": f"""
        SELECT COUNT(*) AS suspicious_velo FROM {SRC}
        WHERE TRY_CAST(release_speed AS DOUBLE) < 50 OR TRY_CAST(release_speed AS DOUBLE) > 106""",
    "pitch_type_mix": f"SELECT pitch_type, COUNT(*) n FROM {SRC} GROUP BY 1 ORDER BY 2 DESC",
    "roster_size_per_team": f"""
        SELECT snapshot_date, MIN(n) AS smallest, MAX(n) AS largest, COUNT(*) AS teams
        FROM (SELECT snapshot_date, team_id, COUNT(*) n FROM {ROSTERS} GROUP BY 1,2)
        GROUP BY 1""",
}
for name, sql in checks.items():
    print(f"\n=== {name} ===")
    print(con.execute(sql).df().to_string(index=False))
