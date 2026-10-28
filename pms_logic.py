"""Pure functions for PMS scheduling and Art. 88-style trend detection (unit-testable, no Streamlit)."""
import numpy as np
import pandas as pd

# Art. 85/86: Class I = PMS report, updated when necessary; IIa = PSUR when necessary, at least every 2 years;
# IIb and III = PSUR at least annually. Verify against the current regulation text.
REPORT_DAYS = {"I": None, "Is": None, "Im": None, "Ir": None, "IIa": 730, "IIb": 365, "III": 365}

def report_kind(cls):
    return "PMS report (Art. 85)" if cls in ("I", "Is", "Im", "Ir") else "PSUR (Art. 86)"

def monthly_table(complaints, sales, baseline):
    """complaints: DataFrame with 'awareness_date' (ISO). sales: DataFrame with 'period' (YYYY-MM) and 'units'.
    Illustrative Poisson control chart: signal when monthly count > expected + 3*sqrt(max(expected, 1)),
    or when 3 consecutive months exceed expected. Baseline months are not tested."""
    if complaints.empty:
        return None
    per = complaints.awareness_date.str[:7]
    counts = per.value_counts().sort_index()
    sales_s = sales.set_index("period").units if len(sales) else pd.Series(dtype=float)
    first = min(list(counts.index) + list(sales_s.index))
    last = max(list(counts.index) + list(sales_s.index))
    periods = pd.period_range(first, last, freq="M").astype(str)
    out = pd.DataFrame(index=periods)
    out["complaints"] = counts.reindex(periods).fillna(0).astype(int)
    out["units"] = sales_s.reindex(periods)
    base = out.iloc[:baseline]
    have_units = out.units.notna().all() and base.units.sum() > 0
    if have_units:
        out["expected"] = base.complaints.sum() / base.units.sum() * out.units
        basis = "complaint rate per unit sold"
    else:
        out["expected"] = base.complaints.mean()
        basis = "mean monthly count (no complete sales data)"
    out["UCL"] = out.expected + 3 * np.sqrt(np.maximum(out.expected, 1))
    out["signal"] = out.complaints > out.UCL
    out["run3"] = (out.complaints > out.expected).rolling(3).sum() == 3
    out.iloc[:baseline, out.columns.get_indexer(["signal", "run3"])] = False
    out.attrs["basis"] = basis
    return out
