"""Persist schema-backed processing issues for parsed messages."""

from __future__ import annotations

import sqlite3

from red_store import model


def insert(
    open_connection: sqlite3.Connection,
    message_id: str,
    issue: model.ProcessingIssue,
) -> model.ProcessingIssue:
    """Insert and return one interpretation gap without transforming it."""

    open_connection.execute(
        """
        INSERT INTO processing_issues (message_id, kind, detail)
        VALUES (?, ?, ?)
        """,
        (message_id, issue.kind, issue.detail),
    )
    return issue
