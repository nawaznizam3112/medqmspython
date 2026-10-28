import streamlit as st

def why(md: str):
    with st.expander("🎓 Why this exists (ISO 13485 / EU MDR reasoning)"):
        st.markdown(md)

def risk_level(score: int) -> str:
    # Illustrative policy. YOUR risk management plan (ISO 14971 §4.2) must define acceptability criteria.
    if score >= 12: return "Unacceptable"
    if score >= 5:  return "ALARP - review benefit/risk"
    return "Acceptable"
