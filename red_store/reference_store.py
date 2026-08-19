"""Load the tightly bound cluster of seeded reference vocabularies."""

from __future__ import annotations

import json
import sqlite3

from red_store import model


def load_vocabularies(
    open_connection: sqlite3.Connection,
) -> model.Vocabularies:
    """Return all canonical names and seeded aliases used by extraction."""

    locations = {
        str(canonical_name): int(location_id)
        for location_id, canonical_name in open_connection.execute(
            "SELECT location_id, canonical_name FROM locations"
        )
    }
    locations.update(
        {
            str(alias_text): int(location_id)
            for alias_text, location_id in open_connection.execute(
                "SELECT alias_text, location_id FROM location_aliases"
            )
        }
    )

    sites_by_id = {
        int(site_id): model.Site(
            site_id=int(site_id),
            location_id=int(location_id),
        )
        for site_id, location_id in open_connection.execute(
            "SELECT site_id, location_id FROM sites"
        )
    }
    sites = {
        str(canonical_name): sites_by_id[int(site_id)]
        for site_id, canonical_name in open_connection.execute(
            "SELECT site_id, canonical_name FROM sites"
        )
    }
    sites.update(
        {
            str(alias_text): sites_by_id[int(site_id)]
            for alias_text, site_id in open_connection.execute(
                "SELECT alias_text, site_id FROM site_aliases"
            )
        }
    )

    organisations = {
        str(canonical_name): int(org_id)
        for org_id, canonical_name in open_connection.execute(
            "SELECT org_id, canonical_name FROM organisations"
        )
    }
    organisations.update(
        {
            str(alias_text): int(org_id)
            for alias_text, org_id in open_connection.execute(
                "SELECT alias_text, org_id FROM organisation_aliases"
            )
        }
    )

    predicates: dict[str, str] = {}
    for predicate, noun_alias in open_connection.execute(
        "SELECT predicate, noun_alias FROM fact_predicates"
    ):
        for alias in json.loads(str(noun_alias)):
            predicates[str(alias)] = str(predicate)

    return model.Vocabularies(
        locations=locations,
        sites=sites,
        organisations=organisations,
        predicates=predicates,
    )
