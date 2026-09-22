# samples/generate_case_studies.py
"""Generate two case-study evidence documents for each sample policy.

A policy alone cannot demonstrate the Compliance Check tab: that tab needs a second
document — the organisation's own account of what it did — to judge the policy's
obligations and deadlines against. Each policy gets two, so both halves of the
verdict scale can be shown from the same requirements:

- Case study A: the provider largely followed the policy. Mostly "done", with a
  deliberate "partly" or two where something was late or incomplete.
- Case study B: the provider did not. "not_done" where the account contradicts the
  policy, "unclear" where it is simply silent.

Every case study states its incident date and time in its opening sentence, in the
"18 September 2026 at 6:40am" form `find_incident_datetime` reads, so relative
deadlines ("within 24 hours of the incident") resolve against the incident rather
than against the upload time.

Everything here is fictional: providers, residents, workers, document IDs and
incident references are all invented.

Run: python samples/generate_case_studies.py  (writes into samples/, or $SAMPLES_OUT)
"""

import os
import re
from pathlib import Path

from docx import Document

OUT = Path(os.environ.get("SAMPLES_OUT", Path(__file__).parent))
MARKER = "SAMPLE — fictional document for demonstration"

# (filename, blocks) where a block is (text, heading level) and level None is body
# text. Kept as data so the narrative reads next to the policy it answers.
CASE_STUDIES: list[tuple[str, list[tuple[str, int | None]]]] = []


def case(filename: str, title: str, blocks: list[tuple[str, int | None]]) -> None:
    CASE_STUDIES.append((filename, [(title, 0), (MARKER, None), *blocks]))


# --------------------------------------------------------------------------
# Sunrise Grove — Incident Management and Reportable Incidents Policy
# --------------------------------------------------------------------------

case(
    "Sunrise-Grove-Case-Study-A-Unwitnessed-Fall.docx",
    "Sunrise Grove Aged Care Services — Case study: unwitnessed fall, Resident M",
    [
        ("Incident summary", 1),
        ("The incident occurred on 18 September 2026 at 6:40am. Resident M was found on "
         "the floor beside her bed by a care worker commencing the morning round. The "
         "resident was conscious, reported pain in her right hip, and was later confirmed "
         "to have sustained a fractured neck of femur. The Facility Manager classified the "
         "incident as a Priority 1 reportable incident at 7:15am.", None),
        ("Immediate response", 1),
        ("The registered nurse attended at 6:44am, completed neurological and pain "
         "observations, and did not move the resident until the ambulance crew arrived at "
         "7:05am.", None),
        ("A registered nurse completed the post-fall clinical review and recorded it in the "
         "clinical record at 8:20am, including the resident's pre-fall mobility, footwear, "
         "medications and the state of the call bell.", None),
        ("Notifying the person and their supporters", 1),
        ("Resident M's son, her nominated representative, was telephoned at 7:30am and given "
         "an account of what was known at that time. A second call was made at 11:00am once "
         "the fracture was confirmed. Both calls are recorded in the incident record.", None),
        ("Notification to the Commission", 1),
        ("The Executive Director of Clinical Governance lodged the Priority 1 notification "
         "through the Commission's portal on 18 September 2026 at 2:05pm, approximately "
         "seven hours after the provider became aware of the incident. The portal reference "
         "is recorded in the incident record.", None),
        ("On 21 September 2026 the physiotherapy assessment identified a contributing "
         "equipment fault. Because this materially changed the picture given to the "
         "Commission, an amended notification was lodged the same day.", None),
        ("Open disclosure", 1),
        ("Open disclosure was commenced with Resident M and her son at 4:00pm on 18 "
         "September 2026. The discussion covered what happened, what was being done and "
         "what would change. A follow-up meeting is scheduled for 28 September 2026 and the "
         "process has not yet been completed.", None),
        ("Investigation and corrective actions", 1),
        ("A severity-rated investigation was opened on 18 September 2026 and allocated to "
         "the Quality and Risk Manager. Three corrective actions were recorded: replacement "
         "of the faulty bed rail mechanism, a night-shift environmental check added to the "
         "handover sheet, and a review of Resident M's night sedation by the prescriber.", None),
        ("Supporting the workers involved", 1),
        ("The care worker who found Resident M was offered support through the employee "
         "assistance program on the morning of the incident and was not stood down.", None),
        ("Outstanding at the time of writing", 1),
        ("Verification that the corrective actions have been effective has not yet been "
         "carried out; it is scheduled once the actions are closed.", None),
    ],
)

