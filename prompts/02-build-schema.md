/goal In `red-mle-technical-exercise`, create the installable Python package
scaffold and the SQLite schema for the Part A store defined by the current
`docs/requirements.md` and `docs/architecture.md`. Do not seed reference data
and do not implement ingestion. Seeding is the separate
`03-seed-reference-data.md` prompt; ingestion is later work. Continue until
the schema, its tests, and the package scaffold satisfy every completion
condition below.

## One objective

Produce an installable Python 3.11+ package that can create the Part A
SQLite schema, idempotently, via one documented command — and nothing more.
No rows exist in any table when this prompt is done. That is expected.

## Read before editing

1. `docs/requirements.md` and `docs/architecture.md`, in full. They define the
  required behaviour and structural constraints; the table definitions below
  define this prompt's schema scope.
2. `README-EXERCISE.md`, in full — Python version, packaging and
   no-external-service constraints.
3. `tests/conftest.py`, if present — not needed for schema shape, but
   useful context for what the schema will eventually hold.
4. The current repository tree, `git status` and diff. Preserve all
  pre-existing worktree changes. Do not modify `docs/requirements.md`,
   `README-EXERCISE.md`, `data/README.md` or the raw emails.

## Scope boundary

Implement only:

- the installable package scaffold (`pyproject.toml` or equivalent, a
  package directory, declared runtime and test dependencies, `python -m
  pytest` established and documented as the test command). Declare a console
  entry point (e.g. `[project.scripts]`) so that `<tool>` below is a real
  command name rather than a placeholder, and state in this prompt's
  completion report both the editable-install command that makes it available
  and the equivalent `python -m <package>` invocation for a non-installed
  checkout. A CLI that only runs after an undocumented install step does not
  satisfy "one documented command";
- a schema-creation module that issues `CREATE TABLE IF NOT EXISTS` (or
  equivalent) for all 12 tables below, with their real columns, primary
  keys, foreign keys and constraints;
- one documented schema-only CLI command, `<tool> schema --db PATH`, that
  creates the schema at a given SQLite file path and is a no-op if the schema
  already exists. `03-seed-reference-data.md` will add `<tool> init --db PATH`
  as the combined schema-and-seed command; keeping the two entry points
  distinct is what makes the empty-after-schema-only proof executable;
- tests that inspect the actual created schema (via `sqlite_master` /
  `PRAGMA table_info`), not just "the command exited zero". This prompt's tests
  must exercise only the `schema` command and must never invoke `init` or
  import the seed module: `init` and every reference row belong to
  `03-seed-reference-data.md`, and a schema test that happens to insert a row
  matching a seeded one will pass by coincidence and break the moment that
  seed value is revised. Where such a test needs a row to prove data survival,
  use a sentinel no seed script would produce.

Do not implement: reference-data seeding, MIME/email parsing, entity
matching, fact extraction, `README.md`, or `DESIGN.md`. Leave every table
empty. A later prompt seeds it; a later prompt still reads from it.

## The 12 tables

Implement exactly these, with the columns, keys and constraints described
below:

- `messages` — PK `message_id`, declared explicitly `NOT NULL` as well as
  `PRIMARY KEY` because SQLite otherwise permits NULL in a non-`INTEGER`
  primary-key column; nullable `original_author_email`; nullable
  `duplicate_of_message_id` (FK → `messages.message_id`); `body_hash` column
  documented as SHA-256 of the normalised body (normalisation itself is later
  ingestion work).
- `organisations` — PK `org_id`; `canonical_name`.
- `locations` — PK `location_id`; `canonical_name`; `county`.
- `sites` — PK `site_id`; `canonical_name`; `location_id` (FK →
  `locations.location_id`).
- `aliases` — `alias_text`; `entity_type` (constrained to `organisation`,
  `location`, `site`); `entity_id`. No enforced FK to a specific table (the
  target table depends on `entity_type`); document this in a code comment.
