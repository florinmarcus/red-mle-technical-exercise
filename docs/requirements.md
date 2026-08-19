# Part A requirements

> **Status:** Implemented and verified.
>
> **Authority:** `README-EXERCISE.md` is the assessor's source requirement and
> overrides this derived contract. The [architecture](architecture.md) defines
> structural constraints, and `README.md` describes current operator-visible
> behaviour. Root `DESIGN.md` describes a future Part B service and does not
> authorize changes to Part A.

## Purpose

Turn the 16 supplied emails into a local, structured and queryable incident
store while preserving the evidence needed for a duty officer to inspect every
stored fact. The implementation is deliberately bounded by the exercise's
rough two-hour Part A time-box; completeness is not a requirement.

## Requirement register

| ID | Requirement | Acceptance evidence | Status |
|---|---|---|---|
| `PA-01` | One self-explanatory documented command provisions reference data, ingests the directory named by `--emails`, and produces the SQLite store named by `--db` without a prior init step. | Run `python -m red_store ingest --db <fresh-db> --emails data\emails`; expect 16 processed, 16 inserted and no failures. | Implemented |
| `PA-02` | Repeating the same ingest is an exact logical no-op. | Second command run inserts 0, skips 16, and leaves every persisted table unchanged. | Implemented |
| `PA-03` | Messages preserve source evidence needed for attribution: message id, raw sender, original author where detected, sent time and header, subject, canonical body and body hash. | Corpus-wide parser expectations plus literal database-column checks. | Implemented |
| `PA-04` | Every stored fact is attributable to its message, sender, time and verbatim source quote. | Join every fact to its message; require non-empty sender/time and `source_quote` within the canonical body. | Implemented |
| `PA-05` | The store represents entities, reported facts and relationships in queryable relational form. | Provisioning and full-ingest tests; foreign-key and integrity checks. | Implemented |
| `PA-06` | Repeated names for scoped organisations, locations and sites resolve deterministically to seeded canonical entities. Edge cases need not be exhaustive. | Extractor tests for aliases, sender display names/domains and unresolved senders. | Implemented |
| `PA-07` | A resend with a new Message-ID remains stored as evidence but does not generate duplicate derived rows. | 007 points to 001 through `duplicate_of_message_id` and has no facts, incidents or processing issues of its own. | Implemented |
| `PA-08` | Interpretation gaps selected by this bounded extractor remain visible rather than becoming guessed facts. | Required `processing_issues` rows exist for unmatched numeric lines and measurements without a current incident. | Implemented |
| `PA-09` | Runtime ingestion requires no external service and uses deterministic processing. | Python standard library and local SQLite only; architecture dependency tests pass. | Implemented |
| `PA-10` | The limitations of the deterministic approach are stated plainly for assessors and operators. | `README.md` deliberate-limitations section agrees with this register. | Implemented |

## Accepted scope decisions

These are requirements for the current bounded slice, not defects to fix
silently. A proposed change must first update this contract and its acceptance
evidence.

| ID | Accepted decision | Required observable result |
|---|---|---|
| `LIM-01` | The one-pass current-incident rule is not given a confidence score or second disambiguation pass. | 011's 1,847 customers-off-supply fact remains attached to Upton flooding, not power, with intact provenance. |
| `LIM-02` | Broader message context is not used to invent an incident for unanchored measurements. | 003's two measurements and 014's property measurement are `no_location_matched` issues, not facts. |
| `LIM-03` | The pipe-delimited tracker in 006 is not parsed as a table. | Its five data rows are `number_no_matching_predicate` issues; the Worcestershire rest-centre occupancy query returns no rows. |
| `LIM-04` | Reporting-organisation links are incident-scoped rather than message-scoped. | Facts retain raw sender/time through `facts.message_id`; an incident-to-organisation join must not be presented as a unique normalized reporter for one fact. |
| `LIM-05` | Attachment content, missing-attachment interpretation, relative-date resolution, causal links, non-reporting organisation roles and site lifecycle are outside Part A. | No inferred rows are created for those capabilities; the README names the omissions. |
| `LIM-06` | `site_aliases` remains empty and the strict road rule remains unreachable for this corpus. | No speculative site aliases or road incidents are introduced. |

## Semantic acceptance baseline

A fresh full ingest currently yields exactly:

- 16 messages, including 007 as a resend of 001;
- 6 incidents and 11 message-to-incident links;
- 11 incident-scoped reporting-organisation links;
- 5 facts: the three accepted 001 facts, 011's deliberately flooding-attached
  outage fact, and 012's health fact;
- 60 processing issues, including the exact `LIM-02` and `LIM-03` subsets;
- no incident-to-incident links.

The total issue count is evidence for the current rules, not a target to
optimize. Exact required issue subsets and the absence of impermissible facts
are the stable semantic checks.

## Traceability

- `tests/test_message_parser.py` and `tests/conftest.py`: `PA-03`,
  `PA-07`.
- `tests/test_provisioning.py`: `PA-05`, `PA-09`.
- `tests/test_incident_extractor.py`: `PA-06`, `PA-08`, `LIM-01`–`LIM-03`.
- `tests/test_ingest_service.py`: `PA-02`, `PA-04`, `PA-05`, `PA-07`,
  `PA-08`, `LIM-02`–`LIM-04`.
- `tests/test_architecture.py`: `PA-09` and the structural constraints in
  `docs/architecture.md`.
- Fresh CLI ingestion, direct SQL integrity checks and persisted semantic
  queries: `PA-01`–`PA-08` and the semantic acceptance baseline.

## Supporting evidence

The [input data analysis](input-data-analysis.md) records the richer domain
reading of the input. It is evidence and future-model input, not authority for
what Part A currently extracts. Raw `.eml` files and the expectations in
`tests/conftest.py` remain the evidence oracle for literal values.
