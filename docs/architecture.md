# Part A architecture

Module boundaries and runtime flow for `red_store`. Implements the
[Part A requirements](requirements.md), informed by the
[input data analysis](input-data-analysis.md). The future service belongs in
root `DESIGN.md`.

## Modules

- `cli`: arguments, output, exit codes.
- `provisioning`: schema creation and reference seeding.
- `ingest_service`: ordering and per-message transactions.
- `message_parser`: raw bytes to `Message`. Pure; no file or database access.
- `incident_extractor`: `Message` plus `Vocabularies` to `Extraction`. Pure.
- Stores: SQL for one table or aggregate. No parsing or extraction.
- `model`: shared frozen records.
- `connection`: SQLite connections. `sql/`: packaged schema and seed.

## Dependency rule

Dependencies point inward; never back into orchestration.

```
cli  ->  ingest_service  ->  message_parser
                        ->  incident_extractor
                        ->  store
message_parser      ->  model
incident_extractor  ->  model
store               ->  model
```

Parser, extractor and stores depend on `model`, never on each other or the
workflow. `ingest_service` composes them. Nothing imports `cli`.

`tests/test_architecture.py` enforces the boundaries most vulnerable to
accidental drift: runtime modules remain flat; parser and extractor cannot use
filesystem or SQLite modules; stores cannot depend on transformations or
workflow code; and SQL execution stays out of transformations, `ingest_service`,
`cli` and `model`.

## Component view

```mermaid
graph TD
    CLI["cli<br/><i>shell</i>"]
    SVC["ingest_service<br/><i>service</i>"]
    MP["message_parser<br/><i>parser</i>"]
    EX["incident_extractor<br/><i>extractor</i>"]
    MS["message_store<br/><i>store</i>"]
    RS["reference_store<br/><i>store</i>"]
    IS["incident_store<br/><i>store</i>"]
    PS["processing_issue_store<br/><i>store</i>"]
    MODEL["model<br/><i>records</i>"]
    CONN["connection + provisioning<br/><i>infrastructure</i>"]
    DB[("SQLite<br/>red-store.sqlite")]

    CLI --> SVC
    SVC --> MP
    SVC --> EX
    SVC --> MS
    SVC --> RS
    SVC --> IS
    SVC --> PS
    SVC --> CONN
    MP --> MODEL
    EX --> MODEL
    MS --> MODEL
    RS --> MODEL
    IS --> MODEL
    PS --> MODEL
    MS --> DB
    RS --> DB
    IS --> DB
    PS --> DB
    CONN --> DB
```

## Ingest sequence

Provision once, load vocabularies once, then handle each parsed message in its
own transaction.

```mermaid
sequenceDiagram
    actor Operator
    participant CLI as cli
    participant Provisioning as provisioning
    participant Service as ingest_service
    participant References as reference_store
    participant Parser as message_parser
    participant Messages as message_store
    participant Extractor as incident_extractor
    participant Incidents as incident_store
    participant Issues as processing_issue_store
    participant DB as SQLite

    Operator->>CLI: ingest --db PATH --emails PATH
    CLI->>Provisioning: create_schema(database)
    Provisioning->>DB: execute schema.sql
    CLI->>Provisioning: seed_reference_data(database)
    Provisioning->>DB: execute seed.sql
    CLI->>Service: ingest_directory(database, emails_directory)
    Service->>DB: open connection
    Service->>References: load_vocabularies(connection)
    References->>DB: select reference rows and aliases
    References-->>Service: Vocabularies

    loop Each .eml file, sorted by name
        Service->>Service: read file bytes
        alt File cannot be read
            Service->>Service: record IngestionFailure
        else File read
            Service->>Parser: parse(raw bytes)
            alt Message cannot be parsed
                Parser-->>Service: error
                Service->>Service: record IngestionFailure
            else Message parsed
                Parser-->>Service: Message
                Service->>Messages: exists(connection, message_id)
                Messages->>DB: query message id
                alt Message-ID already exists
                    Messages-->>Service: true
                    Service->>Service: count as skipped
                else New Message-ID
                    Service->>Messages: first_with_body_hash(connection, body_hash)
                    Messages->>DB: query body hash
                    Service->>Messages: insert(message, duplicate id)
                    Messages->>DB: insert message
                    alt Body is a resend
                        Service->>Service: skip derived extraction
                    else New body
                        Service->>Extractor: extract(message, vocabularies)
                        Extractor-->>Service: Extraction
                        Service->>Incidents: insert(message_id, extraction)
                        Incidents->>DB: insert incidents, facts and links
                        loop Each processing issue
                            Service->>Issues: insert(message_id, issue)
                            Issues->>DB: insert processing issue
                        end
                    end
                    Service->>DB: commit message transaction
                    Service->>Service: count as inserted
                end
            end
        end
    end

    Service-->>CLI: IngestionResult
    CLI-->>Operator: counters, failures and exit code
```

## Contracts

- `message_parser.parse(bytes) -> Message` owns RFC/MIME normalization.
- `incident_extractor.extract(Message, Vocabularies) -> Extraction` owns
  interpretation.
- Stores own persistence and resolve extracted natural keys to database IDs.
- `model.py` records are immutable values crossing these boundaries.
- One parsed message and all its derived rows commit together.
- Read or parse failures are collected; write failures propagate.

No interfaces, dependency-injection container, ORM, event bus or plugin layer:
one implementation, one input shape, one SQLite store.
