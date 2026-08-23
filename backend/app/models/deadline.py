from sqlalchemy import Column, ForeignKey, Integer, String, Text

from app.database import Base


class Deadline(Base):
    __tablename__ = "deadlines"

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    section_id = Column(Integer, ForeignKey("sections.id"), nullable=False)
    description = Column(Text, nullable=False)
    due_date = Column(String, nullable=True)
    responsible_role = Column(String, nullable=True)
