"""Runtime SQLite connections to the incident store.

Every caller that touches the store — provisioning, ingestion, future readers —
opens its connection here, so the pragmas that make the schema's constraints
real are applied in exactly one place.
"""

from __future__ import annotations

from collections.abc import Generator
import contextlib
from pathlib import Path
import sqlite3


@contextlib.contextmanager
def get_connection(database: Path) -> Generator[sqlite3.Connection, None, None]:
    """Yield a SQLite connection with integrity checks enabled.

    SQLite disables foreign-key enforcement per connection by default, so a
    connection opened without this pragma would accept rows the schema declares
    invalid. The connection is closed when the block exits, including on error.
    """

    connection = sqlite3.connect(database)
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
    finally:
        connection.close()
