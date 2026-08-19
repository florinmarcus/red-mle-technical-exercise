# Input data analysis

## Purpose and analytical approach

This document records what the supplied emails imply for the
[Part A requirements](requirements.md) and the future service in root
`DESIGN.md`. Filenames are inventory labels only, never source metadata.
Message headers, decoded MIME content, quoted or forwarded sections and
attachment content are the evidence.

An **incident** is an operationally coherent situation with its own lifecycle and command decisions. Related incidents can sit beneath a broader response. A message may therefore link to multiple incidents with different roles: primary report, secondary mention, causal link, coordination, or recovery summary. A warning or unconfirmed signal is not automatically promoted to an incident.

## Recommended incident structure

**Umbrella response: West Mercia severe weather, 27–29 January 2026**

| Incident or tracked situation | Status and relationship | Core messages | Rationale |
|---|---|---|---|
| Leadon/Ledbury flooding (`LEADON-27JAN`) | Confirmed child incident; response closed 29 Jan 09:00 and moved to recovery | 001, 002, 003, 007, 008, 009, 012, 013, 014 | Same Leadon flooding, Ledbury impacts, rest-centre movement and road disruption. Message 012 explicitly uses this reference. |
| Upton-upon-Severn flooding | Confirmed child incident | 004, 006, 010, 011, 013, 014, 015 | Warning, river peak, property impacts, evacuation and Upton rest centre form a separate geographical and hydrological event. |
| Upton power outage | Confirmed incident caused by Upton flooding | 010, 011, 013 | It has a distinct owner, affected population, restoration lifecycle and welfare consequences, so it should remain queryable separately while linked causally to the flood. |
| Bromyard surface-water disruption | Confirmed low-priority child incident | 002, 013, 014 | The sender explicitly calls it separate and unrelated to Ledbury. It progresses from inaccessible to reopened. |
| Eileen Fairhurst welfare case | Confirmed protected operational case linked to Upton flood and outage | 010; context in 011 | A person-level safeguarding task with a two-hour deadline, not merely another flood impact. It requires restricted handling and case closure evidence. |
| Possible gastrointestinal cluster | Unconfirmed health situation linked to Leadon flooding | 012 | UKHSA explicitly says to treat it as linked rather than separate pending results. Model as a provisional child situation, not a confirmed independent incident. |
| Bishop's Frome flood alert | Monitoring signal; no impact incident yet | 002 | An alert is in force but “nothing happening yet”. Retain the warning and location without inventing an incident. |

Message 005 is umbrella-response coordination rather than a situation report. Message 016 cannot be assessed because its claimed spreadsheet is absent.

### Messages that cross incident boundaries

These messages demonstrate why email-level single-label classification is insufficient:

- **002:** updates Leadon/Ledbury, explicitly introduces separate Bromyard surface-water disruption, and mentions a Bishop's Frome monitoring alert. Its Woodleigh Road power loss is a Ledbury flood impact unless later evidence establishes a distinct outage; it must not be merged with the Upton DNO outage.
- **006:** reports active rest centres for both Ledbury and Upton plus regional standby capability at Pershore and Great Malvern.
- **010:** connects the Upton flood warning area, the power outage and one restricted person-level welfare case.
- **011:** describes the flood-caused Upton power incident and area-wide PSR/welfare activity; it contextualises but does not resolve the named case in 010.
- **012:** creates a provisional public-health situation while explicitly linking it to the established Leadon incident rather than declaring independence.
- **013:** one regional SITREP updates Leadon/Ledbury, Upton flooding, the Upton power outage and Bromyard disruption.
- **014:** one recovery update covers Leadon phase transition, Ledbury and Upton recovery impacts, and Bromyard reopening.
- **005:** belongs to the umbrella response as coordination but contains no evidence that every agenda topic was active or discussed.

## Message-to-incident assessment

