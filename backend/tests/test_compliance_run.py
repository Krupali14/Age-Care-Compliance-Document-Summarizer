from datetime import datetime
from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import CheckFinding, ComplianceCheck, Deadline, Document, Obligation, Section, User
from app.services.docling_parser import ParsedSection


def _db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _seed(db):
    user = User(email="a@b.com", hashed_password="h")
    db.add(user)
    db.flush()
    doc = Document(user_id=user.id, filename="policy.pdf", file_type="pdf", status="done")
    db.add(doc)
    db.flush()
    section = Section(document_id=doc.id, heading="Part 3", order_idx=0, page_ref=None, raw_text="x")
    db.add(section)
    db.flush()
    db.add(Obligation(document_id=doc.id, section_id=section.id, text="Notify the family", responsible_role="RN", priority="high"))
    db.add(Deadline(document_id=doc.id, section_id=section.id, description="Notify the Commission", due_date="within 24 hours of the incident", responsible_role="RN"))
    check = ComplianceCheck(document_id=doc.id, filename="case.pdf", file_type="pdf", status="pending")
    db.add(check)
    db.commit()
    return doc, check


def test_select_evidence_passes_a_short_case_study_whole():
    from app.services.compliance_check import select_evidence

    text = "The fall occurred at 3pm. The family was notified at 3:30pm."
    assert select_evidence("Notify the family", text) == text


def test_select_evidence_retrieves_passages_from_a_long_case_study():
    from app.services.compliance_check import MAX_WHOLE_EVIDENCE_CHARS, select_evidence

    needle = "The registered nurse notified the family at 3:30pm."
    filler = "\n\n".join(f"Routine observation entry number {i} recorded no change." for i in range(400))
    assert len(filler) > MAX_WHOLE_EVIDENCE_CHARS
    selected = select_evidence("notified the family", f"{filler}\n\n{needle}")
    assert needle in selected
    assert len(selected) < len(filler)


def test_run_check_stores_a_verdict_per_requirement_and_times_deadlines_from_the_incident():
    from app.services.compliance_check import CheckBatch, CheckVerdict, run_check

    db = _db()
    doc, check = _seed(db)
    check_id = check.id

    parsed = [ParsedSection(heading="Case study", order_idx=0, page_ref=None,
                            raw_text="The medication error occurred on 14 September 2026 at 3:10pm. The family was notified at 3:30pm.")]
    verdicts = CheckBatch(verdicts=[
        CheckVerdict(index=0, verdict="done", evidence="The family was notified at 3:30pm.", note="Notified within the hour."),
        CheckVerdict(index=1, verdict="not_done", evidence=None, note="No notification to the Commission is recorded."),
    ])
    fake_llm = MagicMock()
    fake_llm.with_structured_output.return_value.invoke.return_value = verdicts

    with patch("app.services.compliance_check.SessionLocal", return_value=db), \
         patch("app.services.compliance_check.parse_document", return_value=parsed), \
         patch("app.services.compliance_check.get_llm", return_value=fake_llm):
        run_check(check_id, "/tmp/case.pdf")

    stored = db.query(ComplianceCheck).filter_by(id=check_id).one()
    assert stored.status == "done"
    assert stored.incident_source == "stated"
    assert stored.incident_at == datetime(2026, 9, 14, 15, 10)

    findings = {f.kind: f for f in db.query(CheckFinding).filter_by(check_id=check_id)}
    assert findings["obligation"].verdict == "done"
    assert findings["deadline"].verdict == "not_done"
    # "within 24 hours of the incident", counted from 3:10pm on the 14th.
    assert findings["deadline"].due_at == datetime(2026, 9, 15, 15, 10)
    assert findings["deadline"].bucket in {"overdue", "within_24_hours", "within_7_days", "within_30_days", "later"}


def test_run_check_records_unclear_when_the_model_call_fails():
    from app.services.compliance_check import run_check

    db = _db()
    doc, check = _seed(db)
    check_id = check.id

    parsed = [ParsedSection(heading="Case study", order_idx=0, page_ref=None, raw_text="A resident fell on 14 September 2026.")]
    fake_llm = MagicMock()
    fake_llm.with_structured_output.return_value.invoke.side_effect = RuntimeError("provider down")

    with patch("app.services.compliance_check.SessionLocal", return_value=db), \
         patch("app.services.compliance_check.parse_document", return_value=parsed), \
         patch("app.services.compliance_check.get_llm", return_value=fake_llm):
        run_check(check_id, "/tmp/case.pdf")

    stored = db.query(ComplianceCheck).filter_by(id=check_id).one()
    assert stored.status == "done"
    assert {f.verdict for f in db.query(CheckFinding).filter_by(check_id=check_id)} == {"unclear"}


