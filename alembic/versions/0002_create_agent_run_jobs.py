"""create agent run jobs

Revision ID: 0002_create_agent_run_jobs
Revises: 0001_create_agent_run_tables
Create Date: 2026-06-21
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_create_agent_run_jobs"
down_revision: str | None = "0001_create_agent_run_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agent_run_jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("rq_job_id", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("request_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_run_jobs_status", "agent_run_jobs", ["status"])
    op.create_index("ix_agent_run_jobs_run_id", "agent_run_jobs", ["run_id"])
    op.create_index("ix_agent_run_jobs_rq_job_id", "agent_run_jobs", ["rq_job_id"])


def downgrade() -> None:
    op.drop_index("ix_agent_run_jobs_rq_job_id", table_name="agent_run_jobs")
    op.drop_index("ix_agent_run_jobs_run_id", table_name="agent_run_jobs")
    op.drop_index("ix_agent_run_jobs_status", table_name="agent_run_jobs")
    op.drop_table("agent_run_jobs")