case(
    "Sunrise-Grove-Case-Study-B-Unexplained-Bruising.docx",
    "Sunrise Grove Aged Care Services — Case study: unexplained bruising, Resident T",
    [
        ("Incident summary", 1),
        ("The incident was discovered on 12 September 2026 at 7:20pm. Extensive bruising to "
         "Resident T's upper arms was noticed by an agency care worker during the evening "
         "personal care round. Resident T lives with advanced dementia and could not account "
         "for the bruising. The worker recorded a progress note and told the registered nurse "
         "at the end of her shift.", None),
        ("Initial handling", 1),
        ("No clinical review of the bruising was documented on 12 September. The first entry "
         "describing the injury in the clinical record was made on 13 September 2026 at "
         "10:40am by the day-shift registered nurse.", None),
        ("Classification", 1),
        ("The Facility Manager discussed the bruising with the Executive Director of Clinical "
         "Governance on 14 September 2026 and recorded that it was “likely a manual "
         "handling mark”. The incident was logged as non-reportable. No consultation with "
         "the resident's representative informed that decision.", None),
        ("Notifying the person and their supporters", 1),
        ("Resident T's daughter was informed on 14 September 2026 at 5:15pm, two days after "
         "the bruising was discovered.", None),
        ("Notification to the Commission", 1),
        ("No notification has been made to the Aged Care Quality and Safety Commission. The "
         "Facility Manager's note records that advice is being sought on whether the "
         "bruising meets the reportable threshold for unreasonable use of force.", None),
        ("Open disclosure", 1),
        ("Open disclosure has not been commenced. The incident record contains no plan for "
         "it and no date.", None),
        ("Workers involved", 1),
        ("The agency care worker who had provided personal care on the preceding shift was "
         "told by telephone on 13 September 2026 not to attend further shifts pending "
         "inquiry. Nothing was given to her in writing, and no expected duration was "
         "stated.", None),
        ("Investigation", 1),
        ("No investigation has been allocated and no corrective actions have been recorded. "
         "The incident remains open in the register with no owner.", None),
    ],
)

# --------------------------------------------------------------------------
# Kanangra Court — Medication Management Policy and Procedure
# --------------------------------------------------------------------------

case(
    "Kanangra-Court-Case-Study-A-Missed-Anticoagulant-Dose.docx",
    "Kanangra Court Aged Care — Case study: missed anticoagulant dose, Resident P",
    [
        ("Incident summary", 1),
        ("The medication error occurred on 19 September 2026 at 8:15am. Resident P's morning "
         "anticoagulant dose was not administered during the morning round; the omission was "
         "identified at the second-check reconciliation at 8:15am by the registered nurse "
         "completing the round.", None),
        ("Immediate response", 1),
        ("The registered nurse assessed Resident P at 8:20am, recorded observations and "
         "checked for signs of bleeding or clotting. The assessment was entered in the "
         "clinical record at 8:35am.", None),
        ("The prescriber was telephoned at 8:40am and gave a verbal order to administer the "
         "dose late, with an instruction to monitor INR the following morning. The verbal "
         "order was taken by a registered nurse, read back, and entered on the chart with "
         "the time and both names.", None),
        ("The written confirmation of the verbal order was received from the prescriber and "
         "filed on 19 September 2026 at 4:50pm, and the prescriber signed the chart the same "
         "afternoon.", None),
        ("Recording the incident", 1),
        ("The medication incident was recorded in the incident system at 9:05am on 19 "
         "September 2026, identifying the medicine, the resident, the round, the staff "
         "member and the contributing factor — an interrupted round caused by a call bell "
         "in an adjoining room.", None),
        ("Notification and disclosure", 1),
        ("The Director of Nursing was notified at 8:45am. Resident P's nominated "
         "representative was telephoned at 10:15am and told what had happened and what was "
         "being monitored.", None),
        ("Review", 1),
        ("A Residential Medication Management Review referral was made for Resident P on 22 "
         "September 2026. Resident P is not prescribed a psychotropic medicine and no "
         "chemical restraint question arises.", None),
        ("Schedule 8 medicines were not involved in this incident; the Schedule 8 register "
         "count at the shift change on 19 September 2026 was completed and signed by two "
         "registered nurses with no discrepancy.", None),
        ("Outstanding at the time of writing", 1),
        ("The competency reassessment of the registered nurse involved has been requested "
         "but not yet scheduled. The monthly medication administration audit for September "
         "has not yet been run.", None),
    ],
)

