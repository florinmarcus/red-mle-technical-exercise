"""Transform RFC email bytes into the canonical message record.

This is a bounded email parser, not a general document-ingestion system. It
selects one plain or HTML MIME body, records attachment names without reading
their contents, reduces HTML with a lightweight text collector, and recognises
an original author only in one exact forwarded-message header form. Those
choices are deterministic and sufficient for the supplied corpus, but other
mail clients, nested forwards, malformed MIME, tables, and attached documents
need broader fixtures and format-specific parsers. A production pipeline would
retain the raw message, classify each MIME part, extract supported attachments
in isolated workers, and version parser outputs so improvements can be replayed.
"""

from __future__ import annotations

import datetime
import email.message
import email.parser
import email.policy
import email.utils
import hashlib
import html.parser

from red_store import model


def normalise_body(body: str) -> str:
    """Convert CRLF and bare CR body line endings to LF.

    Every other character is preserved, including spaces, blank lines, and an
    existing final newline. This keeps the stored body faithful while making
    bodies from mail clients with different line-ending conventions comparable.
    """

    return body.replace("\r\n", "\n").replace("\r", "\n")


def hash_body(body: str) -> str:
    """Return the SHA-256 digest of the line-ending-normalised body.

    The normalised text is encoded as UTF-8 before hashing. The lowercase
    hexadecimal digest supports body-based resend detection; it does not
    identify the raw email bytes.
    """

    return hashlib.sha256(normalise_body(body).encode("utf-8")).hexdigest()


def parse(raw_message: bytes) -> model.Message:
    """Parse raw RFC email bytes into one standard Stage 1 message record.

    Header values supply message identity and provenance. MIME body selection
    prefers one ``text/plain`` representation and falls back to stripped
    ``text/html``. The selected body is line-ending-normalised and hashed;
    attachment contents remain excluded while their filenames are retained.

    An exact, unquoted ``-----Original Message-----`` header block can supply
    ``original_author_email``. A quoted reply-history marker is deliberately
    ignored. ``ValueError`` is raised when no plain or HTML body is selectable,
    and when the Date header is missing or unparseable (see
    ``_parse_sent_at``).
    """

    parsed_email = email.parser.BytesParser(policy=email.policy.default).parsebytes(
        raw_message
    )
    body = _message_body(parsed_email)
    normalised_body = normalise_body(body)
    sent_at_header, sent_at = _parse_sent_at(parsed_email)
    sender_display_name, sender_email = email.utils.parseaddr(
        str(parsed_email["From"])
    )
    return model.Message(
        message_id=str(parsed_email["Message-ID"]),
        sender_display_name=sender_display_name or None,
        sender_email=sender_email,
        original_author_email=_original_author_email(normalised_body),
        sent_at=sent_at,
        sent_at_header=sent_at_header,
        subject=str(parsed_email["Subject"]),
        body=normalised_body,
        body_hash=hash_body(normalised_body),
        attachment_filenames=_attachment_filenames(parsed_email),
    )


def _parse_sent_at(parsed_email: email.message.EmailMessage) -> tuple[str, str]:
    """Return the raw Date header text and its normalised UTC ISO-8601 form.

    RFC 5322 lets a Date header carry ``-0000`` to mean "offset unknown", and
    ``email.utils.parsedate_to_datetime`` returns a naive ``datetime`` for it.
    Converting a naive datetime with ``astimezone`` would silently assume the
    machine's local timezone, making ingestion machine-dependent, so a naive
    result is instead attached to UTC directly; only a datetime that already
    carries an offset is converted. ``ValueError`` is raised when the Date
    header is missing or cannot be parsed, so a missing timestamp never
    reaches the ``NOT NULL sent_at`` column as a silent default.
    """

    date_header = parsed_email["Date"]
    if date_header is None:
        raise ValueError("message has no Date header")
    header_text = str(date_header)
    try:
        parsed_date = email.utils.parsedate_to_datetime(header_text)
    except (TypeError, ValueError) as error:
        raise ValueError(
            f"message has an unparseable Date header: {header_text!r}"
        ) from error
    if parsed_date.tzinfo is None:
        parsed_date = parsed_date.replace(tzinfo=datetime.timezone.utc)
    else:
        parsed_date = parsed_date.astimezone(datetime.timezone.utc)
    return header_text, parsed_date.isoformat()


