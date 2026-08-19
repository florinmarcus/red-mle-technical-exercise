"""Bring a Stage A incident store into existence in a known state.

Setup-time only: these operations run once, before ingestion, from ``red
schema`` or ``red init``. Nothing here is called on the runtime path — this
module depends on :mod:`red_store.connection`, never the reverse.
"""

from __future__ import annotations

from pathlib import Path
import sqlite3

from . import connection


_SQL_DIRECTORY = Path(__file__).parent / "sql"


def create_schema(database: Path) -> None:
    """Create the empty Stage A tables in ``database``.

    The schema SQL script owns its transaction boundaries.
    """

    with connection.get_connection(database) as open_connection:
        open_connection.executescript(_read_sql("schema.sql"))


def seed_reference_data(database: Path) -> None:
    """Seed the owned reference tables in ``database``.

    Repeated calls do not change existing reference data. The seed SQL script
    owns its transaction boundaries.
    """

    with connection.get_connection(database) as open_connection:
        _execute_sql_script(open_connection, _read_sql("seed.sql"))


def _read_sql(filename: str) -> str:
    """Return the text of an SQL file stored beside this package."""

    return (_SQL_DIRECTORY / filename).read_text(encoding="utf-8")


def _execute_sql_script(open_connection: sqlite3.Connection, sql: str) -> None:
    """Execute complete statements without changing the caller's transaction."""

    pending_lines: list[str] = []
    for line in sql.splitlines(keepends=True):
        pending_lines.append(line)
        statement = "".join(pending_lines)
        if sqlite3.complete_statement(statement):
            open_connection.execute(statement)
            pending_lines.clear()

    if "".join(pending_lines).strip():
        raise ValueError("SQL resource ended with an incomplete statement")
