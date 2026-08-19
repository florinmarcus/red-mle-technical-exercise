"""Behaviour tests for attributable message and incident ingestion."""

from __future__ import annotations

from pathlib import Path
from shutil import copyfile, copytree

from red_store import connection, ingest_service, message_parser, model
from tests import conftest


def test_ingest_directory_maps_every_parsed_field_to_its_column(
    seeded_database: Path,
) -> None:
    """Every parsed field lands in the right column for the whole corpus.

    Parsing is covered elsewhere; what matters here is the wiring between the
    parser and the ``messages`` table. Each row is compared against the parser's
    own output plus the corpus expectations, so a transposed or dropped column
    is caught rather than showing up later as quietly wrong data.
    """
    result = ingest_service.ingest_directory(seeded_database, conftest.EMAILS)
    expected_duplicate_of_message_ids = {
        conftest.RESEND.resend: conftest.MESSAGES[
            conftest.RESEND.duplicates
        ].message_id
    }

    assert result == model.IngestionResult(
        processed=conftest.MESSAGE_COUNT,
        inserted=conftest.MESSAGE_COUNT,
        skipped=0,
    )
    with connection.get_connection(seeded_database) as open_connection:
        assert open_connection.execute(
            "SELECT COUNT(*) FROM messages"
        ).fetchone() == (conftest.MESSAGE_COUNT,)
        for filename, expected in conftest.MESSAGES.items():
            parsed = message_parser.parse(
                (conftest.EMAILS / filename).read_bytes()
            )
            assert open_connection.execute(
                """
                SELECT message_id, sender_email, original_author_email, sent_at,
                       sent_at_header, subject, body, body_hash,
                       duplicate_of_message_id
                FROM messages
                WHERE message_id = ?
                """,
                (expected.message_id,),
            ).fetchone() == (
                expected.message_id,
                expected.sender_email,
                expected.original_author_email,
                parsed.sent_at,
                parsed.sent_at_header,
                expected.subject,
                parsed.body,
                parsed.body_hash,
                expected_duplicate_of_message_ids.get(filename),
            )


def test_ingest_directory_orders_messages_chronologically_by_sent_at(
    seeded_database: Path,
) -> None:
    """``ORDER BY sent_at`` must reflect true send order, not lexical Date order.

    012 and 014 were sent on 29 Jan; 013, 015 and 016 were sent a day earlier
    on 28 Jan. Sorting the raw Date header as text would put every "Thu, 29
    Jan" row before every "Wed, 28 Jan" row, because "Thu" sorts lexically
    before "Wed". The expected order below is fixed independently, from the
    corpus's actual Date headers, so this fails against that lexical-text
    ordering rather than merely re-checking whatever ``sent_at`` happens to
    contain.
    """
    ingest_service.ingest_directory(seeded_database, conftest.EMAILS)
    expected_filenames = [
        "001-lrf-sitrep-01.eml",
        "007-lrf-sitrep-01-resend.eml",
        "002-district-freeform.eml",
        "003-reply-chain.eml",
        "004-forwarded-ea-warning.eml",
        "008-highways-reopen.eml",
        "009-police-road-status.eml",
        "005-meeting-invite.eml",
        "006-rest-centre-table.eml",
        "010-welfare-request.eml",
        "011-dno-outage.eml",
        "013-sitrep-attached.eml",
        "015-relative-dates.eml",
        "016-as-per-attached.eml",
        "014-html-newsletter-update.eml",
        "012-ukhsa-cluster.eml",
    ]
    expected_message_ids = [
        conftest.MESSAGES[filename].message_id
        for filename in expected_filenames
    ]

    with connection.get_connection(seeded_database) as open_connection:
        ordered_message_ids = [
            row[0]
            for row in open_connection.execute(
                "SELECT message_id FROM messages ORDER BY sent_at"
            ).fetchall()
        ]

    assert ordered_message_ids == expected_message_ids


