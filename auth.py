"""Login, roles, lockout and e-signature (password re-entry) for the QMS.
Roles: Admin (everything + users), QA (create/edit records), Viewer (read-only)."""
import hashlib, hmac, os
import streamlit as st
import db

ROLES = ["Admin", "QA", "Viewer"]
ITER, MAX_FAILS, MIN_PW = 200_000, 5, 10

def hash_pw(pw):
    salt = os.urandom(16)
    return salt.hex() + "$" + hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, ITER).hex()

def _check(pw, stored):
    salt_hex, h = stored.split("$")
    calc = hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt_hex), ITER).hex()
    return hmac.compare_digest(calc, h)

def _setup():
    st.title("🔐 First-run setup")
    st.info("No users exist yet. Create the administrator account.")
    with st.form("setup"):
        u = st.text_input("Username")
        n = st.text_input("Full name")
        p1 = st.text_input(f"Password (min {MIN_PW} chars)", type="password")
        p2 = st.text_input("Repeat password", type="password")
        if st.form_submit_button("Create admin"):
            if not u or len(p1) < MIN_PW or p1 != p2:
                st.error(f"Username required; password must be at least {MIN_PW} characters and match.")
            else:
                rid = db.execute("INSERT INTO users(username,full_name,role,pw_hash) VALUES(?,?,?,?)", (u, n, "Admin", hash_pw(p1)))
                db.log("CREATE", "users", rid, f"first admin {u}", user=u)
                st.rerun()
    st.stop()

def _login():
    st.title("🔐 Sign in")
    with st.form("login"):
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.form_submit_button("Sign in"):
            rows = db.query("SELECT * FROM users WHERE username=?", (u,))
            row = rows[0] if rows else None
            if not row or not row["active"]:
                db.log("LOGIN_FAILED", "users", 0, f"unknown/inactive: {u}", user=u or "?")
                st.error("Invalid credentials.")
            elif row["failed"] >= MAX_FAILS:
                st.error("Account locked after repeated failures. Ask an Admin to unlock it.")
            elif _check(p, row["pw_hash"]):
                db.execute("UPDATE users SET failed=0 WHERE id=?", (row["id"],))
                st.session_state.user = {"id": row["id"], "username": row["username"], "full_name": row["full_name"], "role": row["role"]}
                db.log("LOGIN", "users", row["id"])
                st.rerun()
            else:
                db.execute("UPDATE users SET failed=failed+1 WHERE id=?", (row["id"],))
                db.log("LOGIN_FAILED", "users", row["id"], user=u)
                st.error("Invalid credentials.")
    st.stop()

def require(min_role=None):
    db.init()
    if not db.query("SELECT 1 FROM users LIMIT 1"):
        _setup()
    if "user" not in st.session_state:
        _login()
    u = st.session_state.user
    with st.sidebar:
        st.markdown(f"**{u['full_name'] or u['username']}** · {u['role']}")
        if st.button("Sign out"):
            db.log("LOGOUT", "users", u["id"])
            del st.session_state["user"]
            st.rerun()
        with st.expander("Change password"):
            with st.form("chpw", clear_on_submit=True):
                old, new = st.text_input("Current", type="password"), st.text_input("New", type="password")
                if st.form_submit_button("Change"):
                    r = db.query("SELECT pw_hash FROM users WHERE id=?", (u["id"],))[0]
                    if _check(old, r["pw_hash"]) and len(new) >= MIN_PW:
                        db.execute("UPDATE users SET pw_hash=? WHERE id=?", (hash_pw(new), u["id"]))
                        db.log("PASSWORD_CHANGE", "users", u["id"])
                        st.success("Changed.")
                    else:
                        st.error(f"Wrong current password or new one shorter than {MIN_PW}.")
    if min_role == "Admin" and u["role"] != "Admin":
        st.error("Admins only.")
        st.stop()
    return u

def sign(pw, meaning, table, rid):
    """Electronic signature = authenticated user re-enters password; logged with its meaning."""
    u = st.session_state.get("user")
    if not u or not pw:
        return False
    row = db.query("SELECT pw_hash FROM users WHERE id=?", (u["id"],))[0]
    ok = _check(pw, row["pw_hash"])
    db.log("E-SIGN" if ok else "E-SIGN_FAILED", table, rid, meaning)
    return ok