case(
    "Kanangra-Court-Case-Study-B-Wrong-Resident-Dose.docx",
    "Kanangra Court Aged Care — Case study: wrong-resident administration, Wing C",
    [
        ("Incident summary", 1),
        ("The medication error occurred on 16 September 2026 at 5:40pm. A resident in Wing C "
         "was administered an evening dose charted for a different resident with a similar "
         "surname. The error was identified by a second registered nurse at 6:10pm during "
         "the following administration.", None),
        ("Immediate response", 1),
        ("The resident was observed at the nurses' station for the remainder of the evening. "
         "No clinical assessment was documented and no observations were recorded in the "
         "clinical record.", None),
        ("The prescriber was not contacted on 16 September. A note on the handover sheet "
         "records an intention to “raise it at the next visit”.", None),
        ("Charting and orders", 1),
        ("A verbal order taken on 14 September 2026 for the same resident remained unsigned "
         "by the prescriber at the time of writing, two days beyond the point at which the "
         "Director of Nursing is to be notified. The medicine continued to be "
         "administered.", None),
        ("Two entries on the resident's chart record no indication for the medicine "
         "charted.", None),
        ("Schedule 8 medicines", 1),
        ("The Schedule 8 register count at the shift change on 16 September 2026 showed a "
         "discrepancy of one tablet. The discrepancy was written in the register and the "
         "count repeated the following morning. It was not reported to the Director of "
         "Nursing, and no report has been made to police or to the Commission.", None),
        ("Dose forms and covert administration", 1),
        ("The resident's evening tablets have been crushed and given in yoghurt since 10 "
         "September 2026. The record does not show a pharmacist or prescriber authorisation "
         "for altering the dose form, and there is no documented consent or decision-making "
         "process for covert administration.", None),
        ("Psychotropic medicines", 1),
        ("A psychotropic medicine was commenced on 15 September 2026 following a period of "
         "calling out at night. The record does not describe any non-pharmacological "
         "approaches tried before it was prescribed.", None),
        ("Recording and follow-up", 1),
        ("The incident was entered in the incident system on 18 September 2026, two days "
         "after it occurred. No corrective actions have been recorded.", None),
    ],
)

# --------------------------------------------------------------------------
# Riverbend Care Group — Infection Prevention and Control Policy
# --------------------------------------------------------------------------

case(
    "Riverbend-Case-Study-A-Gastroenteritis-Outbreak.docx",
    "Riverbend Care Group — Case study: gastroenteritis outbreak, Wattle wing",
    [
        ("Incident summary", 1),
        ("The outbreak was identified on 20 September 2026 at 7:30am, when a third person in "
         "Wattle wing was found to have vomiting and diarrhoea. Two people in the same area "
         "had developed the same symptoms within the preceding 24 hours, meeting the "
         "outbreak threshold in the policy.", None),
        ("Immediate response", 1),
        ("The registered nurse in charge commenced contact and enteric precautions on "
         "clinical suspicion at 7:35am, without waiting for a pathology result and without a "
         "medical order.", None),
        ("The Infection Prevention and Control Lead was notified at 9:10am, within four "
         "hours of precautions being commenced.", None),
        ("Outbreak management", 1),
        ("The outbreak was declared and an outbreak register opened at 9:30am on 20 "
         "September 2026. Faecal specimens were collected from the three affected people the "
         "same morning. The Public Health Unit was notified at 10:05am.", None),
        ("Cleaning frequency in Wattle wing was increased to twice daily with a "
         "chlorine-based product, and shared equipment was allocated to the affected "
         "rooms.", None),
        ("Visiting and isolation", 1),
        ("Visiting was not suspended. Visitors to Wattle wing were met at the entrance, given "
         "personal protective equipment and instructed in its use. Affected residents were "
         "supported with daily contact from the lifestyle team to reduce the harm of "
         "isolation, recorded in each clinical record.", None),
        ("Antimicrobials", 1),
        ("One person was commenced on an antimicrobial on 21 September 2026 after a clinical "
         "assessment recorded the indication and the specimen result pending. The "
         "antimicrobial was reviewed against the culture result at 60 hours.", None),
        ("Worker health and immunisation", 1),
        ("Two care workers reported vomiting on 20 September 2026 and were excluded from the "
         "workplace; both returned 48 hours after their symptoms resolved. Influenza "
         "vaccination coverage for the wing's workers was recorded as 96 per cent at the "
         "last audit.", None),
        ("Outstanding at the time of writing", 1),
        ("The outbreak debrief has been scheduled for 30 September 2026 and has not yet "
         "taken place. Hand hygiene compliance for September has not yet been audited by "
         "direct observation.", None),
    ],
)

