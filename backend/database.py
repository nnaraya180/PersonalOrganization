# database.py
from pathlib import Path
from sqlmodel import SQLModel, create_engine, Session

# Always put the DB file next to this file, in backend/pantry.db
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "pantry.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

# echo=True prints SQL statements (useful while learning)
engine = create_engine(DATABASE_URL, echo=True)


def init_db():
    """Create tables if they don't exist."""
    SQLModel.metadata.create_all(engine)


def get_session():
    """FastAPI dependency that yields a DB session per request."""
    with Session(engine) as session:
        yield session
