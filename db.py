"""SQLite data layer with an automatic audit trail and role-based write guard."""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import streamlit as st

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
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT UNIQUE, full_name TEXT, role TEXT,
  pw_hash TEXT, failed INTEGER DEFAULT 0, active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS audit_trail(id INTEGER PRIMARY KEY, ts TEXT, user TEXT, action TEXT, tbl TEXT,
  record_id INTEGER, detail TEXT);
CREATE TABLE IF NOT EXISTS complaints(id INTEGER PRIMARY KEY, complaint_no TEXT UNIQUE, device TEXT, lot TEXT,
  awareness_date TEXT, description TEXT, event_type TEXT, report_due TEXT, report_status TEXT,
  investigation TEXT, capa_no TEXT, fsca TEXT, status TEXT);
CREATE TABLE IF NOT EXISTS mgmt_reviews(id INTEGER PRIMARY KEY, review_date TEXT, attendees TEXT,
  inputs_snapshot TEXT, other_inputs TEXT, decisions TEXT, actions TEXT, next_review TEXT);
CREATE TABLE IF NOT EXISTS devices(id INTEGER PRIMARY KEY, name TEXT UNIQUE, intended_purpose TEXT, mdr_class TEXT,
  rule TEXT, route TEXT);
CREATE TABLE IF NOT EXISTS techdoc(id INTEGER PRIMARY KEY, device TEXT, item_ref TEXT, item TEXT, status TEXT,
  doc_ref TEXT, notes TEXT);
CREATE TABLE IF NOT EXISTS design_reqs(id INTEGER PRIMARY KEY, device TEXT, req_no TEXT, requirement TEXT, source TEXT,
  risk_ref INTEGER DEFAULT 0, output_ref TEXT, verification_ref TEXT, verification_status TEXT, validation_ref TEXT,
  validation_status TEXT);
CREATE TABLE IF NOT EXISTS design_reviews(id INTEGER PRIMARY KEY, device TEXT, stage TEXT, review_date TEXT,
  participants TEXT, independent_reviewer TEXT, decisions TEXT, status TEXT);
CREATE TABLE IF NOT EXISTS design_changes(id INTEGER PRIMARY KEY, change_no TEXT, device TEXT, description TEXT,
  reason TEXT, impact_risk TEXT, impact_vv TEXT, impact_regulatory TEXT, status TEXT, change_date TEXT);
CREATE TABLE IF NOT EXISTS pms_plans(id INTEGER PRIMARY KEY, device TEXT UNIQUE, plan_ref TEXT, data_sources TEXT,
  trend_method TEXT, pmcf_needed TEXT, pmcf_justification TEXT, last_report TEXT, next_report_due TEXT);
CREATE TABLE IF NOT EXISTS pmcf_activities(id INTEGER PRIMARY KEY, device TEXT, activity TEXT, method TEXT, status TEXT,
  due TEXT, report_ref TEXT, findings TEXT);
CREATE TABLE IF NOT EXISTS pms_sales(id INTEGER PRIMARY KEY, device TEXT, period TEXT, units INTEGER);
CREATE TABLE IF NOT EXISTS trend_assessments(id INTEGER PRIMARY KEY, device TEXT, period TEXT, signal TEXT,
  assessment TEXT, significant TEXT, action TEXT, capa_no TEXT, assessed_date TEXT);
CREATE TABLE IF NOT EXISTS equipment(id INTEGER PRIMARY KEY, eq_no TEXT UNIQUE, name TEXT, category TEXT, location TEXT,
  serial TEXT, cal_required TEXT, cal_interval_days INTEGER, last_cal TEXT, next_cal TEXT, status TEXT);
CREATE TABLE IF NOT EXISTS calibrations(id INTEGER PRIMARY KEY, eq_no TEXT, cal_date TEXT, performed_by TEXT,
  standard_ref TEXT, result TEXT, certificate_ref TEXT, impact_assessment TEXT, next_due TEXT);
CREATE TABLE IF NOT EXISTS env_records(id INTEGER PRIMARY KEY, area TEXT, parameter TEXT, reading REAL, limit_low REAL,
  limit_high REAL, recorded_at TEXT, recorded_by TEXT, in_spec TEXT, action TEXT);
CREATE TABLE IF NOT EXISTS process_validations(id INTEGER PRIMARY KEY, process TEXT, eq_no TEXT, stage TEXT,
  protocol_ref TEXT, report_ref TEXT, outcome TEXT, stage_date TEXT, reval_months INTEGER DEFAULT 12, notes TEXT);
"""

def conn():
    DB.parent.mkdir(exist_ok=True)
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def init():
    with conn() as c:
        c.executescript(SCHEMA)

def query(sql, params=()):
    with conn() as c:
        return [dict(r) for r in c.execute(sql, params).fetchall()]

def execute(sql, params=()):
    with conn() as c:
        return c.execute(sql, params).lastrowid

def df(table):
    with conn() as c:
        return pd.read_sql_query(f"SELECT * FROM {table}", c)

def _user():
    return st.session_state.get("user")

def _guard():
    u = _user()
    if not u or u["role"] not in ("Admin", "QA"):
        st.error("Read-only role: you do not have permission to change records.")
        st.stop()

def log(action, table="", rid=0, detail="", user=None):
    execute("INSERT INTO audit_trail(ts,user,action,tbl,record_id,detail) VALUES(?,?,?,?,?,?)",
            (datetime.now(timezone.utc).isoformat(timespec="seconds"), user or (_user() or {}).get("username", "system"),
             action, table, rid, detail))

def _safe(table, row):
    return {"username": row.get("username")} if table == "users" else row

def insert(table, row: dict):
    _guard()
    rid = execute(f"INSERT INTO {table}({','.join(row)}) VALUES({','.join('?' * len(row))})", list(row.values()))
    log("CREATE", table, rid, json.dumps(_safe(table, row), default=str)[:2000])
    return rid

def update(table, rid, row: dict):
    _guard()
    old = query(f"SELECT * FROM {table} WHERE id=?", (rid,))
    old = old[0] if old else {}
    diff = {k: [old.get(k), v] for k, v in row.items() if old.get(k) != v}
    if not diff:
        return
    execute(f"UPDATE {table} SET {','.join(f'{k}=?' for k in row)} WHERE id=?", [*row.values(), rid])
    log("UPDATE", table, rid, json.dumps({k: "***" for k in diff} if table == "users" else diff, default=str)[:2000])

def delete(table, rid):
    _guard()
    log("DELETE", table, rid)
    execute(f"DELETE FROM {table} WHERE id=?", (rid,))

def next_no(table, col, prefix):
    n = query(f"SELECT COALESCE(MAX(id),0)+1 AS n FROM {table}")[0]["n"]
    return f"{prefix}-{n:03d}"

