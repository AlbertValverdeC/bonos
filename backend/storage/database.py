from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker, Session

from backend.config.settings import DATABASE_URL
from backend.storage.models import Base

engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)


def init_db():
    """Create all tables if they don't exist."""
    Base.metadata.create_all(engine)


def get_db() -> Session:
    """Get a database session. Caller must close it."""
    return SessionLocal()


def ensure_schema():
    """Add any new columns/tables without dropping existing data."""
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    for table in Base.metadata.sorted_tables:
        if table.name not in existing_tables:
            table.create(engine)
        else:
            existing_cols = {c["name"] for c in inspector.get_columns(table.name)}
            for col in table.columns:
                if col.name not in existing_cols:
                    col_type = col.type.compile(engine.dialect)
                    default = ""
                    if col.default is not None:
                        val = col.default.arg
                        if callable(val):
                            default = ""
                        elif isinstance(val, str):
                            default = f" DEFAULT '{val}'"
                        else:
                            default = f" DEFAULT {val}"
                    engine.execute(
                        f"ALTER TABLE {table.name} ADD COLUMN {col.name} {col_type}{default}"
                    )