def test_ingest_directory_is_an_exact_no_op_for_existing_message_ids(
    seeded_database: Path,
) -> None:
    """Re-running ingest over the same corpus leaves the table untouched.

    Operators will re-run the command after adding a few files, so ingest has to
    be safe to repeat. Rows already present are skipped rather than updated: the
    full table is compared before and after, and the counts must report every
    message as skipped and none inserted.
    """
    ingest_service.ingest_directory(seeded_database, conftest.EMAILS)

    before_counts = conftest._table_row_counts(seeded_database)
    with connection.get_connection(seeded_database) as open_connection:
        before = open_connection.execute(
            "SELECT * FROM messages ORDER BY message_id"
        ).fetchall()

    second_result = ingest_service.ingest_directory(
        seeded_database, conftest.EMAILS
    )

    with connection.get_connection(seeded_database) as open_connection:
        after = open_connection.execute(
            "SELECT * FROM messages ORDER BY message_id"
        ).fetchall()
    after_counts = conftest._table_row_counts(seeded_database)
    assert second_result == model.IngestionResult(
        processed=conftest.MESSAGE_COUNT,
        inserted=0,
        skipped=conftest.MESSAGE_COUNT,
    )
    assert after == before
    assert after_counts == before_counts


def test_ingest_directory_populates_the_stage_2_tables(
    seeded_database: Path,
) -> None:
    """Ingest writes messages and the in-scope derived incident aggregate."""
    before = conftest._table_row_counts(seeded_database)

    ingest_service.ingest_directory(seeded_database, conftest.EMAILS)

    after = conftest._table_row_counts(seeded_database)
    assert before["messages"] == 0
    assert after["messages"] == conftest.MESSAGE_COUNT
    for table in (
        "incidents",
        "facts",
        "message_incident_links",
        "org_incident_links",
        "processing_issues",
    ):
        assert before[table] == 0
        assert after[table] > 0
    for table in (
        "fact_predicates",
        "location_aliases",
        "locations",
        "organisation_aliases",
        "organisations",
        "site_aliases",
        "sites",
    ):
        assert after[table] == before[table]


def test_ingest_directory_stores_the_unambiguous_worked_example_facts(
    seeded_database: Path,
) -> None:
    """Unambiguous in-scope examples retain their verbatim source line."""

    ingest_service.ingest_directory(seeded_database, conftest.EMAILS)
    expected = {
        (
            conftest.MESSAGES["001-lrf-sitrep-01.eml"].message_id,
            "properties_flooded",
            12,
            "- 12 residential properties confirmed flooded, Bye Street and "
            "Woodleigh Road, Ledbury",
        ),
        (
            conftest.MESSAGES["001-lrf-sitrep-01.eml"].message_id,
            "evacuees",
            40,
            "- Approx 40 residents evacuated",
        ),
        (
            conftest.MESSAGES["001-lrf-sitrep-01.eml"].message_id,
            "rest_centre_capacity",
            80,
            "- Rest centre opened 0600 at Ledbury Community Hall, HR8 2AA, "
            "capacity 80",
        ),
        (
            conftest.MESSAGES["011-dno-outage.eml"].message_id,
            "customers_off_supply",
            1847,
            "precaution due to floodwater ingress. 1,847 customers currently "
            "off supply",
        ),
    }

    with connection.get_connection(seeded_database) as open_connection:
        stored = set(
            open_connection.execute(
                """
                SELECT message_id, predicate, value, source_quote
                FROM facts
                """
            ).fetchall()
        )

    assert expected <= stored


