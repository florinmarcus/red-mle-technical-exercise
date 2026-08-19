"""Behaviour tests for parsing Stage 1 message records."""

from __future__ import annotations

import pytest

from red_store import message_parser, model
from tests import conftest


def test_parser_returns_the_standard_message_record() -> None:
    """Pin every field of the record for a plain, single-part SITREP.

    This is the baseline shape every downstream stage relies on: identity
    (``message_id``), provenance (``sender_email``), ordering (``sent_at``),
    and the normalised body plus its hash used for duplicate detection. A
    straightforward email is asserted end to end so the later tests can each
    focus on one awkward variation.
    """
    parsed = message_parser.parse(
        (conftest.EMAILS / "001-lrf-sitrep-01.eml").read_bytes()
    )

    assert isinstance(parsed, model.Message)
    assert parsed.message_id == (
        "<178568529157.541.16463292412980289561@resilience.gov.uk.example>"
    )
    assert parsed.sender_display_name == "Priya Raman"
    assert parsed.sender_email == "priya.raman@wmlrf.example.gov.uk"
    assert parsed.original_author_email is None
    assert parsed.sent_at_header == "Tue, 27 Jan 2026 07:05:00 -0000"
    assert parsed.sent_at == "2026-01-27T07:05:00+00:00"
    assert parsed.subject == (
        "SITREP 01 - Herefordshire rainfall / River Leadon - 27 Jan 0700"
    )
    assert parsed.body.startswith("SITREP 01\nReporting body:")
    assert parsed.body_hash == (
        "4ab4e28bd5f71fca30d51979fc451be88e6edd2297f1610ade19d102a317eed4"
    )
    assert parsed.attachment_filenames == ()


def test_parser_retains_a_folded_from_display_name() -> None:
    """A folded From header keeps the name needed for organisation matching."""

    parsed = message_parser.parse(
        (conftest.EMAILS / "005-meeting-invite.eml").read_bytes()
    )

    assert parsed.sender_display_name == "West Mercia LRF Secretariat"
    assert parsed.sender_email == (
        "wmlrfsecretariat@westmercia.example.police.uk"
    )


def test_parser_credits_the_author_of_an_unquoted_forward() -> None:
    """A forwarded warning must be attributed to whoever originally wrote it.

    The ``From:`` header only names the person who pressed forward. The real
    source sits in the unquoted ``-----Original Message-----`` block, so it is
    surfaced separately as ``original_author_email`` rather than losing the
    provenance of the warning.
    """
    filename = "004-forwarded-ea-warning.eml"
    parsed = message_parser.parse((conftest.EMAILS / filename).read_bytes())

    assert "\n-----Original Message-----\n" in parsed.body
    assert parsed.sender_email == "comms.duty@wmlrf.example.gov.uk"
    assert parsed.original_author_email == "no-reply@floodwarning.example.gov.uk"


def test_parser_does_not_treat_quoted_reply_history_as_a_forward() -> None:
    """Quoted (``>`` prefixed) history is conversation, not a forward.

    A reply chain carries the same ``-----Original Message-----`` marker as a
    forward, but indented as a quote. Treating it as a forward would
    misattribute the message to an earlier participant, so quoting is the
    signal that distinguishes the two and ``original_author_email`` stays unset.
    """
    filename = "003-reply-chain.eml"
    parsed = message_parser.parse((conftest.EMAILS / filename).read_bytes())

    assert "> -----Original Message-----" in parsed.body
    assert "\n-----Original Message-----\n" not in parsed.body
    assert parsed.sender_email == "priya.raman@wmlrf.example.gov.uk"
    assert parsed.original_author_email is None


def test_parser_does_not_take_an_unrelated_later_from_line_as_forward_author() -> None:
    """Only a ``From:`` inside the forwarded header block names an author.

    Guards against a naive "first ``From:`` after the marker" search. Here the
    forwarded header block has no author and a plain sentence starting with
    ``From:`` appears further down the body; attribution must fail closed rather
    than invent an author. Synthesised inline because the corpus has no such
    message.
    """
    raw_message = (
        b"From: Reporter <reporter@example.gov.uk>\r\n"
        b"To: RED Duty Desk <red.duty@example.gov.uk>\r\n"
        b"Subject: Marker without forwarded headers\r\n"
        b"Date: Fri, 30 Jan 2026 09:00:00 -0000\r\n"
        b"Message-ID: <marker-only@example.gov.uk>\r\n"
        b"Content-Type: text/plain; charset=utf-8\r\n"
        b"\r\n"
        b"-----Original Message-----\r\n"
        b"Subject: Header block without an author\r\n"
        b"\r\n"
        b"Body note\r\n"
        b"From: this is ordinary body text\r\n"
    )

    parsed = message_parser.parse(raw_message)

    assert parsed.original_author_email is None


