"""Sidebar access panel: Member (default) and Admin (passcode)."""
import time

import streamlit as st

from .. import auth

MAX_FAILS, LOCK_SECONDS = 5, 60


def render() -> None:
    role = st.session_state.get("role", "member")
    st.markdown(f"**Role:** {'🛡️ Admin' if role == 'admin' else '👤 Member'}")
    if role == "admin":
        if st.button("Sign out of admin", key="admin_out"):
            st.session_state["role"] = "member"
            st.rerun()
        return
    with st.expander("🔐 Admin access"):
        if not auth.is_configured():
            st.caption("No admin passcode yet. The person who owns this installation creates one (8+ characters).")
            a = st.text_input("New passcode", type="password", key="adm_new")
            b = st.text_input("Repeat passcode", type="password", key="adm_new2")
            if st.button("Create admin passcode", key="adm_create"):
                if a != b:
                    st.error("The two passcodes differ.")
                else:
                    try:
                        auth.set_passcode(a)
                        st.session_state["role"] = "admin"
                        st.rerun()
                    except (ValueError, PermissionError) as exc:
                        st.error(str(exc))
            return
        locked_until = st.session_state.get("locked_until", 0)
        if time.time() < locked_until:
            st.error(f"Too many attempts. Try again in {int(locked_until - time.time())} seconds.")
            return
        code = st.text_input("Admin passcode", type="password", key="adm_code")
        if st.button("Sign in", key="adm_in"):
            if auth.verify(code):
                st.session_state.update(role="admin", failed_logins=0)
                st.rerun()
            fails = st.session_state.get("failed_logins", 0) + 1
            st.session_state["failed_logins"] = fails
            if fails >= MAX_FAILS:
                st.session_state.update(locked_until=time.time() + LOCK_SECONDS, failed_logins=0)
            st.error("That passcode is not correct.")
