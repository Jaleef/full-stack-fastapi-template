"""初始迁移：建 10 张表、向量列与 HNSW 索引。

Revision ID: 0001_initial
Revises:
Create Date: 2026-11-21

前置条件：外部库已启用 pgvector（本迁移不负责 CREATE EXTENSION）。
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

# 与 Settings.EMBEDDING_DIM 保持一致；改动维度需要新的迁移。
EMBEDDING_DIM = 1024


def upgrade() -> None:
    """建表、向量列与 HNSW 索引。"""
    # 先确认扩展存在，否则报一条比 "type vector does not exist" 更清楚的错误。
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_extension WHERE extname = 'vector'
            ) THEN
                RAISE EXCEPTION
                    'pgvector extension is required; run CREATE EXTENSION vector';
            END IF;
        END $$;
        """
    )

    op.create_table(
        "analysis",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("stage", sa.String(length=64), nullable=True),
        sa.Column("profile", sa.String(length=64), nullable=True),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("llm_enabled", sa.Boolean(), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=True),
        sa.Column("prompt_version", sa.String(length=32), nullable=True),
        sa.Column("embedding_model", sa.String(length=128), nullable=True),
        sa.Column("embedding_dim", sa.Integer(), nullable=True),
        sa.Column("previous_id", sa.Uuid(), nullable=True),
        sa.Column("stats", sa.JSON(), nullable=False),
        sa.Column("diff", sa.JSON(), nullable=False),
        sa.Column("error", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["previous_id"], ["analysis.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "document",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("analysis_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("filename", sa.String(length=512), nullable=False),
        sa.Column("stored_path", sa.String(length=1024), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("version_hint", sa.String(length=64), nullable=True),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["analysis_id"], ["analysis.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_document_analysis_id", "document", ["analysis_id"])

    op.create_table(
        "parse_decision",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("analysis_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("block_index", sa.Integer(), nullable=False),
        sa.Column("section_no", sa.String(length=64), nullable=True),
        sa.Column("section_title", sa.String(length=512), nullable=True),
        sa.Column("text", sa.String(), nullable=False),
        sa.Column("verdict", sa.String(length=32), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=True),
        sa.Column("reason", sa.String(length=512), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["analysis_id"], ["analysis.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_parse_decision_analysis_id", "parse_decision", ["analysis_id"]
    )

    op.create_table(
        "requirement_unit",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("analysis_id", sa.Uuid(), nullable=False),
        sa.Column("unit_key", sa.String(length=128), nullable=False),
        sa.Column("external_id", sa.String(length=128), nullable=True),
        sa.Column("parent_external_id", sa.String(length=128), nullable=True),
        sa.Column("section_no", sa.String(length=64), nullable=True),
        sa.Column("section_title", sa.String(length=512), nullable=True),
        sa.Column("title", sa.String(length=512), nullable=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("category", sa.String(length=32), nullable=True),
        sa.Column("domain", sa.String(length=64), nullable=True),
        sa.Column("is_container", sa.Boolean(), nullable=False),
        sa.Column("judge_confidence", sa.Float(), nullable=True),
        sa.Column("judge_reason", sa.String(length=512), nullable=True),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("raw_text", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["analysis_id"], ["analysis.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_requirement_unit_analysis_id", "requirement_unit", ["analysis_id"]
    )

    op.create_table(
        "atomic_requirement",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("analysis_id", sa.Uuid(), nullable=False),
        sa.Column("text", sa.String(), nullable=False),
        sa.Column("search_text", sa.String(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("has_metric", sa.Boolean(), nullable=False),
        sa.Column("variant_count", sa.Integer(), nullable=False),
        sa.Column("merge_method", sa.String(length=32), nullable=True),
        sa.Column("merge_confidence", sa.Float(), nullable=True),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=True),
        sa.Column("embedding_model", sa.String(length=128), nullable=True),
        sa.Column("text_hash", sa.String(length=64), nullable=True),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["analysis_id"], ["analysis.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_atomic_requirement_analysis_id",
        "atomic_requirement",
        ["analysis_id"],
    )

    op.create_table(
        "atom_source",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("atom_id", sa.Uuid(), nullable=False),
        sa.Column("unit_id", sa.Uuid(), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("span_text", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["atom_id"], ["atomic_requirement.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["unit_id"], ["requirement_unit.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_atom_source_atom_id", "atom_source", ["atom_id"])
    op.create_index("ix_atom_source_unit_id", "atom_source", ["unit_id"])

    op.create_table(
        "design_element",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("analysis_id", sa.Uuid(), nullable=False),
        sa.Column("element_key", sa.String(length=128), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=True),
        sa.Column("name", sa.String(length=512), nullable=False),
        sa.Column("level", sa.String(length=32), nullable=True),
        sa.Column("domain", sa.String(length=64), nullable=True),
        sa.Column("section_no", sa.String(length=64), nullable=True),
        sa.Column("section_title", sa.String(length=512), nullable=True),
        sa.Column("caption", sa.String(length=512), nullable=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("interface", sa.String(), nullable=True),
        sa.Column("input", sa.String(), nullable=True),
        sa.Column("output", sa.String(), nullable=True),
        sa.Column("performance", sa.String(), nullable=True),
        sa.Column("constraints", sa.String(), nullable=True),
        sa.Column("test_points", sa.String(), nullable=True),
        sa.Column("narrative", sa.String(), nullable=True),
        sa.Column("attributes", sa.JSON(), nullable=False),
        sa.Column("fields", sa.JSON(), nullable=False),
        sa.Column("search_text", sa.String(), nullable=False),
        sa.Column("raw_text", sa.String(), nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=True),
        sa.Column("embedding_model", sa.String(length=128), nullable=True),
        sa.Column("text_hash", sa.String(length=64), nullable=True),
        sa.Column("variants", sa.JSON(), nullable=False),
        sa.Column("source_refs", sa.JSON(), nullable=False),
        sa.Column("parent_code", sa.String(length=64), nullable=True),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["analysis_id"], ["analysis.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_design_element_analysis_id", "design_element", ["analysis_id"]
    )

    op.create_table(
        "mapping",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("analysis_id", sa.Uuid(), nullable=False),
        sa.Column("atom_id", sa.Uuid(), nullable=False),
        sa.Column("element_id", sa.Uuid(), nullable=False),
        sa.Column("relation", sa.String(length=16), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("method", sa.String(length=16), nullable=False),
        sa.Column("rationale", sa.String(), nullable=True),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("review_status", sa.String(length=16), nullable=False),
        sa.Column("review_note", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["analysis_id"], ["analysis.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["atom_id"], ["atomic_requirement.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["element_id"], ["design_element.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_mapping_analysis_id", "mapping", ["analysis_id"])
    op.create_index("ix_mapping_atom_id", "mapping", ["atom_id"])
    op.create_index("ix_mapping_element_id", "mapping", ["element_id"])

    op.create_table(
        "finding",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("analysis_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("dimension", sa.String(length=32), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("detail", sa.String(), nullable=False),
        sa.Column("unit_refs", sa.JSON(), nullable=False),
        sa.Column("atom_refs", sa.JSON(), nullable=False),
        sa.Column("element_refs", sa.JSON(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("suggestion", sa.String(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("fingerprint", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("note", sa.String(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["analysis_id"], ["analysis.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_finding_analysis_id", "finding", ["analysis_id"])
    op.create_index("ix_finding_fingerprint", "finding", ["fingerprint"])

    op.create_table(
        "llm_cache",
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("prompt_version", sa.String(length=32), nullable=False),
        sa.Column("response", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )

    # HNSW 索引依赖 pgvector；空表上创建很快。
    op.execute(
        "CREATE INDEX ix_atomic_requirement_embedding_hnsw "
        "ON atomic_requirement USING hnsw (embedding vector_cosine_ops)"
    )
    op.execute(
        "CREATE INDEX ix_design_element_embedding_hnsw "
        "ON design_element USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    """按依赖反序删表。"""
    op.execute("DROP INDEX IF EXISTS ix_design_element_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS ix_atomic_requirement_embedding_hnsw")

    op.drop_table("llm_cache")
    op.drop_table("finding")
    op.drop_table("mapping")
    op.drop_table("design_element")
    op.drop_table("atom_source")
    op.drop_table("atomic_requirement")
    op.drop_table("requirement_unit")
    op.drop_table("parse_decision")
    op.drop_table("document")
    op.drop_table("analysis")
