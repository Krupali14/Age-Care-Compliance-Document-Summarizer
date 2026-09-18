"""compliance checks

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "compliance_checks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("file_type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(), nullable=True),
        sa.Column("incident_at", sa.DateTime(), nullable=True),
        sa.Column("incident_source", sa.String(), nullable=True),
        sa.Column("evidence_text", sa.Text(), nullable=True),
    )
    op.create_index("ix_compliance_checks_document_id", "compliance_checks", ["document_id"])

    op.create_table(
        "check_findings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("check_id", sa.Integer(), sa.ForeignKey("compliance_checks.id"), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("section_id", sa.Integer(), nullable=True),
        sa.Column("requirement", sa.Text(), nullable=False),
        sa.Column("verdict", sa.String(), nullable=False),
        sa.Column("evidence", sa.Text(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("due_at", sa.DateTime(), nullable=True),
        sa.Column("bucket", sa.String(), nullable=True),
    )
    op.create_index("ix_check_findings_check_id", "check_findings", ["check_id"])


def downgrade() -> None:
    op.drop_index("ix_check_findings_check_id", table_name="check_findings")
    op.drop_table("check_findings")
    op.drop_index("ix_compliance_checks_document_id", table_name="compliance_checks")
    op.drop_table("compliance_checks")
