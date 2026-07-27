"""Simple CLI for exporting/importing key catalog tables as JSON (for backup or bulk editing).

`import` REPLACES the contents of each table present in the JSON file - it is destructive by
design (this is meant for restoring a backup or bulk-loading a prepared catalog, not for merging).
Back up %APPDATA%/LapLIS-Python (or ~/.config/LapLIS-Python) before running it.
"""
import argparse
import json

from app.db import get_connection

# Only these tables may be exported/imported - table names are never taken from the JSON file
# itself, since interpolating an arbitrary string into SQL as a table name is a SQL-injection risk.
ALLOWED_TABLES = ["roles", "role_permissions", "users", "departments", "tests", "price_list_items"]


def export_json(path: str) -> None:
    conn = get_connection()
    try:
        data = {}
        for t in ALLOWED_TABLES:
            rows = [dict(r) for r in conn.execute(f"SELECT * FROM {t}").fetchall()]
            data[t] = rows
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Exported {', '.join(ALLOWED_TABLES)} to {path}")
    finally:
        conn.close()


def import_json(path: str, force: bool) -> None:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    unknown = [t for t in data if t not in ALLOWED_TABLES]
    if unknown:
        raise SystemExit(f"Refusing to import unknown table(s): {', '.join(unknown)}")

    if not force:
        answer = input(
            f"This will DELETE and replace all rows in: {', '.join(t for t in data if data[t])}\n"
            "Back up your data directory first. Type 'yes' to continue: "
        )
        if answer.strip().lower() != "yes":
            print("Aborted.")
            return

    conn = get_connection()
    try:
        # Deferred FK enforcement means row order within the transaction doesn't matter, so a
        # table can be deleted/reinserted even while another still-unprocessed table references it.
        conn.execute("PRAGMA foreign_keys = OFF")
        for t in ALLOWED_TABLES:
            rows = data.get(t)
            if not rows:
                continue
            cols = list(rows[0].keys())
            placeholders = ",".join("?" for _ in cols)
            conn.execute(f"DELETE FROM {t}")
            for r in rows:
                conn.execute(f"INSERT INTO {t} ({','.join(cols)}) VALUES ({placeholders})",
                             tuple(r[col] for col in cols))
        conn.commit()
        print(f"Imported data from {path}")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.close()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd")
    e = sub.add_parser("export", help="Dump catalog tables to a JSON file")
    e.add_argument("path")
    i = sub.add_parser("import", help="Replace catalog tables from a JSON file (destructive)")
    i.add_argument("path")
    i.add_argument("--force", action="store_true", help="Skip the confirmation prompt")

    args = p.parse_args()
    if args.cmd == "export":
        export_json(args.path)
    elif args.cmd == "import":
        import_json(args.path, args.force)
    else:
        p.print_help()


if __name__ == "__main__":
    main()