case(
    "Riverbend-Case-Study-B-Sharps-Injury-and-Cluster.docx",
    "Riverbend Care Group — Case study: sharps injury and respiratory cluster, Banksia wing",
    [
        ("Incident summary", 1),
        ("The sharps injury occurred on 15 September 2026 at 10:10pm, when a registered nurse "
         "sustained a needlestick injury while recapping a needle after an insulin "
         "administration in Banksia wing.", None),
        ("Response to the sharps injury", 1),
        ("The injury was recorded on the staff incident form at the end of the shift. The "
         "worker was assessed by a general practitioner at 11:00am the following morning, "
         "approximately thirteen hours after the injury.", None),
        ("Post-exposure prophylaxis was not commenced. The record states that the decision "
         "was deferred until source testing results were available, which were received on "
         "18 September 2026.", None),
        ("The Infection Prevention and Control Lead was made aware of the injury on 17 "
         "September 2026, when the incident forms were collected for the weekly review.", None),
        ("Respiratory symptoms in the same wing", 1),
        ("Between 16 and 18 September 2026, three people in Banksia wing developed cough and "
         "fever. Each was managed in their room. No outbreak was declared, no outbreak "
         "register was opened and the Public Health Unit was not notified.", None),
        ("Transmission-based precautions were commenced for one of the three people on 18 "
         "September 2026, after a positive point-of-care test. The record does not show "
         "precautions being applied to the other two.", None),
        ("Worker health", 1),
        ("A care worker who reported a fever on 17 September 2026 completed her rostered "
         "shift that day and worked a further shift on 18 September 2026.", None),
        ("Antimicrobials", 1),
        ("Two people were commenced on antimicrobials on 17 September 2026. Neither entry "
         "records an indication, and no review against a culture result appears in either "
         "record.", None),
        ("Environment and review", 1),
        ("Cleaning frequency was not increased. No debrief has been held and no corrective "
         "actions have been recorded.", None),
    ],
)

# --------------------------------------------------------------------------
# Harbourview Residential Care — Complaints, Feedback and Open Disclosure Policy
# --------------------------------------------------------------------------

case(
    "Harbourview-Case-Study-A-Call-Bell-Complaint.docx",
    "Harbourview Residential Care — Case study: complaint about night call bell response",
    [
        ("Incident summary", 1),
        ("The complaint was received on 17 September 2026 at 9:05am, when the daughter of a "
         "resident in Cedar wing telephoned to say that her mother had waited more than "
         "forty minutes for a call bell to be answered on two consecutive nights.", None),
        ("Acknowledgement and triage", 1),
        ("The complaint was logged in the complaints register at 9:20am and acknowledged in "
         "writing to the complainant at 2:40pm the same day.", None),
        ("A risk screen for abuse and neglect was completed on receipt and recorded in the "
         "triage record. The complaint was assessed as Tier 2 and allocated to the Head of "
         "Consumer Experience.", None),
        ("Support to complain", 1),
        ("The complainant was told in the acknowledgement letter that she may complain to "
         "the Aged Care Quality and Safety Commission at any time, and that doing so would "
         "not affect her mother's care. An accredited interpreter was offered and "
         "declined.", None),
        ("Handling and communication", 1),
        ("The complainant was given a named contact and was updated by telephone on 21 and 25 "
         "September 2026. Call bell response data for Cedar wing for the preceding fortnight "
         "was extracted and reviewed with the night roster.", None),
        ("Outcome", 1),
        ("A written outcome was sent on 29 September 2026, within the Tier 2 timeframe. It "
         "set out what was found, what would change — an additional night-shift care "
         "worker in Cedar wing from 5 October 2026 — and the complainant's right to seek "
         "an internal review within 30 days or to complain externally.", None),
        ("Learning from the complaint", 1),
        ("The complaint was coded to “responsiveness of staff” in the complaints "
         "register and included in the monthly trend analysis. The rostering change was "
         "entered in the continuous improvement register and published in the October "
         "resident newsletter.", None),
        ("Outstanding at the time of writing", 1),
        ("The Consumer Advisory Body has not yet reviewed the de-identified complaint; its "
         "next meeting is in October 2026.", None),
    ],
)

