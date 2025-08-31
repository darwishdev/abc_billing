import frappe
from pathlib import Path

SQL_DIR = Path(frappe.get_app_path("abc_billing", "sql"))

def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")

def exec_sql_file(filename: str) -> None:
    """
    Execute SQL file as a single statement.
    The SQL file should handle its own delimiters using DELIMITER command.
    """
    sql = _read(SQL_DIR / filename)
    # Commit any pending transaction before DDL
    frappe.db.commit()
    frappe.db.sql(sql, auto_commit=True)

