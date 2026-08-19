"""Derive incidents, facts and processing issues from one parsed message.

Extraction is deliberately deterministic and corpus-bound. Incident types are
hard-coded regexes; entities and predicates come from closed, manually seeded
alias tables; place and predicate matches cannot span lines; and numeric values
are associated with the nearest predicate text on the same line. A single
top-to-bottom pass carries one current incident, with no confidence score,
document structure, temporal reasoning, contradiction handling, or second-pass
disambiguation. Unmatched numeric content becomes a processing issue rather
than a guessed fact. These limits make decisions reproducible and inspectable,
but they do not generalise to new vocabularies or message formats.

A production extractor could combine maintained taxonomies and entity
resolution with layout-aware document parsing and schema-constrained model
extraction. Candidate facts would carry confidence and evidence spans, then be
validated against rules and reviewed at calibrated thresholds. Evaluation,
monitoring, replay, and the staged route to that design belong in ``DESIGN.md``.
This module performs no I/O.
"""

from __future__ import annotations

import collections.abc
from dataclasses import dataclass
import re

from red_store import model


_NUMBER_PATTERN = re.compile(
    r"(?<![\w])\d(?:[\d,]*\d)?(?:\.\d+)?(?![\w])"
)
_TYPE_PATTERNS = {
    "power": (
        re.compile(r"\bpower\s+outage\b", re.IGNORECASE),
        re.compile(r"\bde-energised\b", re.IGNORECASE),
        re.compile(r"\bsubstation\b", re.IGNORECASE),
    ),
    "welfare": (
        re.compile(r"\bwelfare\b", re.IGNORECASE),
        re.compile(r"\bpsr\b", re.IGNORECASE),
    ),
    "health": (
        re.compile(r"\bukhsa\b", re.IGNORECASE),
        re.compile(r"\bcluster\b", re.IGNORECASE),
        re.compile(r"\billness\b", re.IGNORECASE),
    ),
    "road": (
        re.compile(r"\broad\s+closed\b", re.IGNORECASE),
        re.compile(r"\broad\s+reopened\b", re.IGNORECASE),
        re.compile(r"\bdiversion\b", re.IGNORECASE),
    ),
    # Flooding comes last so a later floodwater line deliberately moves the
    # current incident from power to flooding, as prompt 10 documents for 011.
    "flooding": (
        re.compile(r"\bflood\w*", re.IGNORECASE),
        re.compile(r"\briver\b", re.IGNORECASE),
        re.compile(r"\bovertopped\b", re.IGNORECASE),
    ),
}


@dataclass(frozen=True)
class _PlaceMatch:
    """The longest seeded place name found on one line."""

    location_id: int
    site_id: int | None
    length: int


@dataclass(frozen=True)
class _AliasMatch:
    """One predicate alias occurrence and its canonical predicate."""

    predicate: str
    start: int
    end: int
    length: int


def extract(
    message: model.Message, vocabularies: model.Vocabularies
) -> model.Extraction:
    """Return the narrow Stage 2 extraction for ``message``.

    The subject is visited first, followed by each body line. Quote-prefixed
    lines are ignored. A type found without an explicit place reuses only the
    location of the current incident; no other context or second pass is used.
    This can attach a later measurement to the wrong incident when prose moves
    between topics, a known trade-off recorded in the README.
    """

    incidents: dict[model.IncidentKey, model.Incident] = {}
    facts: list[model.Fact] = []
    issues: list[model.ProcessingIssue] = []
    current_incident: model.IncidentKey | None = None

    for line in (message.subject, *message.body.splitlines()):
        if line.startswith(">"):
            continue

        place = _match_place(line, vocabularies)
        incident_types = _match_incident_types(line)
        if incident_types:
            location_id = (
                place.location_id
                if place is not None
                else (
                    current_incident.location_id
                    if current_incident is not None
                    else None
                )
            )
            if location_id is not None:
                for incident_type in incident_types:
                    current_incident = model.IncidentKey(
                        location_id=location_id,
                        type=incident_type,
                    )
                    incidents.setdefault(
                        current_incident,
                        model.Incident(
                            location_id=location_id,
                            type=incident_type,
                        ),
                    )

        numbers = tuple(_NUMBER_PATTERN.finditer(line))
        predicate_matches = _match_predicates(line, vocabularies.predicates)
        if predicate_matches and numbers:
            if current_incident is None:
                issues.append(
                    model.ProcessingIssue(
                        kind="no_location_matched",
                        detail=line,
                    )
                )
                continue

            for predicate_match in _one_match_per_predicate(predicate_matches):
                nearest_number = min(
                    numbers,
                    key=lambda number: _span_distance(
                        number.start(),
                        number.end(),
                        predicate_match.start,
                        predicate_match.end,
                    ),
                )
                facts.append(
                    model.Fact(
                        incident=current_incident,
                        site_id=None if place is None else place.site_id,
                        predicate=predicate_match.predicate,
                        value=_number_value(nearest_number.group(0)),
                        source_quote=line,
                    )
                )
        elif numbers:
            issues.append(
                model.ProcessingIssue(
                    kind="number_no_matching_predicate",
                    detail=line,
                )
            )

    return model.Extraction(
        incidents=tuple(incidents.values()),
        facts=tuple(facts),
        issues=tuple(issues),
        reporting_org_id=_reporting_organisation(message, vocabularies),
    )


