# Senior AI (Machine Learning) Engineer - Technical Exercise

Resilience and Recovery Directorate (RED), MHCLG

---

## Task overview

You will build a small piece of working software and write a short design
note about how you would take it further.

**Please spend no more than four hours on this**. We 
are not expecting anyone to fully complete the task. What you choose to leave 
out - and whether you tell us why - is part of what we are assessing.

Please spend time reading this full brief before beginning to ensure you are
spending your time in the most valuable way.

## What we are assessing

- Whether you write Python that a colleague could pick up, extend and trust
- Whether you can model a messy real-world domain sensibly, so that an LLM can
  reason over your database
- Whether you make good judgement calls about scope under time pressure
- Whether you can design a production system
- Whether you can explain technical trade-offs in writing, clearly and briefly

## What we are not assessing

- How much you can get finished. Unfinished code will not be penalised as long as
  it doesn't stop the rest of the code from running.
- Front-end skills, you do not need to build a UI.
- Cloud deployment, nothing needs to be deployed anywhere.

---

## Ground rules

**No AI endpoint is required.** As we cannot provide every candidate access to an
LLM endpoint, the exercise is built to be completed without one and nobody is 
scored higher for using one. If you want to run something locally, that is fine. 
If your code calls a hosted API, it must still run for us without a key.

The judgement about *where models belong* and how to best use them is what Part B 
and the interview are for.

AI coding assistants are permitted and expected but let us know in the `README.md`
(Part C).

Please use Python 3.11 or later and list your required packages so we can run
your submission.

## Submitting

Send a zip file via email, or a link to a private repository, to `cameron.currie@communities.gov.uk`
(GitHub account: `cameron-currie`) by 23:55 on the 23rd of August.


## Adjustments and access

If you require adjustments for any reason, please contact
`cameron.currie@communities.gov.uk` or `anna.workman@communities.gov.uk`.

---

## The scenario

RED sits at the centre of government's resilience system. During an incident -
flooding, severe weather, loss of power, a public health threat - information
about what is happening often arrives via **email prose**. Local resilience
forums, councils, emergency services, network operators and health bodies all
report in, in their own formats, at their own cadence, correcting and
contradicting each other as the picture develops.

Today, a duty officer reads all of this and retypes the useful parts into
documents and spreadsheets. That works at low volume but it does not scale, it
loses information, and at 3am it depends heavily on one tired person.

The Transformation Unit's job is to build the plumbing that would let this
information land in a structured, queryable form - so that "how many people are
in rest centres in Worcestershire right now, and who told us that?" is a query
rather than a phone call.

This test is a small slice of that problem.

## Dummy data

`data/emails/` contains 16 `.eml` files: a few days of traffic to a fictional
duty mailbox during a flooding event. See `data/README.md`. It is synthetic but
representative - including in the ways it is inconvenient.

---

## Part A - the pipeline (aim for around 2 hours)

Write a Python application that reads the emails and populates a structured,
queryable store of **entities**, **facts reported about them** and **relationships 
between entities**.

We are not going to tell you what the entities are as we want to see your reasoning. 
It is recommended to read the data first, then design.

Hard requirements:

1. **It runs.** A single documented command ingests the directory and produces
   the store.
1. **It is idempotent.** Running the ingest twice does not double up the data.
1. **Facts are attributable.** For anything in the store, it must be possible to
   establish which message it came from, who sent it, and when. A duty officer
   who cannot see where a number came from will not use the number.
1. **The same real-world thing is one thing.** The data refers to the same
   places, organisations and sites in more than one way. Handle as much of this as
   you judge worthwhile but do not spend all of your time handling edge-cases.
   We are interested in how you might generically solve this challenge (Part B).

Deterministic processing is fine for this exercise (regex, lookup tables), but be 
explicit about which parts of the code are not generalisable. Include, in code 
comments and/or Part B, how you might achieve greater generalisability.

Use whatever storage/database you like as long as it needs no external service to run.

## Part B - design note (aim for around 1 hour)

A note of **no more than 1,000 words** (`DESIGN.md`), written for a multi-disciplinary 
team: two engineers, a delivery manager, and a user researcher. Diagrams welcome and 
do not count towards the word limit.

Cover at least:

1. **Target architecture.** How this becomes a service on AWS/Azure/GCP. 
1. **Generalisation.** How you might generically solve this challenge for a larger 
   number/variety of entities.
1. **How you would know it works.** How you would evaluate extraction quality
   in development and whilst live.
1. **First and last.** What you would build in the first six weeks, and one
   tempting thing you would deliberately not build.

Additionally, we welcome you to include anything not listed above if you think 
it is relevant.

## Part C - README (aim for around 30 minutes)

A `README.md` containing:

- How to install and run it, including the exact command to run the ingest and 
  where the store is written.
- The entity model you chose and, briefly, why
- Which AI coding assistants you used and *briefly* where they helped, and where 
  they didn't. We use these tools daily and are interested in how you supervise them.


---

## Thanks and good luck!

We are really looking forward to reading these and seeing what you come up with. 
We've designed this so that it's not too straightforward so don't get worked up 
if you can't achieve everything you wanted.