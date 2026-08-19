"""Behaviour tests for the public Stage A provisioning operations."""

from __future__ import annotations

from pathlib import Path

from red_store import connection, provisioning


def test_create_schema_runs_on_an_empty_database(tmp_path: Path) -> None:
    """Schema creation works against a database file that does not yet exist.

    This is the first command anyone runs, so it must bootstrap from nothing.
    Querying ``messages`` afterwards proves the statements actually executed:
    the table exists and is empty, rather than the file merely being created.
    """
    database = tmp_path / "red-store.sqlite"

    provisioning.create_schema(database)

    with connection.get_connection(database) as open_connection:
        assert open_connection.execute(
            "SELECT COUNT(*) FROM messages"
        ).fetchone() == (0,)


def test_seed_reference_data_is_idempotent(tmp_path: Path) -> None:
    """Seeding twice leaves reference data exactly as it was after the first run.

    Setup gets re-run during development and after schema changes, so it must
    not duplicate organisations or renumber their identifiers, which ingest
    later refers to. The rows are compared before and after a second seed, and
    asserted non-empty so an unseeded database cannot pass by default.
    """
    database = tmp_path / "red-store.sqlite"
    provisioning.create_schema(database)
    provisioning.seed_reference_data(database)

    with connection.get_connection(database) as open_connection:
        before = open_connection.execute(
            "SELECT * FROM organisations ORDER BY org_id"
        ).fetchall()

    provisioning.seed_reference_data(database)

    with connection.get_connection(database) as open_connection:
        after = open_connection.execute(
            "SELECT * FROM organisations ORDER BY org_id"
        ).fetchall()

    assert before
    assert after == before