| Msg | Evidence value | Incident links | Treatment |
|---:|---|---|---|
| 001 | High | Leadon/Ledbury | Baseline 07:00 SITREP. Preserve approximate quantities and forecast separately from observed impacts. |
| 002 | High but informal | Leadon/Ledbury; Bromyard; Bishop's Frome; possibly local Ledbury power disruption | Split into separate incident-scoped claims. Resolve “Ledburry” to Ledbury but preserve the original text. |
| 003 | High | Leadon/Ledbury | Extract only the new reply as new assertions. Link the quoted 001 content as repeated evidence, not fresh observations. |
| 004 | High | Upton flooding | Preserve both the forwarding sender and the Environment Agency as the original claim author. “210 properties within warning area” is exposure, not flooded-property count. |
| 005 | Operational | Umbrella response | Store the TCG event and invitation; do not manufacture situation facts from a standing agenda. |
| 006 | High | Leadon/Ledbury; Upton flooding | One table spans incidents. Each row links to the relevant incident; standby sites are capabilities, not active impacts. |
| 007 | Duplicate evidence | Leadon/Ledbury | Same substantive report as 001 with a different Message-ID and received time. Keep both messages and group them as semantic duplicates; do not double-count facts. |
| 008 | High but later qualified | Leadon/Ledbury | Claim that the A417 reopened at 14:00. Retain as an attributable assertion subsequently narrowed/contradicted by 009. |
| 009 | High | Leadon/Ledbury | Police clarify that only the northern section reopened and the Gloucester Road junction remained closed. Also adds two closures. |
| 010 | High, highly sensitive | Upton flooding; Upton outage; welfare case | Restrict person, address, phone and medical-dependency data. Create an urgent unresolved action; do not infer completion from later area-level restoration alone. |
| 011 | High | Upton outage; Upton flooding; welfare context | Area outage report with ETR, generator deployment and Priority Services Register contact progress. It does not confirm the named resident was contacted. |
| 012 | High, restricted | Leadon/Ledbury; possible GI cluster | Preserve uncertainty, embargo (“not for onward circulation”), case definitions and pending test date. Do not assert floodwater causation. |
| 013 | High | Leadon/Ledbury; Upton flooding; Upton outage; Bromyard | Body is only a covering note; facts are in the decoded attachment. Attachment provenance must remain connected to the parent message. |
| 014 | High | Umbrella recovery; Leadon/Ledbury; Upton flooding; Bromyard | Plain-text and HTML are alternative representations of the same content, not two reports. Records phase transition and recovery impacts. |
| 015 | High but retrospective | Upton flooding | Resolve relative dates from the message date: “yesterday evening” = 27 Jan, “this morning” = 28 Jan, “tomorrow AM” = 29 Jan. Preserve evacuation start/end, observation and report-received times separately. |
| 016 | No extractable payload | Unknown | Store the message and raise a missing-attachment issue. Do not infer anything from `FYI` or “as per attached”. |

## Contradictions, qualifications and ambiguity

Contradictions must remain visible as relationships between immutable assertions. A “current state” view may rank them, but must never erase the losing report.

### A417 road status

- 001/007: closed in both directions between Ledbury and Gloucester Road junction at 07:00.
- 008: reopened “in both directions” at 14:00 after receding water.
- 009: at 15:20 the Gloucester Road junction remains closed; the council reopening applies only north of town. It also introduces a carriageway collapse.
- 013: still closed at the junction at 08:00 next day.

This is partly a contradiction and partly a spatial-scope correction. The system should represent road **segments**, not only a single A417 entity. Until the exact segment in 008 is resolved, its broad reopening claim conflicts with 009. The best-supported current state after 15:20 is “north section reopened; Gloucester Road junction closed”.

### Ledbury flooded-property count

- 001/007: 12 **residential properties confirmed flooded** at 07:00.
- 002: council observer estimates 18 or 19, including two shops.
- 003: 19 **confirmed properties**, said to align with the council.
- 013: 19 properties, unchanged.
- 014: 19 properties requiring recovery support; two businesses report uninsured losses.

The sequence is an evolution from 12 to 19, but definitions drift: residential only, all properties including shops, flooded, and requiring support are not identical measures. The system must retain measurement scope and wording rather than collapsing everything into one unqualified `property_count`.

### Ledbury evacuation and rest-centre occupancy

- 001/007: approximately 40 residents evacuated; Community Hall open, stated capacity 80.
- 003: evacuees rise to 65; the hall “reached capacity” at 10:15 and the rest centre relocated to St Michael's.
- 006: at 18:00 St Michael's occupancy 65/capacity 150; Community Hall closed, occupancy 0/capacity 80.
- 013: at 08:00 next day 41 residents remain at St Michael's.

This is a normal lifecycle, except “reached capacity” at 65 appears inconsistent with nominal capacity 80. It may reflect usable capacity, staffing, or people other than evacuees, but none is stated. Flag for review; do not silently alter either value. Also keep “evacuated people” distinct from “rest-centre occupants”.

### Upton rest-centre occupancy

- 006: Upton Memorial Hall occupancy 12 at 18:00 on 27 Jan.
- 015: caravan evacuation ran 18:30–21:15; 19 people evacuated, with one couple going to family, implying 17 went to the hall.
- 013: the hall has 12 residents at 08:00 on 28 Jan.

