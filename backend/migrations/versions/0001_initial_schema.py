"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-11-25
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _created_at(name: str = "created_at") -> sa.Column:
    return sa.Column(
        name, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )


def upgrade() -> None:
    op.create_table(
        "studies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("subject_code", sa.String(length=32), nullable=False),
        sa.Column("laterality", sa.String(length=5), nullable=False),
        _created_at(),
        sa.CheckConstraint(
            "laterality IN ('left', 'right')", name=op.f("ck_studies_laterality_allowed")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_studies")),
    )
    op.create_index(op.f("ix_studies_subject_code"), "studies", ["subject_code"])

    op.create_table(
        "images",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("study_id", sa.Integer(), nullable=False),
        sa.Column("angle", sa.SmallInteger(), nullable=False),
        sa.Column("modality", sa.String(length=20), nullable=False),
        sa.Column("storage_key", sa.String(length=64), nullable=False),
        _created_at(),
        sa.CheckConstraint("angle IN (0, 90, 180)", name=op.f("ck_images_angle_allowed")),
        sa.CheckConstraint(
            "modality IN ('b_mode', 'color_doppler', 'spectral_doppler')",
            name=op.f("ck_images_modality_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["study_id"], ["studies.id"],
            name=op.f("fk_images_study_id_studies"), ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_images")),
        sa.UniqueConstraint("storage_key", name=op.f("uq_images_storage_key")),
    )
    op.create_index(op.f("ix_images_study_id"), "images", ["study_id"])

    op.create_table(
        "measurements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("study_id", sa.Integer(), nullable=False),
        sa.Column("angle", sa.SmallInteger(), nullable=False),
        sa.Column("diameter_mm", sa.Float(), nullable=True),
        sa.Column("velocity_cm_s", sa.Float(), nullable=True),
        sa.Column("patency", sa.String(length=20), nullable=True),
        sa.Column("quality", sa.String(length=20), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        _created_at("updated_at"),
        sa.CheckConstraint("angle IN (0, 90, 180)", name=op.f("ck_measurements_angle_allowed")),
        sa.CheckConstraint(
            "diameter_mm IS NULL OR diameter_mm >= 0",
            name=op.f("ck_measurements_diameter_non_negative"),
        ),
        sa.CheckConstraint(
            "velocity_cm_s IS NULL OR velocity_cm_s >= 0",
            name=op.f("ck_measurements_velocity_non_negative"),
        ),
        sa.ForeignKeyConstraint(
            ["study_id"], ["studies.id"],
            name=op.f("fk_measurements_study_id_studies"), ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_measurements")),
        sa.UniqueConstraint("study_id", "angle", name=op.f("uq_measurements_study_id_angle")),
    )
    op.create_index(op.f("ix_measurements_study_id"), "measurements", ["study_id"])

    op.create_table(
        "evaluations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("study_id", sa.Integer(), nullable=False),
        sa.Column("compression_pct", sa.Float(), nullable=True),
        sa.Column("criteria_met", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("rule_version", sa.String(length=16), nullable=False),
        sa.Column("review_status", sa.String(length=16), server_default="pending", nullable=False),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column(
            "measurements_snapshot",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            nullable=False,
        ),
        _created_at(),
        sa.ForeignKeyConstraint(
            ["study_id"], ["studies.id"],
            name=op.f("fk_evaluations_study_id_studies"), ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_evaluations")),
    )
    op.create_index(op.f("ix_evaluations_study_id"), "evaluations", ["study_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_evaluations_study_id"), table_name="evaluations")
    op.drop_table("evaluations")
    op.drop_index(op.f("ix_measurements_study_id"), table_name="measurements")
    op.drop_table("measurements")
    op.drop_index(op.f("ix_images_study_id"), table_name="images")
    op.drop_table("images")
    op.drop_index(op.f("ix_studies_subject_code"), table_name="studies")
    op.drop_table("studies")
