"""Idempotently repair legacy local SQLite databases created via create_all.

Production PostgreSQL databases must use Alembic normally. This helper exists
only for the developer SQLite fallback, where historical databases may predate
the Alembic version table.
"""

import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).resolve().parent.parent / "ovulite_local.db"
ORG_TABLES = [
    "users", "donors", "sires", "recipients", "technicians", "protocols",
    "embryos", "et_transfers", "embryo_images", "protocol_logs",
    "predictions", "anomalies",
]


def columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in connection.execute(f'PRAGMA table_info("{table}")')}


def main() -> None:
    connection = sqlite3.connect(DB_PATH)
    try:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "organizations" not in tables:
            connection.execute("""CREATE TABLE organizations (
                organization_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(200) NOT NULL UNIQUE,
                slug VARCHAR(120) NOT NULL UNIQUE,
                organization_type VARCHAR(80), country VARCHAR(80),
                time_zone VARCHAR(80), primary_species VARCHAR(80),
                active BOOLEAN DEFAULT 1, created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""")
        connection.execute("""INSERT OR IGNORE INTO organizations
            (organization_id, name, slug, organization_type, time_zone, primary_species)
            VALUES (1, 'Default Organization', 'default', 'Farm', 'Asia/Karachi', 'Bovine')""")

        for table in ORG_TABLES:
            if table not in tables:
                continue
            if "organization_id" not in columns(connection, table):
                connection.execute(f'ALTER TABLE "{table}" ADD COLUMN organization_id INTEGER')
            connection.execute(f'UPDATE "{table}" SET organization_id = 1 WHERE organization_id IS NULL')
            connection.execute(f'CREATE INDEX IF NOT EXISTS ix_{table}_organization_id ON "{table}" (organization_id)')

        prediction_fields = {
            "feature_snapshot": "JSON", "feature_schema_version": "VARCHAR(50)",
            "request_id": "VARCHAR(50)", "uncertainty_level": "VARCHAR(20)",
            "is_ood": "BOOLEAN NOT NULL DEFAULT 0", "ood_reasons": "JSON",
            "similar_cases": "JSON", "plain_language_summary": "TEXT",
            "selected_for_case": "BOOLEAN NOT NULL DEFAULT 0",
            "actual_outcome": "VARCHAR(20)", "actual_outcome_recorded_at": "DATETIME",
        }
        existing = columns(connection, "predictions")
        for name, sql_type in prediction_fields.items():
            if name not in existing:
                connection.execute(f'ALTER TABLE predictions ADD COLUMN "{name}" {sql_type}')
        connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_predictions_request_id ON predictions (request_id)")
        connection.commit()
        print(f"Repaired local SQLite schema: {DB_PATH}")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
