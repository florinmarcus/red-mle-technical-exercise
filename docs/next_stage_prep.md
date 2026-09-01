# Interview preparation — Stage 3

Interview: **Friday 4 September 2026**. Blended, 45 minutes, remote (Teams).

## 0. Tone rule — read this first

The reviewer wrote four clauses of praise and one of criticism, and scored the
submission 78%. Walk in as the engineer who wrote that, not as a candidate
under audit.

- Concede once, in one sentence. Then spend the rest of the time as the person
  who fixes it.
- Do not say "weak", "defect", "failure" or "I should have" more than once in
  the whole interview.
- Never say "you're right" before hearing the whole question.
- Stop talking once the point is made. Silence is the panel's turn.

## 1. Where the marks actually are

45 minutes, three graded areas:

| Area | Share | State of preparation |
|---|---|---|
| Two behaviour questions (Success Profiles, **Level 3**) | ~2/3 of questions | §6 — needs your material |
| ML Engineer capability framework | bulk of technical time | §5 |
| One question on the technical test | one question | §3–§4 |

**The schema answer is one question.** It is worth preparing properly because
the panel arrives with a named reservation, but it is not where most of the
score is. Prepare in this order: **behaviours → ML framework → schema.**

Feedback verbatim:

> You produced well-structured, well-documented code and a strong
> architecture, with thoughtful security, evaluation and delivery planning.
> Your use of AI was purposeful and well reviewed. The main area to
> strengthen is the modelling of relationships between entities,
> particularly where relationships need their own attributes.

## 2. Format, conflicts and names

From the invitation (28 August): 45 minutes, blended; one question on the
technical test; the remainder against the *Machine learning engineer —
Government Digital and Data Profession Capability Framework*; two behaviour
questions — **Changing and Improving** and **Delivering at Pace**.

**Document conflict.** The job advert's Stage 3 lists the behaviours as
*Changing and Improving, and **Working Together***. The invitation says
*Delivering at Pace*. Trust the invitation, but have a Working Together story
ready — the panel may be working from the advert.

**Names.** RED is the **Resilience and Recovery Directorate**. Not
"Resilience and Emergencies". The team is the **Transformation Unit**. Job
contact: Cameron Currie.

**Links.** Open the capability framework, the booking confirmation and the
remote-interview guidance from the original emails. The URLs are not
recoverable from the PDF exports — do not retype them from any summary.

## 3. The feedback, decoded — and the honest uncertainty

The reviewer's phrase — *relationships needing their own attributes* — has at
least four plausible referents in this schema. Do not assume which one.

### 3.1 Ask before committing

Open with a calibration probe. It costs twenty seconds and removes the risk of
confidently fixing the wrong thing:

> "There are a couple of places I'd point at — can I check which you had in
> mind, or shall I take you through the one I think is worst?"

### 3.2 The four candidates, strongest first

**(a) `messages` has no relationship to `organisations` at all.**
`messages.sender_email` and `original_author_email` are raw strings — there is
no `org_id` column (verified). Canonical organisations and an alias table were
built, then not used for the one relationship that matters most: *who sent
this*. That relationship needs its own attributes — `role: author | forwarder
| on_behalf_of` — because message 005 is sent by the LRF Secretariat from a
police-hosted address, and the seed comments say so explicitly.

This is probably the sharpest reading, and it undercuts the fix in §4 from the
inside: putting `message_id` on a link only yields *who said so* if messages
resolve to canonical organisations. Be ready to say that yourself.

**(b) The site↔incident relationship does not exist.** "This site is serving
as a rest centre for this incident, opened at T, capacity C, occupancy O" is a
relationship with its own attributes, and it is flattened into a nullable
`facts.site_id`. The README states the motivating time-variance —
*"rest centres can move between buildings"* — and then models containment as a
static FK.

**(c) The three link tables carry no identity, attribution or time.** See §4.

**(d) `facts` has no valid time of its own.** Only the message's `sent_at`.
"12 properties flooded **as at 0600**" loses the 0600. No unit, no modality,
no as-at qualifier. If this is what the reviewer meant, do **not** open by
calling `facts` the strongest part of the schema.

### 3.3 What the code actually shows (get these right)

- `message_incident_links` **does** carry `message_id` (NOT NULL FK).
  `org_incident_links` and `incident_incident_links` carry no attribution.
  None of the three declares a key, and none carries time.
