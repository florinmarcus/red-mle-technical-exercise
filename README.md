# RED Store

RED Store ingests the exercise's incident emails into a local SQLite database.
It preserves each parsed message and derives a deliberately narrow set of
incidents, reported facts, reporting-organisation links and visible processing
issues from the seeded vocabularies.

## Install & run

Requires **Python 3.11+**. No packages to install — the runtime uses only the
standard library, so there is nothing to `pip install` before ingesting. (The
tests use `pytest`, the only test-time dependency.)

```powershell
cd red-mle-technical-exercise
python -m red_store ingest --db data\red-store.sqlite --emails data\emails
```

CLI ingest → parser → extractor → SQLite (`messages`, `incidents`, `facts`,
`processing_issues`)

This one command creates the schema, seeds the reference vocabularies and
processes every `.eml` file in the given directory — nothing else needs to
run first. The store is written to `data/red-store.sqlite`; use `--db PATH`
for another location.

It is idempotent by Message-ID: rerunning does not double up messages or
facts. A resend with a different Message-ID but the same normalised body is
still stored as a message (and points back to the first copy), but duplicate
fact extraction is skipped.

`python -m red_store init --db data\red-store.sqlite` creates an empty,
seeded store without ingesting messages.

## Entity model

- **`message`** — immutable source evidence: sender, original forwarded
  author, timestamp, subject, body, body hash. Example: an email from West
  Mercia LRF at 08:12 on day 2, subject "Ledbury update".

  Never edited or overwritten, so it stays the anchor everything else is
  attributed back to.

- **`incident`** — identified by location plus type, e.g. `(Ledbury,
  flooding)`. Messages and reporting organisations link to it rather than
  being copied onto it.

  Later messages about the same flood accumulate against the same incident
  row instead of spawning a new one each time — the same real-world event
  reported five times is one row, not five.

- **`fact`** — an append-only reported number against a closed predicate
  list, e.g. `properties_flooded = 34`, linked to its message and incident
  and keeping the verbatim source line ("34 residential properties
  flooded").

  Rows are never updated. Two senders reporting different figures for the
  same incident both survive as separate facts rather than one overwriting
  the other — resolving which is authoritative is left to a later reader.

- **`location`** (a seeded town, e.g. Ledbury) and **`site`** (a named
  building within one, e.g. Ledbury Community Hall).

  Locations and sites are stored separately because rest centres can move
  between buildings, while a town-level figure may not identify a specific
  building.

- **`organisation`** — a seeded reporting body, e.g. Environment Agency,
  Hereford and Worcester Fire and Rescue Service — linked to incidents via
  `org_incident_links`.

  Seeded with aliases (e.g. "WMLRF" for West Mercia LRF) so the same body
  signing off differently across emails still resolves to one row.

- **`processing_issue`** — records information the extractor cannot reliably
  turn into a fact, such as a number with no matching predicate or a
  measurement that cannot be linked to an incident.

  This makes extraction limitations explicit instead of silently skipping
  unsupported information. It also distinguishes a message containing no
  facts from one containing information the current extractor cannot handle.

## AI coding assistants

Before implementation, I used Claude Code in a human-in-the-loop (HITL)
process to develop the specifications for a spec-driven development (SDD)
workflow. First, I brainstormed with AI to explore the email
corpus, possible entity models and scope trade-offs. Second, I used a structured
"grill me" interview in which the assistant challenged my assumptions and asked
me to make decisions explicit. This produced three artifacts: requirements
defining expected behaviour, architecture defining structural constraints, and
a task prompt defining the bounded work and its acceptance criteria. Where
possible, those criteria were expressed as executable test cases.

For implementation, I ran each task through Claude Code's `/goal` command as
an autonomous, multi-turn evaluator-optimizer loop. The main agent implemented,
tested and refined the work; after each turn, a separate evaluator decided
whether the stated completion condition had been met. I defined four guardrails
for this execution loop, which the evaluator used as its definition of done:

1. The test cases associated with the task's acceptance criteria passed.
2. The implementation complied with the architecture.
3. The implementation complied with the requirements.
4. The implementation remained within `README-EXERCISE.md`, the authoritative
  brief.

I then reviewed the resulting code and evidence rather than treating the
evaluator's verdict as independent proof.

## Attribution and inspection

Every stored fact reaches its sender and timestamp through `facts.message_id`
and includes `source_quote`. Open `data/red-store.sqlite` with SQLite, DBeaver or
another SQLite client to inspect the evidence and links directly.

Unparseable files are reported on stderr, produce a non-zero exit code and are
not represented by fabricated message rows. `processing_issues` is reserved for
interpretation gaps in messages that did parse.

## Deliberate limitations

As run against the current corpus: 16 messages produce 6 incidents and 5
facts, against 60 `processing_issues`. Most numeric content in these emails
is not in the closed predicate list, so it surfaces as a processing issue
rather than a fact — that ratio is a direct read of the predicate list's
scope, not an extraction failure.

**1. Not generalisable by design** (deterministic lookups, deliberately)

- The reference vocabularies (`locations`, `sites`, `organisations`, the
  predicate list) are closed lookup tables, seeded once by hand. They
  resolve only what they were seeded with; anything outside the seed
  becomes a `processing_issue` rather than a guess. See `DESIGN.md` for how
  this generalises beyond a fixed vocabulary.
- The extractor is a single top-to-bottom pass carrying one "current
  incident" forward, with no confidence score and no second pass. This
  keeps the algorithm simple and deterministic, at the cost of the bug
  below.

**2. Defined in the schema but not populated in this slice**

- Organisation roles `mentioned`, `responding` and `warning_issued` — only
  `reporting` is linked, and it is incident-scoped, not message-scoped: a
  fact's authoritative sender/timestamp always come through
  `facts.message_id`, not through `org_incident_links`.
- `incident_incident_links` and causal linkage.
- Attachment contents and missing-attachment references (the SITREP in 013,
  the absent attachment in 016).
- Relative dates (e.g. in 015) are kept as source text, not resolved to
  calendar timestamps.
- The `road` incident type is schema-valid but unreached — no corpus message
  meets the deliberately strict place-plus-keyword rule.

**3. Known bug** (a consequence of the compromise above, not fixed with a
special case)

- In 011, the word `floodwater` sets flooding as the current incident; the
  1,847 customers-off-supply figure that follows inherits it too, even
  though it describes the power outage. The source line is still stored
  correctly — only the incident it's linked to is wrong.

**4. Known gaps in this corpus** (visible as `processing_issues`, not lost)

- The extractor matches site names within a single line. In 015, the
  canonical site name "Upton Memorial Hall" wraps across two source lines
  ("...Upton Memorial" / "Hall...") and so doesn't resolve — a line-wrap
  gap, not a missing alias.
- 003 and 014's measurements have no incident under the strict one-pass
  rule → recorded as `no_location_matched`.
- 006's pipe-delimited rest-centre tracker isn't parsed → its five rows
  become `number_no_matching_predicate` issues, not Worcestershire
  occupancy facts.