case(
    "Harbourview-Case-Study-B-Anonymous-Conduct-Complaint.docx",
    "Harbourview Residential Care — Case study: anonymous complaint about worker conduct",
    [
        ("Incident summary", 1),
        ("The complaint was received on 8 September 2026 at 2:30pm, in an unsigned note "
         "placed in the feedback box at the main entrance. The note alleged that a care "
         "worker spoke roughly to residents in Fig wing during the evening shift and that "
         "one resident had been left in a chair after asking to go to bed.", None),
        ("Acknowledgement and triage", 1),
        ("The note was passed to the Head of Consumer Experience and entered in the "
         "complaints register on 12 September 2026, four days after it was received.", None),
        ("The triage record contains no risk screen for abuse and neglect. The complaint was "
         "recorded as “feedback — no action possible, anonymous”.", None),
        ("Handling", 1),
        ("No investigation of the allegation was commenced. The register entry states that "
         "the complaint could not be progressed because the complainant could not be "
         "contacted.", None),
        ("On 15 September 2026 a resident in Fig wing raised the same concern verbally with "
         "a care worker. The discussion was held through the resident's son, who "
         "interpreted, because no accredited interpreter was arranged. The discussion was "
         "not repeated with an accredited interpreter.", None),
        ("Outcome and communication", 1),
        ("No written outcome was produced. The resident who raised the concern verbally was "
         "told the matter “would be looked at” and received nothing further.", None),
        ("The resident was not told that she may complain to the Aged Care Quality and "
         "Safety Commission, and no internal review was offered.", None),
        ("Records and learning", 1),
        ("The complaint is not coded to a category in the complaints register and does not "
         "appear in the September trend analysis. Nothing has been entered in the continuous "
         "improvement register.", None),
    ],
)

# --------------------------------------------------------------------------
# Marloo Gardens — Restrictive Practices and Behaviour Support Policy
# --------------------------------------------------------------------------

case(
    "Marloo-Gardens-Case-Study-A-Emergency-Physical-Restraint.docx",
    "Marloo Gardens Aged Care — Case study: emergency physical restraint, Resident B",
    [
        ("Incident summary", 1),
        ("The incident occurred on 21 September 2026 at 8:15pm. Resident B, who lives with "
         "dementia, attempted to leave the building through a fire exit and physically "
         "resisted redirection. Two workers held Resident B's arms for approximately ninety "
         "seconds to prevent him from falling down the external stairs.", None),
        ("Immediate response", 1),
        ("The registered nurse in charge was notified immediately and attended at 8:17pm. "
         "Resident B was supported back to the lounge, offered a drink and settled without "
         "further intervention.", None),
        ("Resident B's son, his substitute decision-maker, was telephoned at 9:40pm on 21 "
         "September 2026 and told what had happened, why, and for how long the hold "
         "lasted.", None),
        ("The use was recorded as a reportable incident and notified through the incident "
         "process on 21 September 2026 at 10:05pm.", None),
        ("Assessment for reversible causes", 1),
        ("A registered nurse completed an assessment for reversible causes on 22 September "
         "2026, including a pain assessment using a validated observational tool, a "
         "urinalysis and a review of the evening routine. Untreated hip pain was identified "
         "and analgesia was charted by the prescriber the same day.", None),
        ("Behaviour support planning", 1),
        ("Resident B's behaviour support plan was reviewed and updated on 24 September 2026, "
         "three days after the emergency use, recording the trigger identified, the "
         "alternatives that worked on the night, and the strategies to be used first in "
         "future.", None),
        ("Authorisation and consent", 1),
        ("No ongoing restrictive practice is in use. Informed consent for the updated plan "
         "was obtained from Resident B's son and recorded on 24 September 2026, with the "
         "alternatives tried and their outcomes set out in the record.", None),
        ("Monitoring and review", 1),
        ("Observations were recorded during and after the hold, including respiratory rate, "
         "skin integrity and distress. A review of the plan is scheduled within three "
         "months, on 20 December 2026.", None),
        ("Outstanding at the time of writing", 1),
        ("The elimination plan has been drafted but not yet endorsed by the Clinical "
         "Governance Committee.", None),
    ],
)

