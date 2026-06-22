"""create agent run tables

Revision ID: 0001_create_agent_run_tables
Revises:
Create Date: 2026-06-21
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001_create_agent_run_tables"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agent_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workflow_version", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("orchestrator_agent", sa.String(length=128), nullable=True),
        sa.Column("plan_id", sa.String(length=128), nullable=True),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("plan_json", sa.JSON(), nullable=True),
        sa.Column("final_result_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_agent_runs_workflow_version",
        "agent_runs",
        ["workflow_version"],
    )
    op.create_index("ix_agent_runs_status", "agent_runs", ["status"])

    op.create_table(
        "agent_steps",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("step_number", sa.Integer(), nullable=False),
        sa.Column("agent_name", sa.String(length=128), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("tool_name", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("input_summary", sa.Text(), nullable=True),
        sa.Column("output_summary", sa.Text(), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("attempt_number", sa.Integer(), nullable=True),
        sa.Column("step_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_steps_run_id", "agent_steps", ["run_id"])
    op.create_index("ix_agent_steps_tool_name", "agent_steps", ["tool_name"])

    op.create_table(
        "agent_decisions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("decision_number", sa.Integer(), nullable=False),
        sa.Column("agent_name", sa.String(length=128), nullable=False),
        sa.Column("decision_type", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("next_agent", sa.String(length=128), nullable=True),
        sa.Column("attempt_number", sa.Integer(), nullable=True),
        sa.Column("feedback_issue_count", sa.Integer(), nullable=False),
        sa.Column("decision_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_decisions_run_id", "agent_decisions", ["run_id"])
    op.create_index(
        "ix_agent_decisions_decision_type",
        "agent_decisions",
        ["decision_type"],
    )

    op.create_table(
        "agent_attempts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("rewrite_suggestions_json", sa.JSON(), nullable=False),
        sa.Column("validation_issues_json", sa.JSON(), nullable=False),
        sa.Column("attempt_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_attempts_run_id", "agent_attempts", ["run_id"])


def downgrade() -> None:
    op.drop_index("ix_agent_attempts_run_id", table_name="agent_attempts")
    op.drop_table("agent_attempts")

    op.drop_index("ix_agent_decisions_decision_type", table_name="agent_decisions")
    op.drop_index("ix_agent_decisions_run_id", table_name="agent_decisions")
    op.drop_table("agent_decisions")

    op.drop_index("ix_agent_steps_tool_name", table_name="agent_steps")
    op.drop_index("ix_agent_steps_run_id", table_name="agent_steps")
    op.drop_table("agent_steps")

    op.drop_index("ix_agent_runs_status", table_name="agent_runs")
    op.drop_index("ix_agent_runs_workflow_version", table_name="agent_runs")
    op.drop_table("agent_runs")
