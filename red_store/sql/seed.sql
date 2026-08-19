PRAGMA foreign_keys = ON;

BEGIN;

-- Existing stable keys are left unchanged so repeat seed runs are no-ops.
INSERT INTO organisations (org_id, canonical_name)
VALUES
    (1, 'West Mercia Local Resilience Forum'),
    (2, 'Environment Agency'),
    (3, 'Hereford and Worcester Fire and Rescue Service'),
    (4, 'West Mercia Police'),
    (5, 'Herefordshire Council'),
    (6, 'Worcestershire County Council'),
    (7, 'DNO'),
    (8, 'UKHSA West Midlands'),
    (9, 'DHSC'),
    (10, 'MHCLG'),
    (11, 'Malvern Hills District Council'),
    (12, 'WI')
ON CONFLICT (org_id) DO NOTHING;

INSERT INTO locations (location_id, canonical_name, county)
VALUES
    (1, 'Ledbury', 'Herefordshire'),
    (2, 'Bromyard', 'Herefordshire'),
    (3, 'Bishop''s Frome', 'Herefordshire'),
    (4, 'Upton-upon-Severn', 'Worcestershire'),
    (5, 'Pershore', 'Worcestershire'),
    (6, 'Great Malvern', 'Worcestershire'),
    (7, 'Malvern Hills', 'Worcestershire')
ON CONFLICT (location_id) DO NOTHING;

INSERT INTO sites (site_id, canonical_name, location_id)
VALUES
    (1, 'St Michael''s Primary School', 1),
    (2, 'Ledbury Community Hall', 1),
    (3, 'Upton Memorial Hall', 4),
    (4, 'Pershore Leisure Centre', 5),
    (5, 'Malvern Cube', 6)
ON CONFLICT (site_id) DO NOTHING;

INSERT INTO organisation_aliases (alias_text, org_id)
VALUES
    ('wmlrf', 1),
    ('LRF', 1),
    ('West Mercia LRF', 1),
    ('West Mercia LRF Secretariat', 1),
    ('LRF comms cell', 1),
    ('Recovery Cell', 1),
    ('Environment Agency Flood Warning Service', 2),
    ('EA', 2),
    ('West Mercia Police Control', 4),
    ('West Mercia Police Force Control Room', 4),
    ('Traffic Management', 5),
    ('Environmental Health', 5),
    ('Adult Social Care Duty', 6),
    ('Adult Social Care Duty Desk', 6),
    ('electricity network operator', 7),
    ('Health Protection Team', 8),
    ('UKHSA West Midlands HPT', 8),
    -- Sender domains. An alias is any text that names an organisation, and the
    -- domain of a corporate address is exactly that, so it lives in the same
    -- lookup rather than a parallel one. Resolution tries the display name
    -- first: 005 is sent by the LRF Secretariat from a police-hosted address,
    -- so its domain would otherwise credit the wrong organisation.
    ('wmlrf.example.gov.uk', 1),
    ('floodwarning.example.gov.uk', 2),
    ('westmercia.example.police.uk', 4),
    ('herefordshire.example.gov.uk', 5),
    ('worcestershire.example.gov.uk', 6),
    ('dno.example.com', 7),
    ('ukhsa.example.gov.uk', 8),
    ('malvernhills.example.gov.uk', 11)
ON CONFLICT (alias_text) DO NOTHING;

INSERT INTO location_aliases (alias_text, location_id)
VALUES
    ('Ledburry', 1),
    ('Upton', 4),
    ('Malvern', 6)
ON CONFLICT (alias_text) DO NOTHING;

INSERT INTO fact_predicates (predicate, noun_alias)
VALUES
    ('properties_flooded', '["residential properties","property flooding figure","properties in Ledbury requiring recovery support"]'),
    ('evacuees', '["residents evacuated","Evacuee numbers"]'),
    ('rest_centre_occupancy', '["Occupancy"]'),
    ('rest_centre_capacity', '["capacity"]'),
    ('customers_off_supply', '["customers currently off supply"]'),
    ('cases_reported', '["cases of gastrointestinal illness"]')
ON CONFLICT (predicate) DO NOTHING;

COMMIT;
