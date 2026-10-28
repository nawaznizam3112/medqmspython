"""Bridge between the EU MDR classifier page and the QMS device register.
In your classifier page, once a result is final, call:
    import classification
    classification.publish("Implant A", "IIa", "Rule 8", purpose="...", rationale="...")
The Technical Documentation page then offers a one-click import."""
import streamlit as st

CLASSES = ["I", "Is", "Im", "Ir", "IIa", "IIb", "III"]

ROUTES = {
 "I":  ("Self-declaration: Annex II/III technical documentation + Annex IV DoC (Art. 52(7)). No Notified Body.", "Self-declaration (Art. 52(7))"),
 "Is": ("Self-declaration, but a Notified Body must assess the sterility aspects (Annex IX Ch. I, or Annex XI Part A).", "Annex IX or XI-A, NB limited to sterility"),
 "Im": ("Self-declaration, but a Notified Body must assess the metrological aspects (Annex IX Ch. I, or Annex XI Part A).", "Annex IX or XI-A, NB limited to measuring function"),
 "Ir": ("Self-declaration, but a Notified Body must assess the reuse/reprocessing aspects (Annex IX Ch. I, or Annex XI Part A).", "Annex IX or XI-A, NB limited to reuse aspects"),
 "IIa": ("Art. 52(6): Annex IX Ch. I + III (technical documentation assessed for at least one representative device per category), or Annex II/III + Annex XI Part A. Note: Rule 8 puts implantable devices placed in the teeth in IIa.", "Annex IX Ch. I+III (sampling per category)"),
 "IIb": ("Art. 52(4): Annex IX Ch. I + III (technical documentation of at least one representative device per generic device group), or Annex X type-examination + Annex XI Part A. Implantable IIb normally need technical documentation assessed for every device (exceptions listed in Art. 52(4)).", "Annex IX Ch. I+III (sampling per generic group)"),
 "III": ("Art. 52(3): Annex IX Ch. I + III with technical documentation assessed for every device, or Annex X + Annex XI Part A. Clinical evaluation consultation procedure may apply (Annex IX §5.1).", "Annex IX Ch. I+III (every device)"),
}

def route_hint(cls): return ROUTES[cls][0]
def default_route(cls): return ROUTES[cls][1]

def publish(device, mdr_class, rule, purpose="", rationale=""):
    st.session_state["classification_result"] = dict(device=device, mdr_class=mdr_class, rule=rule, purpose=purpose, rationale=rationale)

def pending():
    return st.session_state.get("classification_result")
