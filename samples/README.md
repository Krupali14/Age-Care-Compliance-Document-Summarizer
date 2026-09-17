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

The Kanangra Court escalation protocol states deadlines in minutes and hours — 30
minutes, 1 hour, 2 hours, 4 hours, 24 hours, "2 business days", and "30 days and 4
hours" — to give the urgency buckets something short-dated to sort.

What it actually demonstrates, verified across two re-extraction runs: two of
those timeframes ("within 4 hours" and "30 days and 4 hours") keep their relative
wording through extraction and resolve to a real due time of day in the Deadlines
tab. The rest don't. "Within 24 hours" and "within 2 business days" are collapsed
into a bare calendar date instead — the extraction model does this despite an
explicit prompt rule telling it to keep relative phrasing verbatim, so it isn't
something this sample can force. The four shortest timeframes (30 minutes, 1 hour,
2 hours, 4 hours) aren't extracted as deadlines at all; they show up under
Obligations, with no due time. This is a known, parked limitation — see
[14-known-limitations.md](../project-understanding/14-known-limitations.md) — not
a bug in this sample or something worth debugging from here.

The Compliance Check tab is unaffected by that gap: it judges the 30-minute/1-hour/
2-hour/4-hour requirements correctly from their Obligations text, with no due time
attached, alongside the deadlines that did resolve.

Its companion case study is the evidence document for the Compliance Check tab: it
states the incident time (14 September 2026, 3:10pm), records some escalation steps
as completed and leaves others outstanding, so a check against the protocol returns
a mix of done, not done and unclear verdicts.