def _match_place(
    line: str, vocabularies: model.Vocabularies
) -> _PlaceMatch | None:
    candidates: list[_PlaceMatch] = []
    for alias, location_id in vocabularies.locations.items():
        match = _find_alias(line, alias)
        if match is not None:
            candidates.append(
                _PlaceMatch(
                    location_id=location_id,
                    site_id=None,
                    length=match.end() - match.start(),
                )
            )
    for alias, site in vocabularies.sites.items():
        match = _find_alias(line, alias)
        if match is not None:
            candidates.append(
                _PlaceMatch(
                    location_id=site.location_id,
                    site_id=site.site_id,
                    length=match.end() - match.start(),
                )
            )
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda candidate: (
            candidate.length,
            candidate.site_id is not None,
        ),
    )


def _match_incident_types(line: str) -> tuple[str, ...]:
    return tuple(
        incident_type
        for incident_type, patterns in _TYPE_PATTERNS.items()
        if any(pattern.search(line) is not None for pattern in patterns)
    )


def _match_predicates(
    line: str, predicates: collections.abc.Mapping[str, str]
) -> tuple[_AliasMatch, ...]:
    matches: list[_AliasMatch] = []
    for alias, predicate in predicates.items():
        match = _find_alias(line, alias)
        if match is not None:
            matches.append(
                _AliasMatch(
                    predicate=predicate,
                    start=match.start(),
                    end=match.end(),
                    length=match.end() - match.start(),
                )
            )
    return tuple(matches)


def _one_match_per_predicate(
    matches: tuple[_AliasMatch, ...],
) -> tuple[_AliasMatch, ...]:
    longest_by_predicate: dict[str, _AliasMatch] = {}
    for match in matches:
        previous = longest_by_predicate.get(match.predicate)
        if previous is None or match.length > previous.length:
            longest_by_predicate[match.predicate] = match
    return tuple(longest_by_predicate.values())


def _find_alias(line: str, alias: str) -> re.Match[str] | None:
    if not alias:
        return None
    return re.search(
        rf"(?<!\w){re.escape(alias)}(?!\w)",
        line,
        re.IGNORECASE,
    )


def _span_distance(
    first_start: int,
    first_end: int,
    second_start: int,
    second_end: int,
) -> int:
    if first_end <= second_start:
        return second_start - first_end
    if second_end <= first_start:
        return first_start - second_end
    return 0


def _number_value(number: str) -> float:
    return float(number.rstrip(",.").replace(",", ""))


def _reporting_organisation(
    message: model.Message, vocabularies: model.Vocabularies
) -> int | None:
    if (
        message.original_author_email is None
        and message.sender_display_name is not None
    ):
        display_name_match = _exact_alias(
            message.sender_display_name, vocabularies.organisations
        )
        if display_name_match is not None:
            return display_name_match

    address = message.original_author_email or message.sender_email
    domain = address.rpartition("@")[2]
    if not domain:
        return None
    return _exact_alias(domain, vocabularies.organisations)


def _exact_alias(
    alias: str, aliases: collections.abc.Mapping[str, int]
) -> int | None:
    casefolded_alias = alias.casefold()
    return next(
        (
            value
            for candidate, value in aliases.items()
            if candidate.casefold() == casefolded_alias
        ),
        None,
    )
