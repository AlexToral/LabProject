"""Las migraciones crean el esquema completo y coinciden con los modelos."""

from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, inspect

from app.models import Base

BACKEND_DIR = Path(__file__).resolve().parents[1]
EXPECTED_TABLES = {"studies", "images", "measurements", "evaluations"}


def _alembic_config(url: str) -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", url)
    return config


def test_upgrade_creates_all_tables_and_matches_models(tmp_path):
    url = f"sqlite:///{(tmp_path / 'migrations.db').as_posix()}"
    command.upgrade(_alembic_config(url), "head")

    engine = create_engine(url)
    try:
        assert EXPECTED_TABLES <= set(inspect(engine).get_table_names())
        with engine.connect() as connection:
            diff = compare_metadata(MigrationContext.configure(connection), Base.metadata)
        assert diff == [], f"Los modelos y las migraciones difieren: {diff}"
    finally:
        engine.dispose()


def test_downgrade_removes_all_tables(tmp_path):
    url = f"sqlite:///{(tmp_path / 'migrations.db').as_posix()}"
    config = _alembic_config(url)
    command.upgrade(config, "head")
    command.downgrade(config, "base")

    engine = create_engine(url)
    try:
        assert not (EXPECTED_TABLES & set(inspect(engine).get_table_names()))
    finally:
        engine.dispose()