- `fact_predicates` — `predicate` (unique, and therefore a valid parent key
  for `facts.predicate`); `noun_alias`. There is one row per canonical
  predicate. `03-seed-reference-data.md` stores that predicate's finite,
  corpus-attested phrase variants as a JSON array in `noun_alias`; do not
  repeat `predicate` rows because that would make the stated foreign key
  unenforceable in SQLite.
- `incidents` — PK `incident_id`; `location_id` (FK → `locations`); `type`
  constrained to `flooding`, `power`, `welfare`, `health`, `road`. Unique
  constraint on `(location_id, type)`. **No `status` column** — this is a
  deliberate omission, not an oversight; add a test that fails if a `status`
  column ever appears.
- `facts` — PK `fact_id`; `message_id` (FK → `messages`); `incident_id` (FK →
  `incidents`); nullable `site_id` (FK → `sites`); `predicate` (FK →
  `fact_predicates.predicate`); `value` numeric; `source_quote` text. No
  update/delete path is required by the schema — append-only is an
  ingestion-time discipline, but a comment should note it here.
- `message_incident_links` — `message_id` (FK), `incident_id` (FK),
  `relationship_type` constrained to `new`, `update`.
- `org_incident_links` — `org_id` (FK), `incident_id` (FK), `role`
  constrained to `reporting`, `mentioned`, `responding`, `warning_issued`
  (all four are valid values even though Part A will only ever populate the
  first two — do not narrow the constraint to what Part A happens to use).
- `incident_incident_links` — `source_incident_id` (FK → `incidents`),
  `target_incident_id` (FK → `incidents`), `relationship_type` constrained
  to `caused_by`, `contributes_to`, `related_to`.
- `processing_issues` — PK `issue_id`; `message_id` (FK → `messages`); `kind`
  constrained to `attachment_not_parsed`, `attachment_missing`,
  `number_no_matching_predicate`, `no_location_matched`,
  `causal_target_missing`; `detail` text.

Use SQLite `CHECK` constraints for the enum-like columns above wherever
SQLite supports it sensibly; where it does not, enforce the constraint in
the schema-creation code and say so in a comment.

## Checkpoint workflow

Work in small vertical checkpoints. At each checkpoint: name the table or
constraint being added; add or update a schema test; implement the minimum
schema-creation code for it; run the narrow test then the full schema test
suite; inspect the actual `sqlite_master` / `PRAGMA table_info` output for
that table; report briefly what changed and what was proven.

## Required verification

Automated tests, against a real temporary SQLite file (no mocked
connection), must prove:

- all 12 named tables exist after running `schema` once;
- every primary-key column is non-null in actual SQLite behaviour, including
  rejection of NULL `messages.message_id` values. Cover the `INTEGER PRIMARY
  KEY` columns too: SQLite auto-assigns a rowid rather than rejecting the
  insert there, so assert that no NULL was *stored* rather than expecting an
  error;
- `incidents` has no `status` column;
- the `(location_id, type)` uniqueness constraint on `incidents` is enforced;
- foreign keys reference the correct parent tables;
- `fact_predicates.predicate` is genuinely unique and genuinely usable as the
  parent key for `facts.predicate`: a second row for the same predicate is
  rejected, and a `facts` row naming an unknown predicate is rejected by
  foreign-key enforcement. This is what makes the one-row-per-predicate
  representation load-bearing rather than a convention;
- the enum-like constraints reject an invalid value (e.g. inserting a
  `message_incident_links` row with `relationship_type = 'bogus'` fails), and
  `org_incident_links.role` both accepts all four defined roles and rejects a
  fifth;
- running `schema` twice against the same database file is a no-op — no error,
  no duplicate tables, no data loss;
- every table is empty immediately after `schema` (nothing is seeded here).

## Completion audit and stopping condition

Before declaring this prompt complete, report: the exact `schema` command,
the files created, the test command and its output, and confirmation that
every one of the 12 tables exists with the columns and constraints listed
above. Do not proceed to seeding or ingestion as part of this prompt.
