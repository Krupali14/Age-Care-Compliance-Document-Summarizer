from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import (
    User, Document, Section, Summary, Obligation, Risk, Deadline, ActionItem, EvalRun,
)


def test_models_create_and_relate():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    user = User(email="a@b.com", hashed_password="hash")
    db.add(user)
    db.flush()

    doc = Document(user_id=user.id, filename="policy.pdf", file_type="pdf", status="pending")
    db.add(doc)
    db.flush()

    section = Section(document_id=doc.id, heading="Section 1", order_idx=0, page_ref="1", raw_text="text")
    db.add(section)
    db.flush()

    db.add(Summary(document_id=doc.id, text="summary text", model_used="test-model"))
    db.add(Obligation(document_id=doc.id, section_id=section.id, text="must do X", responsible_role="Manager", priority="high"))
    db.add(Risk(document_id=doc.id, section_id=section.id, text="risk of Y", severity="medium"))
    db.add(Deadline(document_id=doc.id, section_id=section.id, description="submit report", due_date=None, responsible_role="Nurse"))
    db.add(ActionItem(document_id=doc.id, section_id=section.id, text="do Z", responsible_role="Manager", timeframe="30 days", priority="low", source_section="Section 1"))
    db.add(EvalRun(document_id=doc.id, precision=0.9, recall=0.8, f1=0.85, ground_truth_ref="gt_1.json"))
    db.commit()

    assert db.query(Document).filter_by(id=doc.id).first().status == "pending"
    assert db.query(Obligation).filter_by(document_id=doc.id).first().responsible_role == "Manager"
