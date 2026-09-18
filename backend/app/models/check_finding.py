from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class CheckFinding(Base):
    __tablename__ = "check_findings"

    id = Column(Integer, primary_key=True)
    check_id = Column(Integer, ForeignKey("compliance_checks.id"), nullable=False)
    # "obligation" or "deadline" — which table source_id points into.
    kind = Column(String, nullable=False)
    source_id = Column(Integer, nullable=False)
    section_id = Column(Integer, nullable=True)
    # Snapshot of the requirement as it was checked. Re-processing the compliance
    # document replaces its obligation rows, and without this an old report would
    # silently change or lose its rows.
    requirement = Column(Text, nullable=False)
    verdict = Column(String, nullable=False)
    evidence = Column(Text, nullable=True)
    note = Column(Text, nullable=True)
    due_at = Column(DateTime, nullable=True)
    bucket = Column(String, nullable=True)

    check = relationship("ComplianceCheck", back_populates="findings")
