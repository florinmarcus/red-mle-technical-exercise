# Prompt 03 — Seed the five reference tables

Produces one seed script/module that populates the five static reference-data
tables: `organisations`, `locations`, `sites`, `aliases` and
`fact_predicates`. Written
after the schema exists (`02-build-schema.md`) and before ingestion. Ingestion
must later treat these tables as
read-only; this prompt is the only place that writes to them.

---

Read all 16 `.eml` files in `data/emails/` directly, plus
`docs/requirements.md` and the expected facts in `tests/conftest.py`. Do not
invent organisations, locations, sites or aliases that are not attested
somewhere in the corpus. Use `tests/conftest.py` as a
cross-check for mention strings you've already extracted — but resolving
each mention to a canonical row is this prompt's own judgement call, not
something to copy mechanically from the contract.

Build one seed script (a single module, not five), because the five tables
are one seeding concern and `aliases` rows depend on the ids assigned to the
other four. It must be:

- callable as part of the documented CLI, alongside the schema-only command
  from `02-build-schema.md`: `<tool> schema --db PATH` creates empty tables,
  while `<tool> init --db PATH` runs schema creation then seeding in one
  idempotent step. Both halves of `init` are mandatory: if seeding cannot run
  at all — the seed module is missing from the installed package, or seeding
  raises — `init` must fail loudly with a non-zero exit, never exit zero
  having created only the schema. Do not wrap the seed import in a
  skip-if-absent fallback; an `init` that silently returns an unseeded store
  is indistinguishable from a working one, which is the exact failure mode
  `processing_issues` exists to prevent elsewhere in this design;
- idempotent — running it twice against an already-seeded database inserts
  no duplicate rows;
- read-only with respect to `messages`, `incidents`, `facts` and the link
  tables — it never touches them.

## Cover

1. `organisations` — every *identifiable organisation* that reports, is
   forwarded, or is mentioned across the 16 emails (e.g. West Mercia Local
   Resilience Forum, West Mercia Police, the Environment Agency, Fire and
   Rescue, the DNO and UKHSA — read the corpus for the full, exact set).
   Resolve an attested department or sender function to an attested parent
   only where the message itself makes that parentage clear. Do not turn
   generic roles, temporary meetings/groups, programmes, sender display names
   or an otherwise-unresolved email domain into invented organisations merely
   to maximise row count; record that boundary in the seed provenance.
2. `locations` — every incident-relevant town/village mentioned, with its
   county, plus the explicitly required Malvern Hills district row. Use Great
   Malvern as the canonical town named by 006, resolve the attested shorter
   `Malvern` mention to it, and keep it distinct from Malvern Hills (the
   district/council) as the human analysis requires. Do not promote roads,
   streets, rivers, catchments, estates, counties or regions to town/village
   rows. Place-name attestation must cite the corpus; county is a normalised
   geography attribute and its provenance must say when the corpus does not
   state the town-to-county relationship directly.
3. `sites` — the five named rest-centre/building sites, each linked to its
   `location_id` (006's pipe-delimited tracker names all five in one place).
4. `aliases` — one row per alternative name string actually found in the
   corpus, each pointing at the `entity_type` and `entity_id` it resolves to.
   Examples that are genuinely attested are `wmlrf` inside sender domains,
  `LRF`, `Upton` and `Malvern`; matching may be
   case-insensitive, so input `WMLRF` resolves through the attested lowercase
  row. Do not seed generic building-category aliases (for example
  `Community Hall`) because they are too ambiguous for deterministic site
  resolution. Do not add hypothetical aliases that don't appear anywhere in
  the corpus.
5. `fact_predicates` — exactly one row for each member of the closed
   vocabulary: `properties_flooded`, `evacuees`,
   `rest_centre_occupancy`, `rest_centre_capacity`,
   `customers_off_supply`, `cases_reported`. The row's `noun_alias` is a JSON
   array of finite, literal, corpus-attested phrase variants for that
   predicate. This one-row-per-predicate representation preserves the unique
   parent key required by `facts.predicate` while still keeping variants in
   reference data rather than ingestion code. Include the bounded variants
   needed for every worked example, including the noun-before-number forms
   `capacity 80` and `Evacuee numbers have risen to 65`. Do not include bare
   `properties`: 004's `Approximately 210 properties are within the warning
   area` is exposure, not impact, and must remain outside
   `properties_flooded`. Each JSON-array member needs its own evidence citation
   in the provenance report.

## Constraints

- Read-only against every table this prompt does not own. Do not touch
  `messages`, `incidents`, `facts`, or any link/issue table.
- No fuzzy matching, no invented entities, no speculative aliases "in case a
  future email uses them" — every row must trace to something in the
  corpus.
- Do not implement MIME parsing, entity matching against message bodies, or
  fact extraction. Later ingestion work must only ever *read* the tables this
  prompt writes.

## Required verification

Add a test (using a real temporary SQLite database created via the
`02-build-schema.md` schema command) that proves, at minimum:

- Great Malvern (town) and Malvern Hills (district) exist as distinct
  `locations` rows — assert both `location_id`s differ and assert the county on
  each row, not only on the district — and `Malvern` resolves to Great Malvern
  rather than to the district;
- all five named sites exist and are each linked to the correct
  `location_id`;
- input "WMLRF" resolves case-insensitively, via the corpus-attested `wmlrf`
  alias row, to the correct `organisations` row;
- the `fact_predicates` table contains exactly the closed vocabulary defined
  in this prompt, and the noun-alias variants needed to extract "capacity 80"
  and "Evacuee numbers have risen to 65";
- running the seed step twice produces no duplicate rows in any of the five
  tables (compare row counts before and after the second run);
- every row in every reference table, and every member of a predicate's JSON
  alias array, can be traced back to a quoted source line from a specific
  `.eml` file — and the check must confirm the quoted fragment actually occurs
  at the cited physical line, not merely that a citation was supplied;
- every `locations` row carries the explicit normalised-county note, asserted
  by a test rather than left to reviewer goodwill, so a reader can always tell
  an attested place name from an inferred county. Report this traceability,
  don't just assert it.

Confirm the reference tables are fully seeded and stable before ingestion
begins reading from them.
