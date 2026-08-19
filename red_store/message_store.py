"""Persist and query immutable received-message rows."""

from __future__ import annotations

import sqlite3

from red_store import model


def exists(open_connection: sqlite3.Connection, message_id: str) -> bool:
    """Return whether ``message_id`` is already stored."""

    return (
        open_connection.execute(
            "SELECT 1 FROM messages WHERE message_id = ?", (message_id,)
        ).fetchone()
        is not None
    )


def first_with_body_hash(
    open_connection: sqlite3.Connection, body_hash: str
) -> str | None:
    """Return the first stored message with ``body_hash``, if one exists."""

    row = open_connection.execute(
        """
        SELECT message_id
        FROM messages
        WHERE body_hash = ?
        ORDER BY rowid
        LIMIT 1
        """,
        (body_hash,),
    ).fetchone()
    return None if row is None else str(row[0])


def insert(
    open_connection: sqlite3.Connection,
    message: model.Message,
    duplicate_of_message_id: str | None,
) -> None:
    """Insert one message and its optional resend attribution."""

    open_connection.execute(
        """
        INSERT INTO messages (
            message_id,
            sender_email,
            original_author_email,
            sent_at,
            sent_at_header,
            subject,
            body,
            body_hash,
            duplicate_of_message_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            message.message_id,
            message.sender_email,
            message.original_author_email,
            message.sent_at,
            message.sent_at_header,
            message.subject,
            message.body,
            message.body_hash,
            duplicate_of_message_id,
        ),
    )