- `fact_predicates` also has no declared PK — `UNIQUE` only. So it is four
  key-less tables, not three. All are rowid tables, so say "no *declared*
  key", not "no primary key".
- `org_incident_links` currently holds **11 rows with zero duplicates**.
  Nothing dedupes it (`incident_store.py:46` is a bare INSERT, once per
  incident per message) but the collision never fires in this corpus: the
  repeat senders either extract no incident, resolve to a different org via
  `original_author_email`, or are body-hash resends caught upstream.
  **Say "nothing constrains it", never "there are duplicate rows."**
- `incident_incident_links` is empty; no code writes to it.
- `causal_target_missing` is a schema CHECK value the extractor never emits.
  That is dead schema, not a dropped implementation.
- The real fact is `properties_flooded = 12` (message 001, Ledbury). There is
  no 34 in the store — the README's own example does not match the corpus.
  Be ready for that.

## 4. The test question — the answer to give

Deliver the **30-second core** and stop. Hold the rest as reserve cards for
follow-ups. Volunteering three defects unprompted turns one graded question
into three.

### Core answer

> "I made that call consciously — the README argues attribution flows through
> `facts.message_id`, so the organisation link only needed to be
> incident-scoped. The reviewer is right that the reasoning has a hole: it's
> only true for facts. Requirement 3 says *anything* in the store must be
> attributable, and an organisation's role is a claim in its own right that
> nothing attributes. So the decision was deliberate and the justification was
> too narrow. The fix is to hold the link tables to the standard `facts`
> already meets."

This matters: **your README defends the current design with a stated
rationale.** If you call it an oversight, the panel asks whether you didn't
notice or noticed and thought it fine. Owning the decision while rejecting its
rationale is the stronger position and is consistent with the artefact they
hold.

### The one-line demonstration

> A duty officer can ask "who told us `properties_flooded = 12`, and when?"
> and get an answer. They cannot ask "who told us the Environment Agency is
> responding?" Same store, same brief — and hard requirement 3 says *anything*
> in the store, not *any fact*.

### The schema, if asked to show it

```sql
CREATE TABLE org_incident_assertions (
    assertion_id  INTEGER PRIMARY KEY,
    message_id    TEXT NOT NULL REFERENCES messages(message_id),
    org_id        INTEGER NOT NULL REFERENCES organisations(org_id),
    incident_id   INTEGER NOT NULL REFERENCES incidents(incident_id),
    role          TEXT NOT NULL CHECK (role IN
                    ('reporting','mentioned','responding','warning_issued')),
    valid_from    TEXT,
    valid_to      TEXT,
    source_quote  TEXT NOT NULL,
    UNIQUE (message_id, org_id, incident_id, role, valid_from)
);
```

Two things to state before they are asked, because both are traps:

1. **`UNIQUE` gives detection, not idempotency.** A repeat insert raises
   `IntegrityError`, and `ingest_service.py` wraps each message in a
   transaction, so that would roll back the whole message. The writer needs
   `ON CONFLICT DO NOTHING`. The gain is that the constraint *enforces* what
   ingest discipline currently assumes.
2. **`valid_from` belongs in the key.** Outside it, one message cannot assert
   two disjoint intervals — "EA responded Mon–Tue, stood down, responded
   Thursday" in a single retrospective message becomes unrepresentable.

### Reserve cards (deploy on follow-up only)

- **Identity.** `incidents UNIQUE (location_id, type)` makes incident identity
  itself a relationship with no time dimension. Two Ledbury floods a month
  apart are the same row, permanently. A cross-town incident cannot exist.
  `message_incident_links.relationship_type IN ('new','update')` is a
  first-seen flag standing in for the temporal story the incident table cannot
  hold. `DESIGN.md:106` already names the target: *"Incident assignment
  becomes evidence-backed, many-to-many and hierarchical, with provisional
  states and typed `caused_by`/`contributes_to`/`related_to` links."*
- **Bitemporality.** Expect: *"Walk me through populating `valid_from` from an
  email that says 'EA are on scene.' What is `valid_to`? If the next four
  messages don't mention EA, does the role lapse, persist, or become
  unknown?"* Answer: assertions carry **transaction time** (the message's
  `sent_at`, always known) and *optionally* valid time when the text states
  it. Roles do not lapse silently — absence of evidence is not a retraction;
  the current-picture view applies an officer-agreed staleness rule and shows
  the assertion's age rather than deleting it.
