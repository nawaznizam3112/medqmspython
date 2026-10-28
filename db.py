"""SQLite data layer. One file DB = easy to back up, easy to version the schema in Git."""
import sqlite3
from pathlib import Path
import pandas as pd

DB = Path(__file__).parent / "data" / "qms.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents(id INTEGER PRIMARY KEY, doc_no TEXT UNIQUE, title TEXT, doc_type TEXT,
  version TEXT, status TEXT, owner TEXT, effective_date TEXT, review_due TEXT, iso_clause TEXT);
CREATE TABLE IF NOT EXISTS capa(id INTEGER PRIMARY KEY, capa_no TEXT UNIQUE, source TEXT, description TEXT,
  root_cause TEXT, correction TEXT, corrective_action TEXT, preventive_action TEXT, owner TEXT, opened TEXT,
  due TEXT, status TEXT, effectiveness_check TEXT, closed TEXT);
CREATE TABLE IF NOT EXISTS risks(id INTEGER PRIMARY KEY, device TEXT, hazard TEXT, hazardous_situation TEXT,
  harm TEXT, severity INTEGER, probability INTEGER, control TEXT, res_severity INTEGER, res_probability INTEGER,
  verified TEXT);
CREATE TABLE IF NOT EXISTS suppliers(id INTEGER PRIMARY KEY, name TEXT, category TEXT, criticality TEXT,
  status TEXT, last_audit TEXT, next_audit TEXT, iso13485_cert TEXT, cert_expiry TEXT, notes TEXT);
CREATE TABLE IF NOT EXISTS audits(id INTEGER PRIMARY KEY, audit_no TEXT, audit_type TEXT, scope TEXT, auditor TEXT,
  audit_date TEXT, finding TEXT, finding_class TEXT, iso_clause TEXT, capa_no TEXT, status TEXT);
"""

def conn():
    DB.parent.mkdir(exist_ok=True)
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def init():
    with conn() as c:
        c.executescript(SCHEMA)

def df(table):
    with conn() as c:
        return pd.read_sql_query(f"SELECT * FROM {table}", c)

def insert(table, row: dict):
    cols = ",".join(row)
    qs = ",".join("?" * len(row))
    with conn() as c:
        c.execute(f"INSERT INTO {table}({cols}) VALUES({qs})", list(row.values()))

def update(table, rid, row: dict):
    sets = ",".join(f"{k}=?" for k in row)
    with conn() as c:
        c.execute(f"UPDATE {table} SET {sets} WHERE id=?", [*row.values(), rid])

def delete(table, rid):
    with conn() as c:
        c.execute(f"DELETE FROM {table} WHERE id=?", (rid,))

def next_no(table, col, prefix):
    n = len(df(table)) + 1
    return f"{prefix}-{n:03d}"
