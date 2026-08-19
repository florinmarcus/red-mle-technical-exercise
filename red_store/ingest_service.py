"""Orchestrate the message-ingestion use case and its transactions."""

from __future__ import annotations

from pathlib import Path
import sqlite3

from red_store import (
    connection,
    incident_extractor,
    incident_store,
    message_parser,
    message_store,
    model,
    processing_issue_store,
    reference_store,
)


def ingest_directory(database: Path, emails_directory: Path) -> model.IngestionResult:
    """Ingest every ``.eml`` file into messages and derived incident rows.

    A file that cannot be read or parsed is skipped and reported on the result
    rather than aborting the run. In the target architecture such a message goes
    to a dead-letter queue and is retried out of band; the store is only ever
    meant to hold mail that parsed, so a failure is deliberately *not* recorded
    as a row here. Locally the command output plus a non-zero exit code stands in
    for that queue.

    Each message is committed in its own transaction, so one bad file costs one
    file rather than the batch. Errors raised while writing a successfully parsed
    message are left to propagate: those indicate a defect in the ingest, not a
    problem with the email.
    """

    email_paths = sorted(emails_directory.glob("*.eml"))
    inserted = 0
    skipped = 0
    failures: list[model.IngestionFailure] = []

    with connection.get_connection(database) as open_connection:
        vocabularies = reference_store.load_vocabularies(open_connection)
        for email_path in email_paths:
            try:
                message = message_parser.parse(email_path.read_bytes())
            except (OSError, ValueError, IndexError, TypeError) as error:
                failures.append(
                    model.IngestionFailure(
                        source_name=email_path.name,
                        reason=f"{type(error).__name__}: {error}",
                    )
                )
                continue

            with open_connection:
                if ingest_message(open_connection, message, vocabularies):
                    inserted += 1
                else:
                    skipped += 1

    return model.IngestionResult(
        processed=len(email_paths),
        inserted=inserted,
        skipped=skipped,
        failures=tuple(failures),
    )


def ingest_message(
    open_connection: sqlite3.Connection,
    message: model.Message,
    vocabularies: model.Vocabularies,
) -> bool:
    """Insert one message and all of its derived rows atomically.

    Returns whether a row was inserted. A message whose ``body_hash`` matches
    an earlier message (but whose ``message_id`` is new) is still inserted,
    with ``duplicate_of_message_id`` pointing at the first match, so its own
    attribution is preserved. Derived extraction is skipped for that resend.
    """

    if message_store.exists(open_connection, message.message_id):
        return False

    duplicate_of_message_id = message_store.first_with_body_hash(
        open_connection, message.body_hash
    )
    message_store.insert(open_connection, message, duplicate_of_message_id)
    if duplicate_of_message_id is not None:
        return True

    extraction = incident_extractor.extract(message, vocabularies)
    incident_store.insert(open_connection, message.message_id, extraction)
    for issue in extraction.issues:
        processing_issue_store.insert(
            open_connection,
            message.message_id,
            issue,
        )
    return True