def test_parser_captures_attachment_filenames_without_using_attachment_text() -> None:
    """Attachments are recorded by name only; their contents stay out of the body.

    Stage 1 records what was attached so later stages can decide whether to
    extract it. Folding attachment text into ``body`` would corrupt the body
    hash and blur the line between what was written in the email and what was
    sent alongside it, so a fact that appears only in the attachment is asserted
    absent.
    """
    filename = "013-sitrep-attached.eml"

    parsed = message_parser.parse((conftest.EMAILS / filename).read_bytes())

    assert parsed.attachment_filenames == ("SITREP-04.txt",)
    assert parsed.body == (
        "SITREP 04 attached as agreed. Nothing dramatically new but the Upton picture\n"
        "has firmed up. Shout if the format is a problem.\n\n"
        "Priya\n"
    )
    assert "19 properties flooded" not in parsed.body


def test_parser_prefers_one_plain_representation_of_multipart_alternative() -> None:
    """``multipart/alternative`` yields the plain text part, exactly once.

    The HTML and plain parts of a newsletter say the same thing. Taking both
    would duplicate the content and destabilise the body hash, so the plain part
    is preferred and no markup is allowed to leak through.
    """
    filename = "014-html-newsletter-update.eml"

    parsed = message_parser.parse((conftest.EMAILS / filename).read_bytes())

    assert parsed.body == (
        "Recovery Coordinating Group stood up 29/01 at 1000, chaired by Herefordshire\n"
        "Council. Response phase formally closed for the Leadon incident at 0900 29/01.\n\n"
        "Initial recovery position:\n"
        "- 19 properties in Ledbury requiring recovery support, 7 in Upton-upon-Severn\n"
        "- Flood Recovery Framework activation requested via MHCLG\n"
        "- Community Recovery Grant expected to be the main route for households\n"
        "- Two businesses on Bye Street report uninsured losses\n"
        "- Bromyard industrial estate reopened 29/01\n\n"
        "Next RCG 05/02 at 1000.\n"
    )
    assert "<html>" not in parsed.body


def test_parser_strips_html_when_no_plain_representation_exists() -> None:
    """HTML-only mail degrades to readable text rather than being dropped.

    Tags are removed and entities such as ``&amp;`` are decoded, so the body is
    the words a reader would have seen. Synthesised inline: the corpus only has
    HTML alongside a plain alternative, and this covers the fallback branch.
    """
    raw_message = (
        b"From: Reporter <reporter@example.gov.uk>\r\n"
        b"To: RED Duty Desk <red.duty@example.gov.uk>\r\n"
        b"Subject: HTML-only update\r\n"
        b"Date: Fri, 30 Jan 2026 09:00:00 -0000\r\n"
        b"Message-ID: <html-only@example.gov.uk>\r\n"
        b"MIME-Version: 1.0\r\n"
        b"Content-Type: text/html; charset=utf-8\r\n"
        b"\r\n"
        b"<html><body><h1>Flood warning</h1>"
        b"<p>Use caution &amp; call.</p></body></html>\r\n"
    )

    parsed = message_parser.parse(raw_message)

    assert parsed.body == "Flood warning\nUse caution & call.\n"


def test_parser_honours_the_declared_non_utf8_charset() -> None:
    """Decoding follows the charset the message declares, not an assumed UTF-8.

    Accented personal names are the visible symptom: guessing the encoding turns
    them into mojibake, which would corrupt both the stored body and any later
    name matching.
    """
    parsed = message_parser.parse(
        (conftest.EMAILS / "015-relative-dates.eml").read_bytes()
    )

    assert "Mr Léon Chaumont" in parsed.body
    assert "Chloé Beaumont" in parsed.body


def test_resend_normalisation_preserves_exact_body_bytes_and_hash() -> None:
    """A resend of the same SITREP hashes identically to the original.

    This is the mechanism duplicate detection depends on: the two files differ
    in headers and line endings, yet normalisation must produce byte-identical
    bodies. Byte count and digest are pinned against the corpus contract so a
    change in normalisation cannot silently shift the hash.
    """
    original = message_parser.parse(
        (conftest.EMAILS / conftest.RESEND.duplicates).read_bytes()
    )
    resend = message_parser.parse(
        (conftest.EMAILS / conftest.RESEND.resend).read_bytes()
    )

    assert original.body == resend.body
    assert (
        len(original.body.encode("utf-8"))
        == conftest.RESEND.normalised_byte_count
    )
    assert (
        message_parser.hash_body(original.body)
        == conftest.RESEND.normalised_sha256
    )


