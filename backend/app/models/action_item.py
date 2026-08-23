from sqlalchemy import Column, ForeignKey, Integer, String, Text

from app.database import Base


class ActionItem(Base):
    __tablename__ = "action_items"

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    section_id = Column(Integer, ForeignKey("sections.id"), nullable=False)
    text = Column(Text, nullable=False)
    responsible_role = Column(String, nullable=True)
    timeframe = Column(String, nullable=True)
    priority = Column(String, nullable=True)
    source_section = Column(String, nullable=True)
