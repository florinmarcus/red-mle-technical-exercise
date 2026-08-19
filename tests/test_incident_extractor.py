"""Pure extraction tests against messages parsed from the real corpus."""

from __future__ import annotations

import dataclasses

from red_store import incident_extractor, message_parser, model
from tests import conftest


_VOCABULARIES = model.Vocabularies(
    locations={
        "Ledbury": 1,
        "Ledburry": 1,
        "Bromyard": 2,
        "Bishop's Frome": 3,
        "Upton-upon-Severn": 4,
        "Upton": 4,
        "Pershore": 5,
        "Great Malvern": 6,
        "Malvern": 6,
        "Malvern Hills": 7,
    },
    sites={
        "St Michael's Primary School": model.Site(1, 1),
        "Ledbury Community Hall": model.Site(2, 1),
        "Upton Memorial Hall": model.Site(3, 4),
        "Pershore Leisure Centre": model.Site(4, 5),
        "Malvern Cube": model.Site(5, 6),
    },
    organisations={
        "West Mercia Local Resilience Forum": 1,
        "West Mercia LRF Secretariat": 1,
        "wmlrf.example.gov.uk": 1,
        "floodwarning.example.gov.uk": 2,
        "westmercia.example.police.uk": 4,
        "herefordshire.example.gov.uk": 5,
        "worcestershire.example.gov.uk": 6,
        "dno.example.com": 7,
        "ukhsa.example.gov.uk": 8,
        "malvernhills.example.gov.uk": 11,
    },
    predicates={
        "residential properties": "properties_flooded",
        "property flooding figure": "properties_flooded",
        "properties in Ledbury requiring recovery support": (
            "properties_flooded"
        ),
        "residents evacuated": "evacuees",
        "Evacuee numbers": "evacuees",
        "Occupancy": "rest_centre_occupancy",
        "capacity": "rest_centre_capacity",
        "customers currently off supply": "customers_off_supply",
        "cases of gastrointestinal illness": "cases_reported",
    },
)


def test_capacity_uses_the_nearest_number_and_the_named_site() -> None:
    extraction = _extract("001-lrf-sitrep-01.eml")

    capacity_fact = next(
        fact
        for fact in extraction.facts
        if fact.predicate == "rest_centre_capacity"
    )
    assert capacity_fact.value == 80
    assert capacity_fact.value != 600
    assert capacity_fact.site_id == 2
    assert capacity_fact.incident.location_id == 1


def test_thousands_separator_is_removed() -> None:
    extraction = _extract("011-dno-outage.eml")

    supply_fact = next(
        fact
        for fact in extraction.facts
        if fact.predicate == "customers_off_supply"
    )
    assert supply_fact.value == 1847


def test_quote_prefixed_reply_history_yields_nothing() -> None:
    extraction = _extract("003-reply-chain.eml")

    assert extraction.facts == ()
    assert {
        issue.detail
        for issue in extraction.issues
        if issue.kind == "no_location_matched"
    } == {
        "Evacuee numbers have risen to 65. Ledbury Community Hall reached "
        "capacity at",
        "Confirmed property flooding figure is now 19, which aligns with what",
    }
    output_quotes = [fact.source_quote for fact in extraction.facts]
    output_quotes.extend(issue.detail for issue in extraction.issues)
    assert all(not quote.startswith(">") for quote in output_quotes)


def test_014_retains_an_unanchored_measurement_as_an_issue() -> None:
    extraction = _extract("014-html-newsletter-update.eml")

    assert extraction.facts == ()
    assert {
        issue.detail
        for issue in extraction.issues
        if issue.kind == "no_location_matched"
    } == {
        "- 19 properties in Ledbury requiring recovery support, 7 in "
        "Upton-upon-Severn"
    }


def test_006_retains_each_tracker_row_as_an_issue_without_parsing_it() -> None:
    extraction = _extract("006-rest-centre-table.eml")

    tracker_issue_details = tuple(
        issue.detail
        for issue in extraction.issues
        if issue.kind == "number_no_matching_predicate" and "|" in issue.detail
    )
    assert tracker_issue_details == (
        "St Michael's Primary School     | Ledbury             | Open   | "
        "65        | 150",
        "Ledbury Community Hall          | Ledbury             | Closed | "
        "0         | 80",
        "Upton Memorial Hall             | Upton-upon-Severn   | Open   | "
        "12        | 90",
        "Pershore Leisure Centre         | Pershore            | Standby| "
        "0         | 200",
        "Malvern Cube                    | Great Malvern       | Standby| "
        "0         | 120",
    )
    assert extraction.facts == ()


def test_number_without_a_predicate_is_a_processing_issue() -> None:
    extraction = _extract("001-lrf-sitrep-01.eml")

    assert any(
        issue.kind == "number_no_matching_predicate"
        and "3 pumps, 1 boat team" in issue.detail
        for issue in extraction.issues
    )


def test_005_prefers_the_sender_display_name_to_the_address_domain() -> None:
    extraction = _extract("005-meeting-invite.eml")

    assert extraction.reporting_org_id == 1


def test_002_resolves_the_reporting_organisation_from_its_domain() -> None:
    extraction = _extract("002-district-freeform.eml")

    assert extraction.reporting_org_id == 5


def test_004_credits_the_forwarded_author_before_the_outer_sender() -> None:
    message = dataclasses.replace(
        _message("004-forwarded-ea-warning.eml"),
        sender_display_name="West Mercia LRF Secretariat",
    )

    extraction = incident_extractor.extract(message, _VOCABULARIES)

    assert extraction.reporting_org_id == 2


def test_unknown_gloucestershire_sender_is_not_guessed() -> None:
    message = dataclasses.replace(
        _message("002-district-freeform.eml"),
        sender_display_name=None,
        sender_email="duty@gloucestershire.example.gov.uk",
        original_author_email=None,
    )

    extraction = incident_extractor.extract(message, _VOCABULARIES)

    assert extraction.reporting_org_id is None


def _extract(filename: str) -> model.Extraction:
    return incident_extractor.extract(_message(filename), _VOCABULARIES)


def _message(filename: str) -> model.Message:
    return message_parser.parse((conftest.EMAILS / filename).read_bytes())