case(
    "Marloo-Gardens-Case-Study-B-Psychotropic-Without-Authorisation.docx",
    "Marloo Gardens Aged Care — Case study: psychotropic commenced after night calling, Resident W",
    [
        ("Incident summary", 1),
        ("The practice commenced on 10 September 2026 at 9:50pm, when a psychotropic medicine "
         "was administered to Resident W to settle repeated calling out at night. The "
         "medicine had been charted that afternoon following a telephone call to the "
         "prescriber by the evening registered nurse.", None),
        ("Assessment before use", 1),
        ("The clinical record contains no assessment for reversible causes before the "
         "medicine was charted. No pain assessment was completed, and there is no record of "
         "infection being excluded.", None),
        ("The record does not describe any non-pharmacological strategies tried before the "
         "medicine was used.", None),
        ("Authorisation and consent", 1),
        ("The restrictive practices register does not contain an authorisation for this use. "
         "Resident W's daughter, her substitute decision-maker, was not asked for informed "
         "consent before the medicine was administered, and no consent has been recorded "
         "since.", None),
        ("The authorisation form in the record is blank in the sections requiring the "
         "specific practice, the circumstances of use, the duration and the least "
         "restrictive alternatives considered.", None),
        ("Reporting", 1),
        ("The use has not been recorded as a reportable incident, and the substitute "
         "decision-maker has not been notified at the time of writing, sixteen days after "
         "the medicine was first administered.", None),
        ("Monitoring during use", 1),
        ("The medicine has been administered nightly since 10 September 2026. No monitoring "
         "observations have been recorded on any night, and the behaviour support plan has "
         "not been updated.", None),
        ("Secure unit", 1),
        ("Resident W was moved into the secure unit on 13 September 2026. The record contains "
         "no documented assessment supporting entry and no consent from the substitute "
         "decision-maker.", None),
        ("Review", 1),
        ("No review of the practice has been scheduled, and the prevalence of chemical "
         "restraint for September has not been reported to the Clinical Governance "
         "Committee.", None),
    ],
)

# --------------------------------------------------------------------------
# Thornbury Aged Care Services — Food, Nutrition and Dining Experience Policy
# --------------------------------------------------------------------------

case(
    "Thornbury-Case-Study-A-Unplanned-Weight-Loss.docx",
    "Thornbury Aged Care Services — Case study: unplanned weight loss, Resident D",
    [
        ("Incident summary", 1),
        ("The weight loss was identified on 14 September 2026 at 9:00am, when Resident D's "
         "monthly weight was recorded and showed a loss of 3.4 kilograms, approximately five "
         "per cent of body weight, over the preceding month.", None),
        ("Screening and monitoring", 1),
        ("Resident D entered care on 2 September 2026. A validated malnutrition screen was "
         "completed by a registered nurse on 5 September 2026, three days after entry, and "
         "filed in the clinical record.", None),
        ("Weights have been recorded monthly since entry, and weekly from 14 September 2026 "
         "once the loss was identified.", None),
        ("Response to the weight loss", 1),
        ("A dietitian referral was made on 16 September 2026, two days after the loss was "
         "identified. The dietitian reviewed Resident D on 21 September 2026 and recommended "
         "fortified meals and a mid-morning supplement.", None),
        ("Food and fluid charting was commenced on 14 September 2026 and has been completed "
         "at every meal since.", None),
        ("Texture and assistance", 1),
        ("Resident D is on a minced and moist diet following a speech pathology assessment on "
         "8 September 2026. The texture level is recorded on the meal service sheet, the "
         "kitchen ticket and above the bed.", None),
        ("Resident D requires assistance to eat and is supported by a named care worker who "
         "sits at eye level for the whole meal, recorded in the care plan.", None),
        ("Dining experience", 1),
        ("Protected mealtimes were observed for all three meals on 14 September 2026; no "
         "non-urgent clinical rounds or medication rounds took place during service.", None),
        ("Food safety", 1),
        ("Hot food temperatures were logged at every service in September and were at or "
         "above the required temperature. The cooling log for 14 September 2026 records the "
         "soup passing from 60 to 21 degrees in 90 minutes and from 21 to 5 degrees in a "
         "further three hours.", None),
        ("Outstanding at the time of writing", 1),
        ("The resident food focus group has not met since July 2026 and the next meeting has "
         "not been scheduled.", None),
    ],
)