- **Migration.** Append-only store, so: create the assertion tables, backfill
  from existing links with `message_id` where derivable and NULL where not,
  dual-write, cut reads over, drop the old tables. The backfill honestly
  cannot recover attribution that was never captured — that gap is the point.

### The brief's own headline query — rehearse this

The brief opens with *"how many people are in rest centres in Worcestershire
right now, and who told us that?"* Against the submitted store:

```sql
SELECT f.predicate, f.value, s.canonical_name, m.sender_email, m.sent_at
FROM facts f
JOIN incidents i  ON i.incident_id = f.incident_id
JOIN locations l  ON l.location_id = i.location_id
LEFT JOIN sites s ON s.site_id = f.site_id
JOIN messages m   ON m.message_id = f.message_id
WHERE l.county = 'Worcestershire'
  AND f.predicate = 'rest_centre_occupancy';
```

**Returns zero rows** (verified). `rest_centre_occupancy` is a seeded
predicate with no facts anywhere in the store. Four separate structural
reasons, and you should be the one to enumerate them:

1. Message 006's pipe-delimited rest-centre tracker is unparsed — its rows
   become `number_no_matching_predicate` issues, so occupancy never lands.
2. There is no site↔incident rest-centre relationship, so "is this site
   currently a rest centre" is unanswerable even with the number.
3. County rollup only works through `incidents.location_id → locations.county`
   — the fact is not itself geolocated.
4. **"Right now" has no handle at all**: facts carry no valid time.

The single Worcestershire fact in the store is `customers_off_supply = 1847`
attached to `(Upton-upon-Severn, flooding)` — which is the documented 011 bug,
visible in one query. Mention it before they find it.

## 5. Machine Learning Engineer capability framework

This is the bulk of the technical time and the submission contains **no
machine learning** — it is regex, a closed predicate list and hand-seeded
aliases. `DESIGN.md` proposes Bedrock, Guardrails, an LLM judge and
AgentCore Evaluations; none of it was built. Prepare to be pressed.

### 5.1 Say this before they do: the vocabularies are fitted to the test set

`seed.sql` seeds predicate aliases lifted verbatim from the 16 supplied
emails — including `"properties in Ledbury requiring recovery support"`, with
a town name inside a predicate alias, and `"cases of gastrointestinal
illness"`. That is fitting to the evaluation set. Therefore:

> "The 16 messages → 6 incidents → 5 facts number in my README is an
> **in-sample** figure. It describes the reach of a vocabulary I seeded by
> hand after reading those emails. I would never report it to a delivery
> manager as accuracy, and the first thing I'd build is a held-out set."

Volunteering this converts the single biggest ML-hygiene hole in the
submission into evidence of judgement.

### 5.2 "You didn't build a model. Why can you do this job?"

Answer in two moves. First, the deliberate one: an LLM was not required, the
brief said nobody scores higher for using one, and for a 4-hour slice a
deterministic extractor with visible failure modes is the honest choice — the
judgement about *where models belong* is what `DESIGN.md` is for. Second, and
this is the part that carries it: **a real prior deployment.** Have ready —

- what the model was and what it served
- throughput / latency / who consumed it
- what broke in production and what you changed
- how you knew it was working after release

*(Fill this in from your own work — it is the single most load-bearing answer
in the technical half.)*

### 5.3 Prepared ground

- **Evaluating an LLM extractor.** Labelled set — who labels, at what cost,
  inter-annotator agreement. Per-field precision/recall, scored separately for
  **span** (did it cite real text) and **value** (is the number right).
  Grounding/hallucination rate. Abstention rate and whether it is calibrated.
  Precision favoured over recall for numeric facts. `DESIGN.md` says "model
  confidence alone is not an acceptance gate" — be ready for *"then what is,
  numerically?"* Answer: officer adjudication on a held-out window, with hard
  gates on correct attribution and zero false merges.
- **MLOps.** Prompt and model versioning with rollback; CI on prompt changes;
  shadow/canary before live; the replay harness in `DESIGN.md`;
  reproducibility of a decision given a version set.