def test_body_normalisation_changes_only_line_endings() -> None:
    """Normalisation is deliberately narrow: CRLF and CR become LF, nothing else.

    Trailing spaces are kept. Stripping whitespace or collapsing blank lines
    would make the body hash less faithful to what was actually sent, so the
    transformation is confined to line endings, which vary purely by mail client.
    """
    assert message_parser.normalise_body("first  \r\nsecond\rthird\n") == (
        "first  \nsecond\nthird\n"
    )


def test_parser_treats_an_unknown_offset_date_header_as_utc_without_local_conversion() -> None:
    """A ``-0000`` Date header means "offset unknown", not "this machine's zone".

    ``email.utils.parsedate_to_datetime`` returns a naive ``datetime`` for
    ``-0000``. Converting a naive datetime with ``astimezone`` would silently
    assume the machine's local timezone, making ingestion results
    machine-dependent, so ``-0000`` is instead attached to UTC directly. A
    header with an explicit ``+0100`` offset is parsed alongside it, at the
    same clock time, so the two paths are distinguished rather than
    accidentally producing the same result.
    """
    unknown_offset = message_parser.parse(
        b"From: Reporter <reporter@example.gov.uk>\r\n"
        b"To: RED Duty Desk <red.duty@example.gov.uk>\r\n"
        b"Subject: Unknown offset date\r\n"
        b"Date: Fri, 30 Jan 2026 09:00:00 -0000\r\n"
        b"Message-ID: <unknown-offset@example.gov.uk>\r\n"
        b"Content-Type: text/plain; charset=utf-8\r\n"
        b"\r\n"
        b"Body text.\r\n"
    )
    explicit_offset = message_parser.parse(
        b"From: Reporter <reporter@example.gov.uk>\r\n"
        b"To: RED Duty Desk <red.duty@example.gov.uk>\r\n"
        b"Subject: Explicit offset date\r\n"
        b"Date: Fri, 30 Jan 2026 09:00:00 +0100\r\n"
        b"Message-ID: <explicit-offset@example.gov.uk>\r\n"
        b"Content-Type: text/plain; charset=utf-8\r\n"
        b"\r\n"
        b"Body text.\r\n"
    )

    assert unknown_offset.sent_at == "2026-01-30T09:00:00+00:00"
    assert explicit_offset.sent_at == "2026-01-30T08:00:00+00:00"


def test_parser_rejects_a_missing_date_header() -> None:
    """No Date header means no orderable timestamp, so ingestion fails loudly.

    A silent ``None`` written into the ``NOT NULL sent_at`` column would
    surface far from its cause; failing here, like the missing-body case,
    keeps the diagnosis local to the message that caused it.
    """
    raw_message = (
        b"From: Reporter <reporter@example.gov.uk>\r\n"
        b"To: RED Duty Desk <red.duty@example.gov.uk>\r\n"
        b"Subject: No date header\r\n"
        b"Message-ID: <no-date@example.gov.uk>\r\n"
        b"Content-Type: text/plain; charset=utf-8\r\n"
        b"\r\n"
        b"Body text.\r\n"
    )

    with pytest.raises(ValueError, match="Date header"):
        message_parser.parse(raw_message)


def test_parser_rejects_an_unparseable_date_header() -> None:
    """A malformed Date header is treated the same as a missing one: fail loudly."""
    raw_message = (
        b"From: Reporter <reporter@example.gov.uk>\r\n"
        b"To: RED Duty Desk <red.duty@example.gov.uk>\r\n"
        b"Subject: Bad date header\r\n"
        b"Date: not a date\r\n"
        b"Message-ID: <bad-date@example.gov.uk>\r\n"
        b"Content-Type: text/plain; charset=utf-8\r\n"
        b"\r\n"
        b"Body text.\r\n"
    )

    with pytest.raises(ValueError, match="Date header"):
        message_parser.parse(raw_message)


@pytest.mark.parametrize(("filename", "expected"), conftest.MESSAGES.items())
def test_parser_matches_every_corpus_message_expectation(
    filename: str, expected: conftest.ExpectedMessage
) -> None:
    """Sweep the whole corpus against the per-message expectations in conftest.

    The tests above explain individual behaviours; this one is the safety net,
    checking the header-derived fields of every fixture so a fix aimed at one
    awkward email cannot quietly regress the other fifteen. Body text is
    excluded here and covered by the focused tests.
    """
    parsed = message_parser.parse((conftest.EMAILS / filename).read_bytes())

    assert parsed.message_id == expected.message_id
    assert parsed.sender_email == expected.sender_email
    assert parsed.original_author_email == expected.original_author_email
    assert parsed.sent_at_header == expected.sent_at_header
    assert parsed.sent_at == expected.sent_at
    assert parsed.subject == expected.subject
    assert parsed.attachment_filenames == expected.attachment_filenames
