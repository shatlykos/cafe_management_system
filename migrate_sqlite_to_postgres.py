"""
One-time migration from local SQLite to PostgreSQL (Neon).

Usage:
  export DATABASE_URL='postgresql://...'
  export SQLITE_PATH='/Users/.../cafe_data.sqlite3'   # optional
  python3 migrate_sqlite_to_postgres.py
"""

import os
import sqlite3
import psycopg
from psycopg.rows import dict_row

from database import CafeDatabase


TABLES_IN_ORDER = [
    "ingredients",
    "dishes",
    "recipe_items",
    "expenses",
    "sales",
    "clients",
    "breakfast_visits",
    "coffee_visits",
    "barcode_events",
]


def existing_ids(conn: sqlite3.Connection, table: str) -> set:
    cur = conn.cursor()
    cur.execute(f"SELECT id FROM {table}")
    return {row[0] for row in cur.fetchall()}


def table_exists_sqlite(conn: sqlite3.Connection, table_name: str) -> bool:
    cur = conn.cursor()
    cur.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (table_name,),
    )
    return cur.fetchone() is not None


def main():
    db_url = (os.getenv("DATABASE_URL") or "").strip()
    if not db_url:
        raise RuntimeError("DATABASE_URL is not set")

    sqlite_path = (os.getenv("SQLITE_PATH") or "cafe_data.sqlite3").strip()
    if not os.path.isfile(sqlite_path):
        raise RuntimeError(f"SQLite file not found: {sqlite_path}")

    # Ensure destination schema exists.
    CafeDatabase(db_url)

    src = sqlite3.connect(sqlite_path)
    src.row_factory = sqlite3.Row
    dst = psycopg.connect(db_url)

    try:
        client_ids = existing_ids(src, "clients") if table_exists_sqlite(src, "clients") else set()
        dish_ids = existing_ids(src, "dishes") if table_exists_sqlite(src, "dishes") else set()
        ingredient_ids = existing_ids(src, "ingredients") if table_exists_sqlite(src, "ingredients") else set()

        with dst.cursor(row_factory=dict_row) as cur:
            cur.execute("TRUNCATE TABLE barcode_events, coffee_visits, breakfast_visits, sales, expenses, recipe_items, clients, dishes, ingredients RESTART IDENTITY CASCADE")

            for table in TABLES_IN_ORDER:
                if not table_exists_sqlite(src, table):
                    continue

                src_cur = src.cursor()
                src_cur.execute(f"SELECT * FROM {table}")
                rows = src_cur.fetchall()
                if not rows:
                    continue

                columns = list(rows[0].keys())
                col_sql = ", ".join(columns)
                ph_sql = ", ".join(["%s"] * len(columns))
                insert_sql = f"INSERT INTO {table} ({col_sql}) VALUES ({ph_sql})"

                data = []
                skipped = 0
                for r in rows:
                    # Skip orphan rows that violate FK in PostgreSQL.
                    if table in {"breakfast_visits", "coffee_visits", "barcode_events"} and r["client_id"] not in client_ids:
                        skipped += 1
                        continue
                    if table == "sales" and r["dish_id"] not in dish_ids:
                        skipped += 1
                        continue
                    if table == "recipe_items":
                        if r["dish_id"] not in dish_ids or r["ingredient_id"] not in ingredient_ids:
                            skipped += 1
                            continue
                    row = []
                    for c in columns:
                        v = r[c]
                        # SQLite stores booleans as 0/1; PostgreSQL expects bool for BOOLEAN columns.
                        if c == "is_free" and isinstance(v, int):
                            v = bool(v)
                        row.append(v)
                    data.append(tuple(row))

                if data:
                    cur.executemany(insert_sql, data)
                if skipped:
                    print(f"{table}: skipped orphan rows = {skipped}")

            # Fix sequences after explicit id inserts.
            for table in TABLES_IN_ORDER:
                cur.execute(
                    f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), COALESCE((SELECT MAX(id) FROM {table}), 1), true)"
                )

        dst.commit()
        print("Migration complete.")
    finally:
        src.close()
        dst.close()


if __name__ == "__main__":
    main()
