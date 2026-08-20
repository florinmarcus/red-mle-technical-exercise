"""Command-line entry points for provisioning and Stage 1 ingestion."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path
import sys

from red_store import ingest_service, model, provisioning


def _initialise_at(path: Path) -> None:
    """Create the schema then seed reference data, as one idempotent step.

    Both halves are mandatory. ``provisioning`` is imported at module scope on
    purpose: an ``init`` that reported success having created only the schema
    would leave a caller with an unseeded store and a zero exit code, which is
    exactly the silent-incompleteness failure the store exists to avoid. A
    missing or broken seed module must surface as an error.
    """
    already_existed = path.exists()
    provisioning.create_schema(path)
    provisioning.seed_reference_data(path)

    if already_existed:
        print(f"red_store: database already exists at {path}")
    else:
        print(f"red_store: created database at {path}")
    print("red_store: transactional tables (messages, incidents, facts, ...) start empty until ingestion runs.")


def _report_failures(
    failures: Sequence[model.IngestionFailure],
) -> int:
    """Name every unparseable file on stderr and return a failing exit code.

    Messages that failed to parse are not written to the store — in the target
    architecture they belong on a dead-letter queue, not in a table a duty
    officer queries for attribution. Standard error and the exit code are the
    local stand-in for that queue, so the gap is loud even though the store that
    was produced is complete and usable.
    """

    for failure in failures:
        print(
            f"red_store: could not ingest {failure.source_name}: {failure.reason}",
            file=sys.stderr,
        )
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="red")
    subcommands = parser.add_subparsers(dest="command", required=True)
    for command in ("schema", "init"):
        command_parser = subcommands.add_parser(command)
        command_parser.add_argument(
            "--db",
            default=Path("data") / "red-store.sqlite",
            type=Path,
            metavar="PATH",
        )
    ingest_parser = subcommands.add_parser("ingest")
    ingest_parser.add_argument(
        "--db",
        default=Path("data") / "red-store.sqlite",
        type=Path,
        metavar="PATH",
        help="SQLite store to create or update",
    )
    ingest_parser.add_argument(
        "--emails",
        dest="emails_directory",
        required=True,
        type=Path,
        metavar="PATH",
        help="directory containing .eml files to ingest",
    )
    return parser


def _check_python_version() -> int | None:
    """Fail fast with a clear message instead of a confusing traceback.

    The parser relies on ``str.removeprefix`` (3.9+) and PEP 604 union type
    hints evaluated at runtime in older interpreters, so anything before 3.11
    (the version this project targets) either breaks obscurely mid-ingest or
    not at all until a rarely hit code path.
    """
    if sys.version_info < (3, 11):
        version = ".".join(str(part) for part in sys.version_info[:3])
        print(
            f"red_store: requires Python 3.11 or later, but this is {version} "
            f"({sys.executable}).",
            file=sys.stderr,
        )
        return 1
    return None


def main(argv: Sequence[str] | None = None) -> int:
    version_error = _check_python_version()
    if version_error is not None:
        return version_error
    args = build_parser().parse_args(argv)
    if args.command == "schema":
        provisioning.create_schema(args.db)
    elif args.command == "init":
        _initialise_at(args.db)
    else:
        _initialise_at(args.db)
        result = ingest_service.ingest_directory(args.db, args.emails_directory)
        print(
            "red_store: ingestion "
            f"processed={result.processed} "
            f"inserted={result.inserted} "
            f"skipped={result.skipped} "
            f"failed={result.failed}"
        )
        if result.failures:
            return _report_failures(result.failures)
    return 0
