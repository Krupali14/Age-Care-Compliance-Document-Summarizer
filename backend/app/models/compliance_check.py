from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class ComplianceCheck(Base):
    """One case-study document checked against one compliance document.

    The case study is deliberately not a Document row: it is evidence, it gets no
    extraction of its own, and it must not appear on the dashboard.
    """

    __tablename__ = "compliance_checks"

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    filename = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    status = Column(String, nullable=False, default="pending")
    error_message = Column(String, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    # When the incident the deadlines hang off actually happened, and whether the
    # case study said so or we fell back to the upload time.
    incident_at = Column(DateTime, nullable=True)
    incident_source = Column(String, nullable=True)
    evidence_text = Column(Text, nullable=True)

    findings = relationship(
        "CheckFinding", back_populates="check", cascade="all, delete-orphan"
    )
