"""Shared immutable records exchanged across RED Store boundaries."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class Message:
    """One parser-independent representation of a received email."""

    message_id: str
    sender_display_name: str | None
    sender_email: str
    original_author_email: str | None
    sent_at: str
    sent_at_header: str
    subject: str
    body: str
    body_hash: str
    attachment_filenames: tuple[str, ...]


@dataclass(frozen=True)
class Site:
    """One seeded site and the location that contains it."""

    site_id: int
    location_id: int


@dataclass(frozen=True)
class IncidentKey:
    """Database-independent identity for an incident."""

    location_id: int
    type: str


@dataclass(frozen=True)
class Incident:
    """An extracted incident, optionally resolved to its stored row."""

    location_id: int
    type: str
    incident_id: int | None = None

    @property
    def key(self) -> IncidentKey:
        """Return the location-and-type identity used by extraction."""

        return IncidentKey(location_id=self.location_id, type=self.type)


@dataclass(frozen=True)
class Fact:
    """One attributable measurement extracted for an incident."""

    incident: IncidentKey
    site_id: int | None
    predicate: str
    value: float
    source_quote: str


@dataclass(frozen=True)
class ProcessingIssue:
    """One visible gap encountered while interpreting a parsed message."""

    kind: str
    detail: str


@dataclass(frozen=True)
class Vocabularies:
    """Seeded aliases handed to the pure incident extractor."""

    locations: Mapping[str, int]
    sites: Mapping[str, Site]
    organisations: Mapping[str, int]
    predicates: Mapping[str, str]


@dataclass(frozen=True)
class Extraction:
    """All derived records produced during one walk over a message."""

    incidents: tuple[Incident, ...] = ()
    facts: tuple[Fact, ...] = ()
    issues: tuple[ProcessingIssue, ...] = ()
    reporting_org_id: int | None = None


@dataclass(frozen=True)
class IngestionFailure:
    """One source file that could not be turned into a message.

    ``source_name`` is the file name rather than a full path so the record is
    stable across machines and safe to print. ``reason`` is the exception text,
    which is what an operator needs in order to decide whether to re-send the
    email or fix the ingest.
    """

    source_name: str
    reason: str


@dataclass(frozen=True)
class IngestionResult:
    """Observable outcome of one directory-ingestion request.

    ``processed`` counts every candidate file seen, so it always equals
    ``inserted + skipped + failed``. Failures are carried on the result rather
    than raised: a file that cannot be parsed is dropped from this run and
    reported, and the messages that did parse are still committed.
    """

    processed: int
    inserted: int
    skipped: int
    failures: tuple[IngestionFailure, ...] = ()

    @property
    def failed(self) -> int:
        """Return how many source files could not be turned into a message."""

        return len(self.failures)
