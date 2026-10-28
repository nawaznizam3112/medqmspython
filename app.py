import streamlit as st
from datetime import date, timedelta
import auth, db

st.set_page_config(page_title="MD-QMS", page_icon="🩺", layout="wide")
auth.require()

st.title("🩺 Medical Device QMS — ISO 13485:2016 / EU MDR 2017/745")
st.caption("Learn the requirement, then run the record. Use the sidebar to move between QMS processes.")

today, soon = date.today().isoformat(), (date.today() + timedelta(days=90)).isoformat()
docs, capa, risks, sup, aud = (db.df(t) for t in ["documents", "capa", "risks", "suppliers", "audits"])

def n(frame, mask): return int(mask.sum()) if len(frame) else 0

c = st.columns(5)
c[0].metric("Docs overdue for review", n(docs, (docs.status == "Effective") & (docs.review_due < today)) if len(docs) else 0)
c[1].metric("Open CAPAs", n(capa, capa.status != "Closed") if len(capa) else 0)
c[2].metric("Overdue CAPAs", n(capa, (capa.status != "Closed") & (capa.due < today)) if len(capa) else 0)
if len(risks):
    res = risks.res_severity * risks.res_probability
    bad = int(((res >= 12) | (risks.verified != "Yes")).sum())
else:
    bad = 0
c[3].metric("Risks: high residual / unverified", bad)
c[4].metric("Supplier certs expiring ≤90d", n(sup, (sup.cert_expiry != "") & (sup.cert_expiry <= soon)) if len(sup) else 0)

comp = db.df("complaints")
c2 = st.columns(3)
c2[0].metric("Open complaints", n(comp, comp.status != "Closed") if len(comp) else 0)
if len(comp):
    pend = comp[(comp.report_status == "To report") & (comp.report_due != "")]
    c2[1].metric("Vigilance reports overdue", int((pend.report_due < today).sum()))
    c2[2].metric("Vigilance due in 5 days", int(((pend.report_due >= today) & (pend.report_due <= (date.today() + timedelta(days=5)).isoformat())).sum()))
else:
    c2[1].metric("Vigilance reports overdue", 0)
    c2[2].metric("Vigilance due in 5 days", 0)

eqd, pld = db.df("equipment"), db.df("pms_plans")
c3 = st.columns(3)
c3[0].metric("Calibrations overdue", int(((eqd.cal_required == "Yes") & (eqd.next_cal != "") & (eqd.next_cal < today)).sum()) if len(eqd) else 0)
c3[1].metric("Equipment quarantined", int((eqd.status == "Quarantined").sum()) if len(eqd) else 0)
c3[2].metric("PSUR/PMS reports due ≤60d or overdue", int(((pld.next_report_due != "") & (pld.next_report_due <= (date.today() + timedelta(days=60)).isoformat())).sum()) if len(pld) else 0)

st.divider()
st.subheader("How the processes connect (the part most people miss)")
st.markdown("""
**Audit finding / complaint / NC → CAPA → updated risk file + updated procedure (Document Control) → effectiveness check → Management Review.**
A QMS is a *closed loop*, not 5 separate logbooks. Notified Body auditors test the loop: pick any CAPA and trace it to
the risk file, the changed document, and the evidence it worked.
""")

with st.expander("Load demo data (for learning / screenshots)"):
    if st.button("Seed demo records"):
        db.insert("documents", dict(doc_no="SOP-001", title="Control of Documents", doc_type="SOP", version="2.0",
                  status="Effective", owner="QA Manager", effective_date="2025-01-10", review_due="2026-01-10", iso_clause="4.2.4"))
        db.insert("capa", dict(capa_no="CAPA-001", source="Internal audit", description="Obsolete SOP found at assembly station",
                  root_cause="", correction="Removed obsolete copy", corrective_action="", preventive_action="", owner="Ops Lead",
                  opened=today, due=soon, status="Open", effectiveness_check="", closed=""))
        db.insert("risks", dict(device="Dental implant system", hazard="Loss of sterility", hazardous_situation="Pouch seal breach before use",
                  harm="Peri-implant infection", severity=4, probability=3, control="Validated seal process; IFU inspection step",
                  res_severity=4, res_probability=1, verified="No"))
        db.insert("suppliers", dict(name="Precision Titanium Pvt Ltd", category="Raw material", criticality="Critical", status="Approved",
                  last_audit="2025-06-01", next_audit="2026-06-01", iso13485_cert="Yes", cert_expiry="2026-12-31", notes="Grade 4 Ti"))
        st.success("Seeded. Refresh the page.")