def test_select_evidence_bounds_a_long_case_study_with_no_paragraph_breaks():
    from app.services.compliance_check import MAX_WHOLE_EVIDENCE_CHARS, select_evidence

    needle = "The registered nurse notified the family at 3:30pm."
    filler = " ".join(f"Routine observation entry number {i} recorded no change." for i in range(400))
    text = f"{filler} {needle}"
    assert len(text) > MAX_WHOLE_EVIDENCE_CHARS
    assert "\n" not in text

    selected = select_evidence("notified the family", text)
    assert len(selected) <= MAX_WHOLE_EVIDENCE_CHARS
    assert needle in selected


def test_run_check_fails_the_check_when_something_breaks_mid_run():
    """A real, unmocked database failure inside the batch loop (a NOT NULL
    violation, not a patched-in RuntimeError) must still be recoverable — the
    session has to survive to record its own failure and remain usable after.

    `_verdicts_for` is patched rather than the LLM: with a requirement whose
    text is None, `_verdicts_for`'s own `" ".join(req.text ...)` raises first,
    before the database is ever touched, which would pass even without the fix
    this test exists to catch. Skipping straight to "no verdicts came back"
    reaches the actual NOT NULL violation on `CheckFinding.requirement`.
    """
    from app.services.compliance_check import Requirement, run_check

    db = _db()
    doc, check = _seed(db)
    check_id = check.id

    parsed = [ParsedSection(heading="Case study", order_idx=0, page_ref=None, raw_text="A resident fell on 14 September 2026.")]
    # A requirement with no text: CheckFinding.requirement is NOT NULL, so the
    # commit inside the batch loop raises IntegrityError — a genuinely broken
    # session, not a patched-in exception.
    broken_requirement = [Requirement("obligation", 1, None, None, None)]

    with patch("app.services.compliance_check.SessionLocal", return_value=db), \
         patch("app.services.compliance_check.parse_document", return_value=parsed), \
         patch("app.services.compliance_check._verdicts_for", return_value={}), \
         patch("app.services.compliance_check.load_requirements", return_value=broken_requirement):
        run_check(check_id, "/tmp/case.pdf")

    stored = db.query(ComplianceCheck).filter_by(id=check_id).one()
    assert stored.status == "failed"
    assert stored.error_message
    # The session itself must still be usable — this is what a missing
    # rollback before the recovery commit would have broken.
    assert db.query(ComplianceCheck).count() == 1


def test_run_check_leaves_out_of_range_indices_unclear():
    from app.services.compliance_check import CheckBatch, CheckVerdict, run_check

    db = _db()
    doc, check = _seed(db)
    check_id = check.id

    parsed = [ParsedSection(heading="Case study", order_idx=0, page_ref=None,
                            raw_text="A resident fell on 14 September 2026 at 3pm.")]
    # Only two requirements exist (index 0 and 1); index 7 cannot match either and
    # must be dropped rather than filed against a real requirement.
    verdicts = CheckBatch(verdicts=[
        CheckVerdict(index=7, verdict="done", evidence=None, note="Bogus index."),
    ])
    fake_llm = MagicMock()
    fake_llm.with_structured_output.return_value.invoke.return_value = verdicts

    with patch("app.services.compliance_check.SessionLocal", return_value=db), \
         patch("app.services.compliance_check.parse_document", return_value=parsed), \
         patch("app.services.compliance_check.get_llm", return_value=fake_llm):
        run_check(check_id, "/tmp/case.pdf")

    stored = db.query(ComplianceCheck).filter_by(id=check_id).one()
    assert stored.status == "done"
    findings = list(db.query(CheckFinding).filter_by(check_id=check_id))
    assert len(findings) == 2
    assert {f.verdict for f in findings} == {"unclear"}


def test_run_check_fails_the_check_when_the_case_study_cannot_be_parsed():
    from app.services.compliance_check import run_check

    db = _db()
    doc, check = _seed(db)
    check_id = check.id

    with patch("app.services.compliance_check.SessionLocal", return_value=db), \
         patch("app.services.compliance_check.parse_document", side_effect=RuntimeError("bad file")):
        run_check(check_id, "/tmp/case.pdf")

    stored = db.query(ComplianceCheck).filter_by(id=check_id).one()
    assert stored.status == "failed"
    assert "could not be read" in stored.error_message
