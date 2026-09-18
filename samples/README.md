# Sample documents

Six fictional aged-care compliance documents for demonstrating the summariser.

| Document | Provider | Pages |
| --- | --- | --- |
| Incident Management and Reportable Incidents Policy | Sunrise Grove Aged Care Services | 26 |
| Medication Management Policy and Procedure | Kanangra Court Aged Care | 26 |
| Infection Prevention and Control Policy | Riverbend Care Group | 26 |
| Complaints, Feedback and Open Disclosure Policy | Harbourview Residential Care | 25 |
| Restrictive Practices and Behaviour Support Policy | Marloo Gardens Aged Care | 25 |
| Food, Nutrition and Dining Experience Policy | Thornbury Aged Care Services | 25 |
| Incident Escalation Protocol | Kanangra Court Aged Care | 1 |
| Case study: medication error, Resident K | Kanangra Court Aged Care | 1 |

## These are not real documents

Every provider, facility, person, document ID and incident reference is invented. Each page
carries a `SAMPLE — fictional document for demonstration` marker in its footer, and each cover
page states the same in full. They are not records of any organisation and are not compliance
advice. The regulatory frameworks they cite (the Aged Care Act 2024, the Strengthened Aged Care
Quality Standards) are real, which is what makes them realistic to demonstrate against.

## Why they demo well

- **Every date is in the future.** Deadlines land between October 2026 and October 2028, so the
  deadline extraction shows live due dates rather than the stale ones a real archived document
  would produce.
- **Headings match the parser.** Numbered forms (`Part 3 Immediate response`, `4.2 When the
  provider becomes aware`) split cleanly into 76–84 sections per document, so findings link back
  to a real source section.
- **Each covers a different domain**, so obligations, risks and action items differ between them
  rather than repeating.
- **Roughly 10–11 model calls each**, processing in about 20 seconds per document.

Measured on the incident policy: 82 sections, 54 obligations, 15 deadlines, 5 risks, 6 action
items, 19.4 seconds, no past-dated deadlines.

## Hour-scale deadlines and the compliance check

The Kanangra Court escalation protocol states eight timeframes, from 30 minutes to
a 6-month recurring audit, to give the urgency buckets something short-dated to
sort. What it actually demonstrates, verified across two re-extraction runs, is
narrower than that list suggests — and the honest summary is: the resolution
machinery is exact once relative wording reaches it; what limits the demonstration
is which of the eight the extraction model keeps as deadlines, and in what form.

| Stated timeframe | Extracted as a deadline? | Due time shown |
|---|---|---|
| within 30 minutes of the incident | No — appears under Obligations | — |
| within 1 hour | No — appears under Obligations | — |
| within 2 hours | No — appears under Obligations | — |
| within 4 hours | No — appears under Obligations | — |
| within 24 hours | Yes, but collapsed to a bare calendar date | End of day only, no time |
| within 2 business days | Yes, but collapsed to a bare calendar date | End of day only, no time |
| within 30 days and 4 hours of the incident | Yes, relative wording intact | 14 October 2026, 19:10 |
| monthly for 6 months | Yes, relative wording intact | 13 March 2027, 15:10 |

Only the last two keep their relative phrasing through extraction and resolve to
a real time of day, anchored to the case study's stated incident time (14
September 2026, 3:10pm) — not to some fixed offset from upload. "Within 24 hours"
and "within 2 business days" are extracted but collapsed into a bare calendar date
instead, despite an explicit prompt rule telling the model to keep relative
phrasing verbatim; that isn't something this sample can force. The four shortest
timeframes aren't extracted as deadlines at all. None of this is a bug in
`app/services/deadlines.py` — give it relative text and it resolves it correctly
every time, minutes included; the gap is upstream, in which timeframes the
extraction model hands it as deadlines with relative wording preserved. It is a
known, parked limitation — see
[14-known-limitations.md](../project-understanding/14-known-limitations.md) — not
a bug in this sample or something worth debugging from here.

The Compliance Check tab is unaffected by that gap: it judges the six timeframes
that don't resolve to a due time (the four shortest, plus the two collapsed to a
bare date) correctly from their text regardless, alongside the two that do.

Its companion case study is the evidence document for the Compliance Check tab: it
states the incident time (14 September 2026, 3:10pm), records some escalation steps
as completed and leaves others outstanding, so a check against the protocol returns
a mix of done, not done and unclear verdicts.
