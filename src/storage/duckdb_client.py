import duckdb
import os
import pathlib
from typing import List

def get_db_path() -> pathlib.Path:
    """
    Returns the path to the DuckDB database file.
    Default: data/catalog.duckdb relative to the project root.
    Override via env var GEOCATALOG_DB_PATH.
    """
    # Prefer env var if set
    env_path = os.getenv("GEOCATALOG_DB_PATH")
    if env_path:
        return pathlib.Path(env_path)
    
    # Default: data/catalog.duckdb in project root
    # transform src/storage/duckdb_client.py -> ... -> project_root/data/catalog.duckdb
    # This logic assumes this file is in src/storage
    current_dir = pathlib.Path(__file__).parent.resolve()
    project_root = current_dir.parent.parent
    return project_root / "data" / "catalog.duckdb"

def connect(read_only: bool = False) -> duckdb.DuckDBPyConnection:
    """
    Connects to the DuckDB database.
    
    Args:
        read_only (bool): If True, opens the connection in read-only mode.
        
    Returns:
        duckdb.DuckDBPyConnection: The database connection.
    """
    db_path = get_db_path()
    
    # Ensure parent directory exists
    if not db_path.parent.exists():
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
    return duckdb.connect(str(db_path), read_only=read_only)

def init_db(con: duckdb.DuckDBPyConnection) -> None:
    """
    Initializes the database schema using ddl_duckdb.sql.
    Idempotent.
    
    Args:
        con (duckdb.DuckDBPyConnection): The database connection.
    """
    # Load DDL SQL
    current_dir = pathlib.Path(__file__).parent.resolve()
    ddl_path = current_dir / "ddl_duckdb.sql"
    
    with open(ddl_path, "r", encoding="utf-8") as f:
        ddl_sql = f.read()
        
    # Execute DDL
    con.sql(ddl_sql)

def ensure_db_initialized() -> pathlib.Path:
    """
    Convenience function that connects to the DB, runs init_db, and closes connection.
    
    Returns:
        pathlib.Path: The path to the initialized database.
    """
    con = connect(read_only=False)
    try:
        init_db(con)
    finally:
        con.close()
        
    return get_db_path()

def list_tables(con: duckdb.DuckDBPyConnection) -> List[str]:
    """
    Returns a sorted list of table names in the main schema.
    
    Args:
        con (duckdb.DuckDBPyConnection): The database connection.
        
    Returns:
        List[str]: List of table names.
    """
    result = con.sql("SHOW TABLES").fetchall()
    # Result is list of tuples (name,)
    tables = [row[0] for row in result]
    tables.sort()
    return tables
