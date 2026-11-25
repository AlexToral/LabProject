"""Modelo de datos del MVP.

Los identificadores son internos. El esquema no almacena nombres ni otros datos
identificativos del paciente: `subject_code` es un código anónimo.
Los valores no medidos se guardan como NULL, nunca como 0.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

ALLOWED_ANGLES = (0, 90, 180)
LATERALITIES = ("left", "right")
MODALITIES = ("b_mode", "color_doppler", "spectral_doppler")

ANGLE_CHECK = "angle IN (0, 90, 180)"
JSON_TYPE = JSON().with_variant(JSONB(), "postgresql")


def _timestamp(**kwargs: Any) -> Mapped[datetime]:
    return mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, **kwargs
    )


class Study(Base):
    __tablename__ = "studies"
    __table_args__ = (
        CheckConstraint("laterality IN ('left', 'right')", name="laterality_allowed"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subject_code: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    laterality: Mapped[str] = mapped_column(String(5), nullable=False)
    created_at: Mapped[datetime] = _timestamp()

    images: Mapped[list["Image"]] = relationship(
        back_populates="study", cascade="all, delete-orphan", passive_deletes=True
    )
    measurements: Mapped[list["Measurement"]] = relationship(
        back_populates="study", cascade="all, delete-orphan", passive_deletes=True
    )
    evaluations: Mapped[list["Evaluation"]] = relationship(
        back_populates="study", cascade="all, delete-orphan", passive_deletes=True
    )


class Image(Base):
    __tablename__ = "images"
    __table_args__ = (
        CheckConstraint(ANGLE_CHECK, name="angle_allowed"),
        CheckConstraint(
            "modality IN ('b_mode', 'color_doppler', 'spectral_doppler')",
            name="modality_allowed",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    study_id: Mapped[int] = mapped_column(
        ForeignKey("studies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    angle: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    modality: Mapped[str] = mapped_column(String(20), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    created_at: Mapped[datetime] = _timestamp()

    study: Mapped[Study] = relationship(back_populates="images")


class Measurement(Base):
    __tablename__ = "measurements"
    __table_args__ = (
        UniqueConstraint("study_id", "angle"),
        CheckConstraint(ANGLE_CHECK, name="angle_allowed"),
        CheckConstraint("diameter_mm IS NULL OR diameter_mm >= 0", name="diameter_non_negative"),
        CheckConstraint(
            "velocity_cm_s IS NULL OR velocity_cm_s >= 0", name="velocity_non_negative"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    study_id: Mapped[int] = mapped_column(
        ForeignKey("studies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    angle: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    diameter_mm: Mapped[float | None] = mapped_column(Float, nullable=True)
    velocity_cm_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Los valores permitidos de patency/quality se definen con el especialista (issue E3-01).
    patency: Mapped[str | None] = mapped_column(String(20), nullable=True)
    quality: Mapped[str | None] = mapped_column(String(20), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = _timestamp(onupdate=func.now())

    study: Mapped[Study] = relationship(back_populates="measurements")


class Evaluation(Base):
    __tablename__ = "evaluations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    study_id: Mapped[int] = mapped_column(
        ForeignKey("studies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    compression_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    criteria_met: Mapped[bool] = mapped_column(Boolean, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    rule_version: Mapped[str] = mapped_column(String(16), nullable=False)
    review_status: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="pending"
    )
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Copia exacta de las mediciones usadas, para que la evaluación sea reproducible.
    measurements_snapshot: Mapped[Any] = mapped_column(JSON_TYPE, nullable=False)
    created_at: Mapped[datetime] = _timestamp()

    study: Mapped[Study] = relationship(back_populates="evaluations")
