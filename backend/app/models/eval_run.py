from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String

from app.database import Base


class EvalRun(Base):
    __tablename__ = "eval_runs"

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    precision = Column(Float, nullable=False)
    recall = Column(Float, nullable=False)
    f1 = Column(Float, nullable=False)
    ground_truth_ref = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
