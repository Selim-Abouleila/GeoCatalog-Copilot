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

def upsert_watchlist_item(item: dict) -> None:
    """
    Upserts a watchlist item.
    
    Args:
        item (dict): Dictionary containing item details. 
                     Must include: item_id, url, title, item_type, owner.
                     Optional: source_query, notes.
    """
    con = connect(read_only=False)
    try:
        con.execute("""
            INSERT INTO watchlist_items (
                item_id, item_url, title, item_type, owner, source_query, added_at, notes
            ) VALUES (
                ?, ?, ?, ?, ?, ?, current_timestamp, ?
            ) ON CONFLICT (item_id) DO UPDATE SET
                item_url = excluded.item_url,
                title = excluded.title,
                item_type = excluded.item_type,
                owner = excluded.owner,
                added_at = current_timestamp,
                notes = COALESCE(excluded.notes, watchlist_items.notes)
        """, (
            item['id'], 
            item.get('url'), 
            item.get('title'), 
            item.get('type'), 
            item.get('owner'),
            item.get('source_query'),
            item.get('notes')
        ))
    finally:
        con.close()

def remove_watchlist_item(item_id: str) -> None:
    """
    Removes a watchlist item by ID.
    
    Args:
        item_id (str): The ID of the item to remove.
    """
    con = connect(read_only=False)
    try:
        con.execute("DELETE FROM watchlist_items WHERE item_id = ?", (item_id,))
    finally:
        con.close()

def list_watchlist_items() -> List[dict]:
    """
    Lists all watchlist items detailed.
    
    Returns:
        List[dict]: List of items sorted by added_at DESC.
    """
    con = connect(read_only=True)
    try:
        # Check if table exists first to avoid errors on fresh start before init
        tables = con.sql("SHOW TABLES").fetchall()
        table_names = [t[0] for t in tables]
        if 'watchlist_items' not in table_names:
            return []
            
        columns = ['item_id', 'item_url', 'title', 'item_type', 'owner', 'source_query', 'added_at', 'notes']
        res = con.execute("SELECT item_id, item_url, title, item_type, owner, source_query, added_at, notes FROM watchlist_items ORDER BY added_at DESC").fetchall()
        
        items = []
        for row in res:
            items.append({
                'id': row[0],
                'url': row[1],
                'title': row[2],
                'type': row[3],
                'owner': row[4],
                'source_query': row[5],
                'added_at': row[6],
                'notes': row[7]
            })
        return items
    finally:
        con.close()
