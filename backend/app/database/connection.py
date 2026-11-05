import os
from pathlib import Path
from typing import Optional, Generator
from contextlib import contextmanager
import duckdb

# Base directory for the project
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DEFAULT_DB_PATH = PROJECT_ROOT / "dataset" / "processed" / "uzex_data.duckdb"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"

def get_db_path(custom_path: Optional[str] = None) -> Path:
    if custom_path:
        return Path(custom_path)
    env_path = os.getenv("DB_PATH")
    if env_path:
        p = Path(env_path)
        return p if p.is_absolute() else (PROJECT_ROOT / p)
    return DEFAULT_DB_PATH

def get_writable_connection(db_path: Optional[str] = None) -> duckdb.DuckDBPyConnection:
    """
    Returns a writable DuckDB connection.
    Used STRICTLY for initial database creation, schema migrations, and batch data imports.
    """
    path = get_db_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(database=str(path), read_only=False)

def get_readonly_connection(db_path: Optional[str] = None) -> duckdb.DuckDBPyConnection:
    """
    Returns a read-only DuckDB connection.
    Used by the AI Agent and API query engines to strictly prevent mutations and SQL injection.
    """
    path = get_db_path(db_path)
    if not path.exists():
        print(f"[UZEX AI] Database file not found at: {path}. Auto-importing 500,000 transactions from dataset/original...")
        from app.database.importer import import_all_data
        import_all_data(db_path=str(path))
    return duckdb.connect(database=str(path), read_only=True)

@contextmanager
def writable_db(db_path: Optional[str] = None) -> Generator[duckdb.DuckDBPyConnection, None, None]:
    """Context manager for writable database operations."""
    conn = get_writable_connection(db_path)
    try:
        yield conn
    finally:
        conn.close()

@contextmanager
def readonly_db(db_path: Optional[str] = None) -> Generator[duckdb.DuckDBPyConnection, None, None]:
    """Context manager for read-only query operations."""
    conn = get_readonly_connection(db_path)
    try:
        yield conn
    finally:
        conn.close()

def init_database(db_path: Optional[str] = None, schema_file: Optional[Path] = None) -> None:
    """
    Initializes the DuckDB database by applying schema.sql using a writable connection.
    """
    path = get_db_path(db_path)
    schema_f = schema_file or SCHEMA_PATH
    if not schema_f.exists():
        raise FileNotFoundError(f"Schema file not found at: {schema_f}")

    with open(schema_f, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    with writable_db(str(path)) as conn:
        conn.execute(schema_sql)