def test_ingest_directory_retains_unanchored_measurements_as_issues(
    seeded_database: Path,
) -> None:
    """Ambiguous prose and table rows remain visible without inferred facts."""

    ingest_service.ingest_directory(seeded_database, conftest.EMAILS)
    message_ids = {
        filename: conftest.MESSAGES[filename].message_id
        for filename in (
            "003-reply-chain.eml",
            "006-rest-centre-table.eml",
            "014-html-newsletter-update.eml",
        )
    }

    with connection.get_connection(seeded_database) as open_connection:
        no_location_issues = set(
            open_connection.execute(
                """
                SELECT message_id, detail
                FROM processing_issues
                WHERE kind = 'no_location_matched'
                  AND message_id IN (?, ?)
                """,
                (
                    message_ids["003-reply-chain.eml"],
                    message_ids["014-html-newsletter-update.eml"],
                ),
            ).fetchall()
        )
        tracker_issues = open_connection.execute(
            """
            SELECT detail
            FROM processing_issues
            WHERE message_id = ?
              AND kind = 'number_no_matching_predicate'
              AND detail LIKE '%|%'
            ORDER BY issue_id
            """,
            (message_ids["006-rest-centre-table.eml"],),
        ).fetchall()
        inferred_facts = open_connection.execute(
            """
            SELECT message_id, predicate, value
            FROM facts
            WHERE message_id IN (?, ?, ?)
            """,
            (
                message_ids["003-reply-chain.eml"],
                message_ids["006-rest-centre-table.eml"],
                message_ids["014-html-newsletter-update.eml"],
            ),
        ).fetchall()

    assert no_location_issues == {
        (
            message_ids["003-reply-chain.eml"],
            "Evacuee numbers have risen to 65. Ledbury Community Hall reached "
            "capacity at",
        ),
        (
            message_ids["003-reply-chain.eml"],
            "Confirmed property flooding figure is now 19, which aligns with "
            "what",
        ),
        (
            message_ids["014-html-newsletter-update.eml"],
            "- 19 properties in Ledbury requiring recovery support, 7 in "
            "Upton-upon-Severn",
        ),
    }
    assert tracker_issues == [
        (
            "St Michael's Primary School     | Ledbury             | Open   | "
            "65        | 150",
        ),
        (
            "Ledbury Community Hall          | Ledbury             | Closed | "
            "0         | 80",
        ),
        (
            "Upton Memorial Hall             | Upton-upon-Severn   | Open   | "
            "12        | 90",
        ),
        (
            "Pershore Leisure Centre         | Pershore            | Standby| "
            "0         | 200",
        ),
        (
            "Malvern Cube                    | Great Malvern       | Standby| "
            "0         | 120",
        ),
    ]
    assert inferred_facts == []


def test_every_linked_incident_has_a_reporting_organisation(
    seeded_database: Path,
) -> None:
    """Every incident graph reachable from a message names a reporting body."""

    ingest_service.ingest_directory(seeded_database, conftest.EMAILS)

    with connection.get_connection(seeded_database) as open_connection:
        incidents_without_reporter = open_connection.execute(
            """
            SELECT message_incident_links.incident_id
            FROM message_incident_links
            LEFT JOIN org_incident_links
              ON org_incident_links.incident_id =
                 message_incident_links.incident_id
             AND org_incident_links.role = 'reporting'
            GROUP BY message_incident_links.incident_id
            HAVING COUNT(org_incident_links.org_id) = 0
            """
        ).fetchall()

    assert incidents_without_reporter == []


def test_ingest_directory_skips_an_unparseable_file_and_reports_it(
    seeded_database: Path,
    tmp_path: Path,
) -> None:
    """A file that will not parse costs that file, not the whole run.

    A directory is built with a good email followed by a body-less binary one.
    The good message is committed and the bad one is reported on the result, so
    an operator gets a usable store plus a named gap. Failed messages are
    deliberately absent from the store: they belong on a dead-letter queue, and
    inventing rows for them would put fabricated senders and bodies into the
    table used for attribution.
    """
    emails_directory = tmp_path / "partial-emails"
    emails_directory.mkdir()
    copyfile(
        conftest.EMAILS / "001-lrf-sitrep-01.eml",
        emails_directory / "001-valid.eml",
    )
    (emails_directory / "002-invalid.eml").write_bytes(_BODYLESS_MESSAGE)

    result = ingest_service.ingest_directory(seeded_database, emails_directory)

    assert result.processed == 2
    assert result.inserted == 1
    assert result.skipped == 0
    assert result.failed == 1
    assert result.failures[0].source_name == "002-invalid.eml"
    assert "no text/plain or text/html body" in result.failures[0].reason
    with connection.get_connection(seeded_database) as open_connection:
        assert open_connection.execute(
            "SELECT message_id FROM messages"
        ).fetchall() == [
            (conftest.MESSAGES["001-lrf-sitrep-01.eml"].message_id,)
        ]


