from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import CheckFinding, ComplianceCheck, Document, User


def test_a_check_cascades_its_findings_when_deleted():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()

    user = User(email="a@b.com", hashed_password="h")
    db.add(user)
    db.flush()
    doc = Document(user_id=user.id, filename="policy.pdf", file_type="pdf", status="done")
    db.add(doc)
    db.flush()
    check = ComplianceCheck(
        document_id=doc.id,
        filename="case.pdf",
        file_type="pdf",
        status="done",
        incident_at=datetime(2026, 9, 14, 15, 10),
        incident_source="stated",
        evidence_text="The fall occurred at 3:10pm.",
    )
    db.add(check)
    db.flush()
    db.add(CheckFinding(
        check_id=check.id, kind="deadline", source_id=1, section_id=None,
        requirement="Notify the Commission", verdict="not_done",
        evidence=None, note="The case study records no notification.",
        due_at=datetime(2026, 9, 15, 15, 10), bucket="overdue",
    ))
    db.commit()

    assert len(check.findings) == 1
    db.delete(check)
    db.commit()
    assert db.query(CheckFinding).count() == 0
