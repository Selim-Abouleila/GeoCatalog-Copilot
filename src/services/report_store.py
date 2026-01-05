from pathlib import Path
import os
import glob
from typing import List, Optional

REPORTS_DIR = Path("reports")

def list_reports(out_dir: Path = REPORTS_DIR) -> List[Path]:
    """Returns a list of markdown report paths sorted by modification time (newest first)."""
    if not out_dir.exists():
        return []
    
    # Use glob to find .md files
    # Using str(out_dir) because glob.glob expects string in some versions, though Path usually works
    pattern = str(out_dir / "catalog_health_*.md")
    files = glob.glob(pattern)
    
    # Sort by mtime desc
    files.sort(key=os.path.getmtime, reverse=True)
    return [Path(f) for f in files]

def read_text(path: Path) -> str:
    """Reads text content safely."""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return f"Error reading file: {e}"

def list_report_csvs(md_path: Path) -> List[Path]:
    """Finds CSVs associated with the given markdown report."""
    if not md_path.exists():
        return []
    
    # Naming convention: catalog_health_<date>_<id>.md
    # CSVs: catalog_health_<date>_<id>_*.csv
    stem = md_path.stem # e.g. catalog_health_2026-01-01_79d0e419
    parent = md_path.parent
    
    pattern = str(parent / f"{stem}_*.csv")
    files = glob.glob(pattern)
    return [Path(f) for f in files]
