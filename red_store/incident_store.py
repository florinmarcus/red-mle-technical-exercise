"""Persist the incident aggregate and its attributable facts and links."""

from __future__ import annotations

import sqlite3

from red_store import model


def insert(
    open_connection: sqlite3.Connection,
    message_id: str,
    extraction: model.Extraction,
) -> tuple[model.Incident, ...]:
    """Insert one message's incident aggregate and return stored incidents.

    Facts have an insert path only. Whether a message link is ``new`` or
    ``update`` is decided from the incident row's existence at write time.
    """

    stored_by_key: dict[model.IncidentKey, model.Incident] = {}
    for extracted_incident in extraction.incidents:
        stored_incident, created = _get_or_create(
            open_connection,
            extracted_incident.key,
        )
        stored_by_key[stored_incident.key] = stored_incident
        open_connection.execute(
            """
            INSERT INTO message_incident_links (
                message_id,
                incident_id,
                relationship_type
            )
            VALUES (?, ?, ?)
            """,
            (
                message_id,
                stored_incident.incident_id,
                "new" if created else "update",
            ),
        )
        if extraction.reporting_org_id is not None:
            open_connection.execute(
                """
                INSERT INTO org_incident_links (org_id, incident_id, role)
                VALUES (?, ?, 'reporting')
                """,
                (
                    extraction.reporting_org_id,
                    stored_incident.incident_id,
                ),
            )

    for fact in extraction.facts:
        stored_incident = stored_by_key[fact.incident]
        open_connection.execute(
            """
            INSERT INTO facts (
                message_id,
                incident_id,
                site_id,
                predicate,
                value,
                source_quote
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                message_id,
                stored_incident.incident_id,
                fact.site_id,
                fact.predicate,
                fact.value,
                fact.source_quote,
            ),
        )

    return tuple(stored_by_key.values())


def _get_or_create(
    open_connection: sqlite3.Connection,
    incident_key: model.IncidentKey,
) -> tuple[model.Incident, bool]:
    row = open_connection.execute(
        """
        SELECT incident_id
        FROM incidents
        WHERE location_id = ? AND type = ?
        """,
        (incident_key.location_id, incident_key.type),
    ).fetchone()
    if row is not None:
        return (
            model.Incident(
                incident_id=int(row[0]),
                location_id=incident_key.location_id,
                type=incident_key.type,
            ),
            False,
        )

    cursor = open_connection.execute(
        "INSERT INTO incidents (location_id, type) VALUES (?, ?)",
        (incident_key.location_id, incident_key.type),
    )
    if cursor.lastrowid is None:
        raise RuntimeError("incident insert did not return a row id")
    return (
        model.Incident(
            incident_id=int(cursor.lastrowid),
            location_id=incident_key.location_id,
            type=incident_key.type,
        ),
        True,
    )
