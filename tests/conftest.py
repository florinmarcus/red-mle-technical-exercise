"""Shared fixtures, corpus expectations and helpers for store tests."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from red_store import connection, provisioning


EMAILS = Path(__file__).parents[1] / "data" / "emails"


@dataclass(frozen=True)
class ExpectedMessage:
    """Header-derived expectations transcribed by hand from one ``.eml`` file.

    The values are read from the raw source files rather than captured from the
    parser's own output, so a regression in parsing cannot quietly rewrite the
    expectation it is checked against. ``docs/input-data-analysis.md`` records why
    each awkward message is in the corpus.
    """

    message_id: str
    sender_email: str
    sent_at_header: str
    sent_at: str
    subject: str
    original_author_email: str | None = None
    attachment_filenames: tuple[str, ...] = ()


MESSAGES: dict[str, ExpectedMessage] = {
    "001-lrf-sitrep-01.eml": ExpectedMessage(
        message_id="<178568529157.541.16463292412980289561@resilience.gov.uk.example>",
        sender_email="priya.raman@wmlrf.example.gov.uk",
        sent_at_header="Tue, 27 Jan 2026 07:05:00 -0000",
        sent_at="2026-01-27T07:05:00+00:00",
        subject="SITREP 01 - Herefordshire rainfall / River Leadon - 27 Jan 0700",
    ),
    "002-district-freeform.eml": ExpectedMessage(
        message_id="<178568529158.541.5572998488160451884@resilience.gov.uk.example>",
        sender_email="g.hollis@herefordshire.example.gov.uk",
        sent_at_header="Tue, 27 Jan 2026 08:22:00 -0000",
        sent_at="2026-01-27T08:22:00+00:00",
        subject="flooding update - couple of things",
    ),
    # Carries a *quoted* forwarded-message marker, so the original author stays
    # unset and attribution remains with the person replying.
    "003-reply-chain.eml": ExpectedMessage(
        message_id="<178568529158.541.8296096565849768540@resilience.gov.uk.example>",
        sender_email="priya.raman@wmlrf.example.gov.uk",
        sent_at_header="Tue, 27 Jan 2026 11:03:00 -0000",
        sent_at="2026-01-27T11:03:00+00:00",
        subject="RE: SITREP 01 - Herefordshire rainfall / River Leadon - 27 Jan 0700",
    ),
    # The only message with an unquoted forwarded header block.
    "004-forwarded-ea-warning.eml": ExpectedMessage(
        message_id="<178568529158.541.9122937973322827542@resilience.gov.uk.example>",
        sender_email="comms.duty@wmlrf.example.gov.uk",
        sent_at_header="Tue, 27 Jan 2026 13:02:00 -0000",
        sent_at="2026-01-27T13:02:00+00:00",
        subject="FW: Flood Warning issued - River Severn at Upton-upon-Severn",
        original_author_email="no-reply@floodwarning.example.gov.uk",
    ),
    # The only message with a folded From header.
    "005-meeting-invite.eml": ExpectedMessage(
        message_id="<178568529158.541.6811961738316124928@resilience.gov.uk.example>",
        sender_email="wmlrfsecretariat@westmercia.example.police.uk",
        sent_at_header="Tue, 27 Jan 2026 16:40:00 -0000",
        sent_at="2026-01-27T16:40:00+00:00",
        subject="Invitation: Tactical Coordinating Group (TCG) 3 - Wed 28 Jan 09:00",
    ),
    "006-rest-centre-table.eml": ExpectedMessage(
        message_id="<178568529158.541.172459640524515462@resilience.gov.uk.example>",
        sender_email="marcus.ntale@worcestershire.example.gov.uk",
        sent_at_header="Tue, 27 Jan 2026 18:12:00 -0000",
        sent_at="2026-01-27T18:12:00+00:00",
        subject="Rest centre status 27/01 1800",
    ),
    "007-lrf-sitrep-01-resend.eml": ExpectedMessage(
        message_id="<178568529159.541.3416391346970498431@resilience.gov.uk.example>",
        sender_email="priya.raman@wmlrf.example.gov.uk",
        sent_at_header="Tue, 27 Jan 2026 07:48:00 -0000",
        sent_at="2026-01-27T07:48:00+00:00",
        subject="SITREP 01 - Herefordshire rainfall / River Leadon - 27 Jan 0700",
    ),
    "008-highways-reopen.eml": ExpectedMessage(
        message_id="<178568529159.541.1982379432847866748@resilience.gov.uk.example>",
        sender_email="tm@herefordshire.example.gov.uk",
        sent_at_header="Tue, 27 Jan 2026 14:15:00 -0000",
        sent_at="2026-01-27T14:15:00+00:00",
        subject="A417 - road reopened",
    ),
    "009-police-road-status.eml": ExpectedMessage(
        message_id="<178568529159.541.6622238191278810384@resilience.gov.uk.example>",
        sender_email="control@westmercia.example.police.uk",
        sent_at_header="Tue, 27 Jan 2026 15:25:00 -0000",
        sent_at="2026-01-27T15:25:00+00:00",
        subject="Road status Ledbury 1520",
    ),
    "010-welfare-request.eml": ExpectedMessage(
        message_id="<178568529159.541.17303712305818631248@resilience.gov.uk.example>",
        sender_email="asc.duty@worcestershire.example.gov.uk",
        sent_at_header="Tue, 27 Jan 2026 19:05:00 -0000",
        sent_at="2026-01-27T19:05:00+00:00",
        subject="URGENT welfare - power dependent resident, Upton",
    ),
    "011-dno-outage.eml": ExpectedMessage(
        message_id="<178568529159.541.9284810378945894813@resilience.gov.uk.example>",
        sender_email="incident.liaison@dno.example.com",
        sent_at_header="Tue, 27 Jan 2026 20:34:00 -0000",
        sent_at="2026-01-27T20:34:00+00:00",
        subject="Power outage - Upton-upon-Severn and surrounding - update 3",
    ),
    "012-ukhsa-cluster.eml": ExpectedMessage(
        message_id="<178568529159.541.12771813553156785892@resilience.gov.uk.example>",
        sender_email="hpt.westmids@ukhsa.example.gov.uk",
        sent_at_header="Thu, 29 Jan 2026 11:40:00 -0000",
        sent_at="2026-01-29T11:40:00+00:00",
        subject="Possible GI cluster - Ledbury - for awareness",
    ),
    # The only message with a MIME attachment.
    "013-sitrep-attached.eml": ExpectedMessage(
        message_id="<178568529159.541.14086137378701080322@resilience.gov.uk.example>",
        sender_email="priya.raman@wmlrf.example.gov.uk",
        sent_at_header="Wed, 28 Jan 2026 08:15:00 -0000",
        sent_at="2026-01-28T08:15:00+00:00",
        subject="SITREP 04 - attached",
        attachment_filenames=("SITREP-04.txt",),
    ),
    # The only multipart/alternative message.
    "014-html-newsletter-update.eml": ExpectedMessage(
        message_id="<178568529160.541.14509870122064004392@resilience.gov.uk.example>",
        sender_email="recovery@wmlrf.example.gov.uk",
        sent_at_header="Thu, 29 Jan 2026 10:20:00 -0000",
        sent_at="2026-01-29T10:20:00+00:00",
        subject="Recovery Coordinating Group - initial position",
    ),
    # The only message declaring a non-UTF-8 charset (iso-8859-1).
    "015-relative-dates.eml": ExpectedMessage(
        message_id="<178568529160.541.3799177800074561131@resilience.gov.uk.example>",
        sender_email="c.beaumont@malvernhills.example.gov.uk",
        sent_at_header="Wed, 28 Jan 2026 09:48:00 -0000",
        sent_at="2026-01-28T09:48:00+00:00",
        subject="Caravan park - Upton - evacuation last night",
    ),
    "016-as-per-attached.eml": ExpectedMessage(
        message_id="<178568529160.541.12681040469059723620@resilience.gov.uk.example>",
        sender_email="duty@gloucestershire.example.gov.uk",
        sent_at_header="Wed, 28 Jan 2026 12:02:00 -0000",
        sent_at="2026-01-28T12:02:00+00:00",
        subject="FYI",
    ),
}

MESSAGE_COUNT = len(MESSAGES)


@dataclass(frozen=True)
class ExpectedResend:
    """The one corpus pair that differs only in headers and line endings.

    ``normalised_byte_count`` and ``normalised_sha256`` pin the agreed
    normalisation: decode the sole ``text/plain`` part, turn CRLF and CR into
    LF, keep every other character including the final LF, encode as UTF-8.
    """

    resend: str
    duplicates: str
    normalised_byte_count: int
    normalised_sha256: str


RESEND = ExpectedResend(
    resend="007-lrf-sitrep-01-resend.eml",
    duplicates="001-lrf-sitrep-01.eml",
    normalised_byte_count=953,
    normalised_sha256=(
        "4ab4e28bd5f71fca30d51979fc451be88e6edd2297f1610ade19d102a317eed4"
    ),
)


@pytest.fixture
def seeded_database(tmp_path: Path) -> Path:
    """Return a temporary store with its schema and reference data provisioned."""

    database = tmp_path / "red-store.sqlite"
    provisioning.create_schema(database)
    provisioning.seed_reference_data(database)
    return database


def _table_row_counts(database: Path) -> dict[str, int]:
    with connection.get_connection(database) as open_connection:
        table_names = [
            row[0]
            for row in open_connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
                """
            )
        ]
        return {
            table: open_connection.execute(
                f'SELECT COUNT(*) FROM "{table}"'
            ).fetchone()[0]
            for table in table_names
        }