def _message_body(parsed_email: email.message.EmailMessage) -> str:
    """Select and decode one textual MIME body representation.

    Plain text takes precedence over HTML so ``multipart/alternative`` content
    is not duplicated. HTML is converted to readable text only when no plain
    representation is available. The returned text is not line-ending-
    normalised here. ``ValueError`` is raised when neither form is selectable.
    """

    plain_part = parsed_email.get_body(preferencelist=("plain",))
    if plain_part is not None:
        return plain_part.get_content()

    html_part = parsed_email.get_body(preferencelist=("html",))
    if html_part is None:
        raise ValueError("message has no text/plain or text/html body")
    return _strip_html(html_part.get_content())


def _original_author_email(body: str) -> str | None:
    """Extract an address from an unquoted forwarded-message header block.

    Only an exact ``-----Original Message-----`` line opens a candidate block.
    A case-sensitive ``From:`` header must then appear before the next blank
    line. This deliberately excludes quote-prefixed reply history and unrelated
    ``From:`` text later in the body. ``None`` is returned when no mailbox can
    be parsed from such a block.
    """

    lines = body.splitlines()
    for marker_index, line in enumerate(lines):
        if line != "-----Original Message-----":
            continue
        for header_line in lines[marker_index + 1 :]:
            if not header_line:
                break
            if header_line.startswith("From:"):
                return (
                    email.utils.parseaddr(
                        header_line.removeprefix("From:").strip()
                    )[1]
                    or None
                )
    return None


def _attachment_filenames(
    parsed_email: email.message.EmailMessage,
) -> tuple[str, ...]:
    """Return named MIME attachments in their message order.

    Unnamed attachment parts are omitted. Attachment contents are never read
    into the message body, and prose that merely mentions an attachment does
    not create a filename.
    """

    return tuple(
        filename
        for part in parsed_email.iter_attachments()
        if (filename := part.get_filename()) is not None
    )


class _HTMLTextExtractor(html.parser.HTMLParser):
    """Collect HTML text fragments with a small structural line-break policy.

    Character references are decoded by ``HTMLParser``. ``br`` elements and
    the configured block-like closing tags contribute newlines; this helper is
    intentionally a lightweight email fallback rather than a general renderer.
    """

    _LINE_BREAK_TAGS = {
        "address",
        "article",
        "aside",
        "blockquote",
        "br",
        "div",
        "footer",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "header",
        "li",
        "main",
        "p",
        "section",
        "tr",
    }

    def __init__(self) -> None:
        """Initialise character-reference decoding and an empty fragment list."""

        super().__init__(convert_charrefs=True)
        self.text_fragments: list[str] = []

    def handle_data(self, data: str) -> None:
        """Append one text fragment emitted between HTML tags unchanged."""

        self.text_fragments.append(data)

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        """Represent a ``br`` start tag as a newline.

        ``attrs`` is accepted as part of the ``HTMLParser`` callback contract
        but does not affect text extraction.
        """

        if tag == "br":
            self.text_fragments.append("\n")

    def handle_endtag(self, tag: str) -> None:
        """Append a newline after a configured block-like closing tag."""

        if tag in self._LINE_BREAK_TAGS:
            self.text_fragments.append("\n")


def _strip_html(html_content: str) -> str:
    """Reduce an HTML body to the parser's readable-text fallback form.

    Extracted lines are individually trimmed, leading and trailing blank lines
    are removed, and internal blank lines are retained. Non-empty output is
    joined with LF and ends in exactly one LF; empty HTML produces an empty
    string.
    """

    extractor = _HTMLTextExtractor()
    extractor.feed(html_content)
    extractor.close()
    lines = [line.strip() for line in "".join(extractor.text_fragments).splitlines()]
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines) + ("\n" if lines else "")
