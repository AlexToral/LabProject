"""Restricciones del esquema a nivel de base de datos.

Por defecto se usa SQLite en memoria. Para probar contra PostgreSQL, definir
TEST_DATABASE_URL apuntando a una base de datos desechable (sus tablas se recrean).
"""

import os

import pytest
from sqlalchemy import create_engine, event, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import Base, Evaluation, Image, Measurement, Study


def _engine():
    url = os.environ.get("TEST_DATABASE_URL")
    if url:
        engine = create_engine(Settings(database_url=url, _env_file=None).database_url)
    else:
        engine = create_engine("sqlite://")

        @event.listens_for(engine, "connect")
        def _enable_sqlite_fks(dbapi_connection, _record):
            dbapi_connection.execute("PRAGMA foreign_keys=ON")

    return engine


@pytest.fixture
def db():
    engine = _engine()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def study(db):
    s = Study(subject_code="demo-001", laterality="right")
    db.add(s)
    db.commit()
    return s


def _assert_rejected(db, obj):
    db.add(obj)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_valid_rows_are_accepted(db, study):
    db.add_all(
        [
            Image(study_id=study.id, angle=180, modality="b_mode", storage_key="k1"),
            Measurement(study_id=study.id, angle=0, diameter_mm=7.4, velocity_cm_s=30.0),
            Evaluation(
                study_id=study.id,
                criteria_met=False,
                status="not_evaluable",
                rule_version="1.0",
                measurements_snapshot={"0": {"diameter_mm": 7.4}},
            ),
        ]
    )
    db.commit()
    evaluation = db.scalar(select(Evaluation))
    assert evaluation.review_status == "pending"
    assert evaluation.created_at is not None
    assert evaluation.measurements_snapshot == {"0": {"diameter_mm": 7.4}}


def test_invalid_laterality_rejected(db):
    _assert_rejected(db, Study(subject_code="demo-002", laterality="both"))


@pytest.mark.parametrize("angle", [-1, 45, 91, 360])
def test_invalid_angle_rejected(db, study, angle):
    _assert_rejected(db, Measurement(study_id=study.id, angle=angle))
    _assert_rejected(
        db, Image(study_id=study.id, angle=angle, modality="b_mode", storage_key=f"a{angle}")
    )


def test_invalid_modality_rejected(db, study):
    _assert_rejected(db, Image(study_id=study.id, angle=0, modality="mri", storage_key="x"))


def test_negative_diameter_rejected(db, study):
    _assert_rejected(db, Measurement(study_id=study.id, angle=0, diameter_mm=-0.1))


def test_negative_velocity_rejected(db, study):
    _assert_rejected(db, Measurement(study_id=study.id, angle=0, velocity_cm_s=-1))


def test_null_measurements_stay_null_not_zero(db, study):
    db.add(Measurement(study_id=study.id, angle=180))
    db.commit()
    db.expire_all()
    m = db.scalar(select(Measurement))
    assert m.diameter_mm is None
    assert m.velocity_cm_s is None


def test_zero_is_a_valid_measurement(db, study):
    db.add(Measurement(study_id=study.id, angle=180, diameter_mm=0, velocity_cm_s=0))
    db.commit()
    db.expire_all()
    m = db.scalar(select(Measurement))
    assert m.diameter_mm == 0
    assert m.velocity_cm_s == 0


def test_one_measurement_per_study_and_angle(db, study):
    db.add(Measurement(study_id=study.id, angle=90))
    db.commit()
    _assert_rejected(db, Measurement(study_id=study.id, angle=90))


def test_measurement_requires_existing_study(db):
    _assert_rejected(db, Measurement(study_id=9999, angle=0))


def test_deleting_study_cascades(db, study):
    db.add_all(
        [
            Image(study_id=study.id, angle=0, modality="b_mode", storage_key="k2"),
            Measurement(study_id=study.id, angle=0),
            Evaluation(
                study_id=study.id,
                criteria_met=False,
                status="not_evaluable",
                rule_version="1.0",
                measurements_snapshot={},
            ),
        ]
    )
    db.commit()
    db.delete(study)
    db.commit()
    for model in (Image, Measurement, Evaluation):
        assert db.scalar(select(model)) is None


def test_schema_has_no_identifying_patient_fields(db):
    forbidden = ("name", "nombre", "apellido", "expediente", "curp", "birth", "nacimiento",
                 "phone", "telefono", "email", "address", "direccion")
    inspector = inspect(db.get_bind())
    for table in inspector.get_table_names():
        for column in inspector.get_columns(table):
            assert not any(word in column["name"].lower() for word in forbidden), (
                f"{table}.{column['name']} parece un dato identificativo"
            )
