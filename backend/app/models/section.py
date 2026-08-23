from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class Section(Base):
    __tablename__ = "sections"

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    heading = Column(String, nullable=False)
    order_idx = Column(Integer, nullable=False)
    page_ref = Column(String, nullable=True)
    raw_text = Column(Text, nullable=False)

    document = relationship("Document", back_populates="sections")
