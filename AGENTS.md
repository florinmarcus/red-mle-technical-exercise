# RED Store

Local SQLite incident store for the RED incident-ingestion exercise: it parses
the supplied emails, persists them as immutable evidence, and derives a
deliberately narrow set of incidents, facts and processing issues from seeded
reference vocabularies. Python 3.11+, standard library only at runtime.

This file is the single agent harness for the repository. There are no
path-scoped rule files, skills or tool-specific instruction files; everything an
agent needs is below.

## Exercise scope — read `README-EXERCISE.md` first

`README-EXERCISE.md` is the assessor's brief and overrides everything below it
if the two ever disagree. Its fundamentals, restated here so they aren't lost
in this file's engineering detail:

- **Time-boxed, not completion-boxed.** Spend no more than ~4 hours total:
  ~2h Part A (code), ~1h Part B (`DESIGN.md`, a prose note, max 1000 words),
  ~30min Part C (`README.md`). Unfinished code is not penalised; what you
  chose to leave out, and whether you say why, is part of what's assessed.
- **Only Part A ships as code.** Part B is a design note about a *hypothetical*
  future service (target architecture, generalisation, evaluation, a six-week
  roadmap). It is never implemented in this repo — it is prose in `DESIGN.md`.
  If a task starts to build the thing Part B merely describes, that is scope
  creep, not thoroughness.
- **What's being assessed:** readable/trustworthy Python, sensible modelling
  of a messy domain, judgement about what to cut under time pressure, ability
  to design (in writing) a production system, and clear written trade-offs.
- **What's not being assessed:** completeness, front-end, cloud deployment.
- **Part A hard requirements:** a single documented ingest command; it is
  idempotent; every fact in the store is attributable to a message, sender and
  time; the same real-world entity referred to differently should be resolved
  as far as is worthwhile, not exhaustively.
- This repo's internal "Stage 1 / Stage 2 / Stage 3" naming (messages →
  incidents → facts) is a sequencing choice *within* Part A's code scope, not
  a second exercise phase. All three still need to land as code inside the
  ~2h Part A budget; none of them is Part B.
- Part A is implemented. Treat additions as changes to a delivered slice:
  update the requirement register before changing behaviour, not after.

## Commands

Run from this directory. Nothing needs installing — `red_store` is imported
from the working directory.

```powershell
python -m red_store ingest --db data\red-store.sqlite --emails data\emails  # the one documented command
python -m red_store init --db data\red-store.sqlite                # schema + reference seed only
python -m red_store schema --db data\red-store.sqlite              # schema only
python -m pytest                                                    # tests
```

`ingest` provisions the store itself; no separate `init` step is required
before it. Expect 16 processed, 16 inserted, 0 failed on a fresh database, and
0 inserted / 16 skipped on a repeat run. Against the current corpus those 16
messages derive 6 incidents and 5 facts, against 60 `processing_issues` — most
numeric content falls outside the closed predicate list and so surfaces as a
processing issue rather than a fact, which is a read of the predicate list's
scope, not an extraction failure. These derived counts must stay in step with
`README.md`'s "Deliberate limitations" section.

## Python conventions

