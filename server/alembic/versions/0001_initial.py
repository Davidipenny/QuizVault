"""Explicit QuizVault v2 baseline schema.

Revision ID: 0001
"""
from alembic import op
import sqlalchemy as sa


revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("workspaces", sa.Column("id", sa.String(36), primary_key=True), sa.Column("name", sa.String(120), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("users", sa.Column("id", sa.String(36), primary_key=True), sa.Column("workspace_id", sa.String(36), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False), sa.Column("display_name", sa.String(120), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_users_workspace_id", "users", ["workspace_id"])
    op.create_table("question_banks", sa.Column("id", sa.String(36), primary_key=True), sa.Column("workspace_id", sa.String(36), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False), sa.Column("name", sa.String(200), nullable=False), sa.Column("description", sa.Text(), nullable=False), sa.Column("tags", sa.JSON(), nullable=False), sa.Column("challenge_size", sa.Integer(), nullable=False), sa.Column("version", sa.Integer(), nullable=False), sa.Column("archived", sa.Boolean(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("workspace_id", "name", name="uq_bank_workspace_name"))
    op.create_index("ix_question_banks_workspace_id", "question_banks", ["workspace_id"])
    op.create_table("questions", sa.Column("id", sa.String(36), primary_key=True), sa.Column("bank_id", sa.String(36), sa.ForeignKey("question_banks.id", ondelete="CASCADE"), nullable=False), sa.Column("type", sa.String(20), nullable=False), sa.Column("prompt", sa.Text(), nullable=False), sa.Column("case_material", sa.Text(), nullable=False), sa.Column("explanation", sa.Text(), nullable=False), sa.Column("source", sa.String(500), nullable=False), sa.Column("sort_order", sa.Integer(), nullable=False), sa.Column("answer_spec", sa.JSON(), nullable=False), sa.Column("fingerprint", sa.String(64), nullable=False), sa.Column("version", sa.Integer(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("bank_id", "fingerprint", name="uq_question_bank_fingerprint"))
    for name, columns in (("ix_questions_bank_id", ["bank_id"]), ("ix_questions_type", ["type"]), ("ix_questions_fingerprint", ["fingerprint"])):
        op.create_index(name, "questions", columns)
    op.create_table("choices", sa.Column("id", sa.String(36), primary_key=True), sa.Column("question_id", sa.String(36), sa.ForeignKey("questions.id", ondelete="CASCADE"), nullable=False), sa.Column("label", sa.String(12), nullable=False), sa.Column("content", sa.Text(), nullable=False), sa.Column("is_correct", sa.Boolean(), nullable=False), sa.Column("display_order", sa.Integer(), nullable=False))
    op.create_index("ix_choices_question_id", "choices", ["question_id"])
    op.create_table("study_states", sa.Column("id", sa.String(36), primary_key=True), sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("question_id", sa.String(36), sa.ForeignKey("questions.id", ondelete="CASCADE"), nullable=False), sa.Column("wrong_count", sa.Integer(), nullable=False), sa.Column("favorite", sa.Boolean(), nullable=False), sa.Column("note", sa.Text(), nullable=False), sa.Column("flagged", sa.Boolean(), nullable=False), sa.Column("last_answered_at", sa.DateTime(timezone=True)), sa.Column("mastery", sa.String(20), nullable=False), sa.UniqueConstraint("user_id", "question_id", name="uq_state_user_question"))
    op.create_index("ix_study_states_user_id", "study_states", ["user_id"])
    op.create_index("ix_study_states_question_id", "study_states", ["question_id"])
    op.create_table("quiz_sessions", sa.Column("id", sa.String(36), primary_key=True), sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("bank_id", sa.String(36), sa.ForeignKey("question_banks.id", ondelete="CASCADE"), nullable=False), sa.Column("config", sa.JSON(), nullable=False), sa.Column("question_order", sa.JSON(), nullable=False), sa.Column("current_index", sa.Integer(), nullable=False), sa.Column("status", sa.String(20), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.Column("completed_at", sa.DateTime(timezone=True)))
    op.create_index("ix_quiz_sessions_user_id", "quiz_sessions", ["user_id"])
    op.create_index("ix_quiz_sessions_bank_id", "quiz_sessions", ["bank_id"])
    op.create_index("ix_quiz_sessions_status", "quiz_sessions", ["status"])
    op.create_table("quiz_answers", sa.Column("id", sa.String(36), primary_key=True), sa.Column("session_id", sa.String(36), sa.ForeignKey("quiz_sessions.id", ondelete="CASCADE"), nullable=False), sa.Column("question_id", sa.String(36), sa.ForeignKey("questions.id", ondelete="CASCADE"), nullable=False), sa.Column("answer", sa.JSON(), nullable=False), sa.Column("question_snapshot", sa.JSON(), nullable=False), sa.Column("is_correct", sa.Boolean()), sa.Column("answered_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("session_id", "question_id", name="uq_answer_session_question"))
    op.create_index("ix_quiz_answers_session_id", "quiz_answers", ["session_id"])
    op.create_index("ix_quiz_answers_question_id", "quiz_answers", ["question_id"])
    op.create_table("collections", sa.Column("id", sa.String(36), primary_key=True), sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("name", sa.String(160), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("user_id", "name", name="uq_collection_user_name"))
    op.create_index("ix_collections_user_id", "collections", ["user_id"])
    op.create_table("collection_questions", sa.Column("collection_id", sa.String(36), sa.ForeignKey("collections.id", ondelete="CASCADE"), primary_key=True), sa.Column("question_id", sa.String(36), sa.ForeignKey("questions.id", ondelete="CASCADE"), primary_key=True), sa.Column("added_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("import_jobs", sa.Column("id", sa.String(36), primary_key=True), sa.Column("bank_id", sa.String(36), sa.ForeignKey("question_banks.id", ondelete="CASCADE"), nullable=False), sa.Column("source_type", sa.String(30), nullable=False), sa.Column("status", sa.String(20), nullable=False), sa.Column("rows", sa.JSON(), nullable=False), sa.Column("errors", sa.JSON(), nullable=False), sa.Column("stats", sa.JSON(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("committed_at", sa.DateTime(timezone=True)))
    op.create_index("ix_import_jobs_bank_id", "import_jobs", ["bank_id"])
    op.create_table("legacy_mappings", sa.Column("legacy_key", sa.String(600), primary_key=True), sa.Column("question_id", sa.String(36), sa.ForeignKey("questions.id", ondelete="CASCADE"), nullable=False))
    op.create_index("ix_legacy_mappings_question_id", "legacy_mappings", ["question_id"])


def downgrade():
    for table in ("legacy_mappings", "import_jobs", "collection_questions", "collections", "quiz_answers", "quiz_sessions", "study_states", "choices", "questions", "question_banks", "users", "workspaces"):
        op.drop_table(table)