- **Drift.** Guaranteed here — new LRFs, new templates, new incident types.
  Signals: input drift by sender/template, output distribution shift,
  abstention rate, officer correction rate. Ground truth arrives late and only
  via adjudication, so correction rate is the leading indicator.
- **Cost and latency.** Two Bedrock calls per email: cost per message, cost at
  10× volume, why two calls rather than one (call 1 cannot see the database;
  candidates must be resolved by application code), what you would cache, and
  the p95 a 3am duty officer will tolerate.
- **When not to use an LLM.** Your submission is the strongest evidence you
  have — deterministic parsing for email structure, models only where language
  varies. Frame it as a judgement, not a limitation.

### 5.4 On the AI-assisted build

The README's account of the `/goal` evaluator-optimizer loop is unusually
detailed and will be probed. Have ready: **two concrete examples of overruling
the assistant**, and an honest answer to the obvious one —

> *"Did your four guardrails catch the relationship-modelling problem?"*

No. They checked tests, architecture, requirements and the brief — all
internal consistency. None of them asked whether the model was *right for the
domain*. That is a real limit of the loop and worth saying plainly: the
evaluator can only verify what you thought to specify.

## 6. Behaviour questions — Level 3

Grade 7 is scored at **Level 3**. This is mechanical: the panel scores against
published level indicators, so the answers must contain the right *kinds* of
evidence, not just be well told.

**Level 3 Delivering at Pace is about leading and enabling others, not
personal throughput.** Indicators: clarifying roles and ownership across a
team; tracking *team* progress against milestones; giving regular feedback;
reallocating resource when priorities collide; removing barriers; maintaining
performance under pressure while keeping others going.

This means the technical exercise is **not** usable as the spine of a
Delivering at Pace answer — a solo four-hour time-box maps to Level 1/2 and
will score poorly however fluently it is delivered. Use it as a 20-second
garnish at most.

### Structure for each story

150–200 words. Situation ~15%, Task ~15%, **Action ~55%**, Result ~15%. Each
must contain:

- a named moment where priorities collided, and the **trade-off you made and
  communicated**
- **what you did to other people's work** — reallocation, unblocking, setting
  the standard, giving feedback
- a **quantified** result
- one sentence of reflection: what you would do differently

### Story 1 — Delivering at Pace

- Situation:
- Task:
- Action (what you did *to the team's* work):
- Result (number):
- Reflection:
- If pushed: what went wrong? / what would you change? / how did you handle
  the person who disagreed?

### Story 2 — Changing and Improving

Needs an improvement that was **measured, not asserted**, where feedback
changed the design, and where you can state what the change cost.

- Situation:
- Task:
- Action:
- Result (before/after measurement):
- Reflection:
- If pushed: how did you evaluate it afterwards? / what did it cost? / who
  resisted and what did you do?

### Story 3 — Working Together (reserve, per the advert)

- Situation:
- Task:
- Action:
- Result:
- Reflection:

## 7. The five hardest questions

Have an answer for each before Friday.

1. *"Your README defends the incident-scoped org link with a reason. Did you
   not spot the problem, or spot it and think the reasoning was sound?"*
   → §4 core answer. Deliberate decision, too-narrow justification.
2. *"You've attached `message_id` to the link — but `sender_email` is a
   string, not a relationship to `organisations`. What has your fix actually
   attributed?"* → §3.2(a). Say it first if you can.
3. *"Populate `valid_from` from 'EA are on scene.' What is `valid_to`?"*
   → §4 reserve card on bitemporality.
4. *"Your predicate aliases are strings lifted from the emails we gave you.
   What is your held-out estimate of extraction quality?"* → §5.1.
5. *"Tell us about delivering at pace — not this exercise. A time you kept a
   team delivering when priorities collided."* → §6, Story 1.

Near-certain runner-up: *"Show me how your store answers the question in our
brief."* → §4, the Worcestershire query.

## 8. Logistics

- Photo ID: driving licence, passport or ID card.
- PC with Chrome, microphone, webcam. ~5 Mb down / 1 Mb up.
- Teams invite arrives a couple of days before; chase if not received two days
  out.
- Recording requires prior arrangement as a reasonable adjustment.
- Have open: `sql/schema.sql`, `sql/seed.sql`, `incident_store.py`,
  `DESIGN.md`, and this note.