case(
    "Thornbury-Case-Study-B-Wrong-Texture-Served.docx",
    "Thornbury Aged Care Services — Case study: wrong texture served at lunch, Resident F",
    [
        ("Incident summary", 1),
        ("The incident occurred on 19 September 2026 at 12:25pm, when Resident F, who is "
         "prescribed a minced and moist diet, was served and began eating a regular-texture "
         "lunch in the main dining room. A care worker noticed after several mouthfuls and "
         "removed the meal.", None),
        ("Immediate response", 1),
        ("The registered nurse in charge was told at 1:05pm, about forty minutes after the "
         "error was noticed. Resident F coughed during the meal but no respiratory "
         "observations were recorded.", None),
        ("The incident was not entered into the incident system. It appears only as a line "
         "in the kitchen communication book.", None),
        ("Texture records", 1),
        ("Resident F's texture level was not recorded on the meal service sheet for 19 "
         "September 2026. The speech pathology recommendation in the clinical record is "
         "dated March 2026 and has not been reviewed since.", None),
        ("Screening and monitoring", 1),
        ("Resident F entered care on 1 September 2026. No validated malnutrition screen "
         "appears in the clinical record at the time of writing, eighteen days after "
         "entry.", None),
        ("A weight loss of 2.9 kilograms was recorded on 12 September 2026. No dietitian "
         "referral has been made.", None),
        ("Food safety", 1),
        ("The cooling log for the week of 14 September 2026 has no entries for three of seven "
         "days. A food recall notice published on 15 September 2026 was actioned on 18 "
         "September 2026, when the affected stock was removed.", None),
        ("Food brought in by the family", 1),
        ("A container of home-cooked food was left by Resident F's family at the nurses' "
         "station at about 11:00am on 19 September 2026 and was placed in the refrigerator "
         "after the lunch service, around 2:00pm. It carried no name and no date.", None),
        ("Dining experience", 1),
        ("The medication round ran through the lunch service on 19 September 2026. Two "
         "residents requiring assistance began eating after the others had finished.", None),
        ("Follow-up", 1),
        ("No corrective actions have been recorded, and Resident F's representative has not "
         "been informed of the texture error.", None),
    ],
)


# The form `find_incident_datetime` needs in order to anchor relative deadlines on
# the incident: a calendar date and a clock time, in the sentence that names the
# event. A case study that loses it silently falls back to the upload time, and the
# Compliance Check report then shows due times that mean nothing.
_INCIDENT_STATED = re.compile(r"\bon \d{1,2} [A-Z][a-z]+ 20\d{2} at \d{1,2}:\d{2}(am|pm)\b")


def _check() -> None:
    """Every case study opens by saying when the incident happened."""
    for filename, blocks in CASE_STUDIES:
        opening = blocks[3][0]
        assert _INCIDENT_STATED.search(opening), f"{filename}: no stated incident date and time"
    print(f"{len(CASE_STUDIES)} case studies state an incident date and time")


def _write(blocks: list[tuple[str, int | None]], path: Path) -> None:
    doc = Document()
    for text, level in blocks:
        if level is None:
            doc.add_paragraph(text)
        else:
            doc.add_heading(text, level=level)
    doc.save(path)
    print(f"wrote {path}")


if __name__ == "__main__":
    _check()
    for filename, blocks in CASE_STUDIES:
        _write(blocks, OUT / filename)
    print(f"{len(CASE_STUDIES)} case studies written to {OUT}")