Code follows the [Google Python style
guide](https://google.github.io/styleguide/pyguide.html). The rules this
project actually enforces are the ones below; the Google guide is their
provenance. No formatter enforces them — they are review-time conventions.

- Import the module, not the names inside it, and call through the module:
  `from red_store import message_parser` then `message_parser.parse(...)`.
  Never `from red_store.message_parser import parse`. Every call site must show
  where the callable came from. (Google Python style guide, 2.2.) Exempt:
  `typing`, `collections.abc`, `pathlib.Path`, `dataclasses`, and
  `from __future__ import annotations`.
- If a module name would collide with a local variable, rename the variable,
  not the import — e.g. `with connection.get_connection(db) as open_connection:`.
- In modules that declare type annotations, put
  `from __future__ import annotations` immediately after the module docstring.
  Use `X | None` and `collections.abc` imports, not `typing.Optional` or
  `typing.Sequence`. Tiny entry-point modules with no annotations do not need
  an unused future import.
- Public functions take `pathlib.Path`, not `str`, for filesystem arguments.
- Keep setup-time provisioning (`provisioning.py`) separate from runtime
  connection handling (`connection.py`). That split is deliberate.
- Runtime dependencies stay empty. `pytest` is the only test-time dependency.
  If a runtime dependency seems necessary, explain why and stop for approval
  rather than adding it to `pyproject.toml`.
- Prefer a failure that exits non-zero over a partial success that exits 0.
  `init` must do both halves — schema *and* seed. An `init` that exits 0 having
  created only the schema is the silent-incompleteness bug this store exists to
  prevent.
- Preserve the flat module boundaries: `message_parser` transforms bytes,
  `incident_extractor` interprets a parsed message, each store owns the SQL for
  one aggregate, and `ingest_service` owns orchestration. `tests/test_architecture.py`
  enforces the dependency direction.

## SQL conventions

Schema changes go in `red_store/sql/schema.sql`, not in Python; reference data
goes in `red_store/sql/seed.sql`. Both ship as package data.

- The entity model in `README.md`, the packaged SQL and
  `tests/test_provisioning.py` describe the same implemented slice. Keep them
  aligned; changing one without the others is drift.
- Every statement must be re-runnable: `IF NOT EXISTS` for schema objects and
  an explicit conflict no-op such as `ON CONFLICT (...) DO NOTHING` for
  reference rows. `init` runs both SQL files against an existing database.
- Reference data belongs in `seed.sql`. Ingestion-owned tables stay empty until
  ingestion runs — never seed them.
- Declare foreign keys explicitly.

## Verifying the store

Use this after changing `schema.sql`, `seed.sql` or the pipeline, and before
handing the exercise in. Work against a disposable database so you are testing
creation rather than reuse, and never overwrite `data\red-store.sqlite`.

```powershell
$verifyDb = Join-Path (Get-Location) 'data\red-store.verify.sqlite'
Remove-Item -LiteralPath $verifyDb -Force -ErrorAction SilentlyContinue
python -m red_store ingest --db $verifyDb --emails data\emails
if ($LASTEXITCODE -ne 0) { throw 'Fresh ingest failed.' }

$before = python -c 'import sqlite3,sys; c=sqlite3.connect(sys.argv[1]); print("\n".join(c.iterdump()))' $verifyDb
python -m red_store ingest --db $verifyDb --emails data\emails
if ($LASTEXITCODE -ne 0) { throw 'Second ingest failed.' }
$after = python -c 'import sqlite3,sys; c=sqlite3.connect(sys.argv[1]); print("\n".join(c.iterdump()))' $verifyDb
if (Compare-Object $before $after) { throw 'Second ingest changed the database.' }

python -m pytest
Remove-Item -LiteralPath $verifyDb -Force
```

Then compare the objects and row counts against `docs/requirements.md`,
`schema.sql` and `seed.sql`. Report what each step actually observed — both runs' counters,
whether the logical dumps were identical, and the exact pytest result — rather
than only that it passed, and list every mismatch explicitly. If pytest fails
because the environment cannot create its temp or cache directory, record that
as an environment failure and rerun somewhere writable; do not edit tests to
hide it.

## Authority map

Read the narrowest relevant source when a task touches it. Do not silently pick
one document when the sources disagree; report the drift and reconcile only the
scope the user requested.

- `red_store/sql/schema.sql`, `red_store/sql/seed.sql` and
  `tests/test_provisioning.py` — current executable provisioning behaviour.
- `docs/requirements.md` — the derived Part A requirement register (`PA-*`) and
  the accepted scope limitations (`LIM-*`). A behaviour change updates this
  first.
- `docs/architecture.md` — the internal module and dependency contract for
  code-generating agents. It describes the current flat boundaries for message
  parsing, incident extraction, stores and ingestion orchestration. It is not
  the Part B `DESIGN.md` deliverable.
- `README.md` — the assessor/operator-facing command, entity model and concise
  list of deliberate implementation limitations. A limitation stated here must
  agree with `docs/requirements.md`.
- `tests/conftest.py` — executable per-message expectations for the email
  corpus. Prefer reading this over prose when you need corpus behaviour.
- `data/README.md` — what the sample corpus in `data/emails/` contains.
- `prompts/` — selected historical work samples for schema creation and
  reference seeding. They are not current behavioural authority.
- `docs/input-data-analysis.md` — evidence-led analysis of the supplied input.

## Gotchas

- Windows and PowerShell. Use `\` in documented paths and don't assume a POSIX
  shell in anything user-facing.
- This directory is its own git repository, nested inside an outer one. Check
  `git rev-parse --show-toplevel` before staging anything.
- `pyproject.toml` sets `pythonpath = ["."]`, so tests import `red_store`
  without an install. Don't add `sys.path` shims.
- `data/red-store.sqlite` is gitignored and is a build artifact. Never commit
  it; regenerate it with `ingest`.