The 18:00 count precedes the caravan evacuation and is not contradictory. The next-morning count is lower than the reported 17 arrivals, which could reflect departures or incompatible counting. Since no movement report exists, mark this as an unresolved apparent contradiction rather than assuming a reason.

### Power restoration

- 011: 1,847 customers off supply at 20:30; estimated restoration 06:00 on 28 Jan, subject to water levels.
- 013: power restored at 05:45 to 1,847 customers.

These are consistent forecast and actual milestones. They supersede the outage state but do not prove that generators or the named welfare intervention were completed.

## Situation evolution

| Time | Material change |
|---|---|
| 27 Jan 04:30 | Leadon flood warning already in force. |
| 06:00–07:00 | Ledbury Community Hall opens; 12 residential properties flooded, ~40 evacuated, A417 closed. |
| 08:22 | Local observer estimates 18–19 Ledbury properties; reports separate Bromyard access disruption and Bishop's Frome alert. |
| 10:15–11:03 | Ledbury evacuees reach 65; rest centre moves to St Michael's; 19 properties confirmed. |
| 12:41–14:00 | Upton warning forecasts overnight peak; barriers due for deployment. A417 reopening is reported, later narrowed. |
| 15:20 | Police confirm Gloucester Road junction still closed and add B4216/Woodleigh Road closures. |
| 16:30–18:00 | Upton Memorial Hall opens; 12 occupants. Ledbury sites show the completed relocation. |
| 18:30–21:15 | Upton caravan park evacuated: 19 people, 17 reported to the hall. |
| 19:05–20:30 | Urgent oxygen-dependent resident case; Upton substation de-energised, affecting 1,847 customers and 46 PSR customers. |
| 28 Jan 02:10–08:00 | Severn peaks at 5.34m; power restored 05:45; 7 Upton properties flooded; Ledbury occupancy falls to 41. |
| 28 Jan 09:48 | Retrospective caravan report adds damage and reoccupation decision request. |
| 29 Jan 09:00–10:20 | Leadon response closes and recovery governance starts; Bromyard reopens. |
| 29 Jan 11:40 | Six-case possible GI cluster reported, with causal link still unconfirmed. |

## Relevance and data-quality findings

- **Directly relevant facts:** impacts, closures, occupancies, capacities, warning states, resource deployments, outages, forecasts, recovery phase and health surveillance.
- **Operationally relevant but not incident-state facts:** TCG/RCG meetings, next-update commitments, document embargoes, requests for decisions and unresolved actions.
- **Context only:** greetings, signatures, “shout if the format is a problem”, standard meeting agenda and meeting URL.
- **Duplicate representations:** 001/007 are semantic duplicate messages; 003 contains quoted 001 content; 014 has MIME alternatives; neither should multiply facts.
- **Missing evidence:** 016 claims a spreadsheet but contains no attachment. This is an ingestion/data-quality alert, not an empty successful report.
- **Uncertainty:** approximate counts, estimates, possible clusters, expected peaks, ETAs and conditional forecasts must retain modality and confidence.
- **Planned versus completed action:** barriers “are being deployed”, generators are “en route”, framework activation is “requested” and a grant is “expected”. None may be upgraded to completed/approved/available without later evidence.
- **Sensitive content:** 010 contains identifiable health/safeguarding data; 012 contains restricted public-health information. Both require access controls, audit, purpose limitation and shorter retention than ordinary incident facts.
- **Entity resolution:** `Ledburry`→Ledbury; `St Michael's Primary School` is both a closed school and later a rest centre; `Community Hall` in informal prose should resolve to Ledbury Community Hall only with incident/location context; road status requires segment-level entities.
- **Time resolution:** distinguish sent/received time, report effective time, observation time, event interval, forecast interval and deadline. Relative dates must be resolved but their original phrases retained.

## Consequences for system design

1. Incident assignment must be many-to-many and hierarchical, with provisional situations and non-incident signals.
2. Assertions must be immutable, source-spanned and attributable through forwarded, quoted and attached content.
3. “Current truth” is a derived view over supersession, qualification, temporal and contradiction links—not an overwritten row.
4. Counts require a metric definition, population, geography, status, unit and time; numeric equality alone does not make two claims equivalent.
5. Semantic duplicate detection is separate from ingestion idempotency: retain both source messages while preventing double-counted canonical assertions.
6. Human review is required for high-impact contradictions, ambiguous entity resolution, missing attachments, urgent actions and sensitive data.