def test_ingest_directory_reports_the_same_failure_on_every_run(
    seeded_database: Path,
    tmp_path: Path,
) -> None:
    """Re-running does not quietly forget a file that failed last time.

    Skipping a bad file must not look like success on the second run, otherwise
    a gap disappears the moment anyone re-runs the command. The failure is
    reported again, and the message that did parse is still counted as skipped
    rather than inserted twice.
    """
    emails_directory = tmp_path / "repeat-emails"
    emails_directory.mkdir()
    copyfile(
        conftest.EMAILS / "001-lrf-sitrep-01.eml",
        emails_directory / "001-valid.eml",
    )
    (emails_directory / "002-invalid.eml").write_bytes(_BODYLESS_MESSAGE)
    ingest_service.ingest_directory(seeded_database, emails_directory)

    second_result = ingest_service.ingest_directory(
        seeded_database, emails_directory
    )

    assert second_result.inserted == 0
    assert second_result.skipped == 1
    assert second_result.failed == 1


def test_ingest_directory_ignores_non_eml_files(
    seeded_database: Path,
    tmp_path: Path,
) -> None:
    """Only ``.eml`` files are ingested; other files in the folder are ignored.

    Real mail exports pick up stray notes, READMEs and editor artefacts. Given
    the corpus plus a loose text file, the processed count stays at the corpus
    size instead of failing on something that was never an email.
    """
    emails_directory = tmp_path / "corpus-copy"
    copytree(conftest.EMAILS, emails_directory)
    (emails_directory / "operator-notes.txt").write_text(
        "This is not an email.",
        encoding="utf-8",
    )

    result = ingest_service.ingest_directory(seeded_database, emails_directory)

    assert result.processed == conftest.MESSAGE_COUNT


def test_ingest_directory_links_a_duplicate_to_the_first_matching_message(
    seeded_database: Path,
    tmp_path: Path,
) -> None:
    """A duplicate body points back at whichever message was ingested first.

    "First" means ingest order, not alphabetical order by identifier. The two
    synthesised messages share a body but have message IDs that sort the other
    way round, so a link built from sorted IDs would point the wrong way and the
    original would be marked as the copy.
    """
    emails_directory = tmp_path / "duplicate-emails"
    emails_directory.mkdir()
    first_message_id = "<z-first@example.gov.uk>"
    second_message_id = "<a-second@example.gov.uk>"
    body = "Identical incident update.\r\n"
    (emails_directory / "001-first.eml").write_bytes(
        _plain_text_message(first_message_id, body)
    )
    (emails_directory / "002-second.eml").write_bytes(
        _plain_text_message(second_message_id, body)
    )

    ingest_service.ingest_directory(seeded_database, emails_directory)

    with connection.get_connection(seeded_database) as open_connection:
        stored = open_connection.execute(
            """
            SELECT message_id, duplicate_of_message_id
            FROM messages
            ORDER BY rowid
            """
        ).fetchall()
    assert stored == [
        (first_message_id, None),
        (second_message_id, first_message_id),
    ]


def _plain_text_message(message_id: str, body: str) -> bytes:
    """Build a minimal valid plain-text email with the given ID and body."""
    return (
        "From: Reporter <reporter@example.gov.uk>\r\n"
        "To: RED Duty Desk <red.duty@example.gov.uk>\r\n"
        "Subject: Duplicate ordering\r\n"
        "Date: Fri, 30 Jan 2026 09:00:00 -0000\r\n"
        f"Message-ID: {message_id}\r\n"
        "Content-Type: text/plain; charset=utf-8\r\n"
        "\r\n"
        f"{body}"
    ).encode("utf-8")


# A well-formed envelope carrying a binary payload: the headers parse, so the
# file reaches the body selector, which then has neither a plain nor an HTML
# part to choose. This is the realistic shape of an unparseable message.
_BODYLESS_MESSAGE = (
    b"From: Reporter <reporter@example.gov.uk>\r\n"
    b"To: RED Duty Desk <red.duty@example.gov.uk>\r\n"
    b"Subject: Non-text update\r\n"
    b"Date: Fri, 30 Jan 2026 09:00:00 -0000\r\n"
    b"Message-ID: <non-text@example.gov.uk>\r\n"
    b"MIME-Version: 1.0\r\n"
    b"Content-Type: application/octet-stream\r\n"
    b"\r\n"
    b"\x00\x01\x02\r\n"
)
