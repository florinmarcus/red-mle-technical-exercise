PRAGMA foreign_keys = ON;

BEGIN;

CREATE TABLE IF NOT EXISTS messages (
    message_id TEXT NOT NULL PRIMARY KEY,
    sender_email TEXT NOT NULL,
    original_author_email TEXT, -- Author of forwarded report content; NULL for directly received emails.
    sent_at TEXT NOT NULL, -- ISO-8601 UTC; a -0000 (RFC 5322 "offset unknown") header is treated as UTC, not converted from local time.
    sent_at_header TEXT NOT NULL, -- Raw RFC 5322 Date header text, preserved for byte-faithful attribution.
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    body_hash TEXT NOT NULL,
    duplicate_of_message_id TEXT,
    FOREIGN KEY (duplicate_of_message_id) REFERENCES messages(message_id)
);

CREATE TABLE IF NOT EXISTS organisations (
    org_id INTEGER PRIMARY KEY,
    canonical_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS locations (
    location_id INTEGER PRIMARY KEY,
    canonical_name TEXT NOT NULL,
    county TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sites (
    site_id INTEGER PRIMARY KEY,
    canonical_name TEXT NOT NULL,
    location_id INTEGER NOT NULL,
    FOREIGN KEY (location_id) REFERENCES locations(location_id)
);

CREATE TABLE IF NOT EXISTS organisation_aliases (
    alias_text TEXT PRIMARY KEY COLLATE NOCASE,
    org_id INTEGER NOT NULL,
    FOREIGN KEY (org_id) REFERENCES organisations(org_id)
);

CREATE TABLE IF NOT EXISTS location_aliases (
    alias_text TEXT PRIMARY KEY COLLATE NOCASE,
    location_id INTEGER NOT NULL,
    FOREIGN KEY (location_id) REFERENCES locations(location_id)
);

CREATE TABLE IF NOT EXISTS site_aliases (
    alias_text TEXT PRIMARY KEY COLLATE NOCASE,
    site_id INTEGER NOT NULL,
    FOREIGN KEY (site_id) REFERENCES sites(site_id)
);

CREATE TABLE IF NOT EXISTS fact_predicates (
    predicate TEXT NOT NULL UNIQUE,
    noun_alias TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS incidents (
    incident_id INTEGER PRIMARY KEY,
    location_id INTEGER NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('flooding', 'power', 'welfare', 'health', 'road')),
    UNIQUE (location_id, type),
    FOREIGN KEY (location_id) REFERENCES locations(location_id)
);

-- Facts are append-only by ingestion discipline; the schema intentionally has no update path.
CREATE TABLE IF NOT EXISTS facts (
    fact_id INTEGER PRIMARY KEY,
    message_id TEXT NOT NULL,
    incident_id INTEGER NOT NULL,
    site_id INTEGER,
    predicate TEXT NOT NULL,
    value NUMERIC NOT NULL,
    source_quote TEXT NOT NULL,
    FOREIGN KEY (message_id) REFERENCES messages(message_id),
    FOREIGN KEY (incident_id) REFERENCES incidents(incident_id),
    FOREIGN KEY (site_id) REFERENCES sites(site_id),
    FOREIGN KEY (predicate) REFERENCES fact_predicates(predicate)
);

CREATE TABLE IF NOT EXISTS message_incident_links (
    message_id TEXT NOT NULL,
    incident_id INTEGER NOT NULL,
    relationship_type TEXT NOT NULL CHECK (relationship_type IN ('new', 'update')),
    FOREIGN KEY (message_id) REFERENCES messages(message_id),
    FOREIGN KEY (incident_id) REFERENCES incidents(incident_id)
);

CREATE TABLE IF NOT EXISTS org_incident_links (
    org_id INTEGER NOT NULL,
    incident_id INTEGER NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('reporting', 'mentioned', 'responding', 'warning_issued')),
    FOREIGN KEY (org_id) REFERENCES organisations(org_id),
    FOREIGN KEY (incident_id) REFERENCES incidents(incident_id)
);

CREATE TABLE IF NOT EXISTS incident_incident_links (
    source_incident_id INTEGER NOT NULL,
    target_incident_id INTEGER NOT NULL,
    relationship_type TEXT NOT NULL CHECK (relationship_type IN ('caused_by', 'contributes_to', 'related_to')),
    FOREIGN KEY (source_incident_id) REFERENCES incidents(incident_id),
    FOREIGN KEY (target_incident_id) REFERENCES incidents(incident_id)
);

CREATE TABLE IF NOT EXISTS processing_issues (
    issue_id INTEGER PRIMARY KEY,
    message_id TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN (
        'attachment_not_parsed',
        'attachment_missing',
        'number_no_matching_predicate',
        'no_location_matched',
        'causal_target_missing'
    )),
    detail TEXT NOT NULL,
    FOREIGN KEY (message_id) REFERENCES messages(message_id)
);

COMMIT;
