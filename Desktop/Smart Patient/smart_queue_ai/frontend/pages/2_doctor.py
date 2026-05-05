import streamlit as st
from config import ANTI_GRAVITY_CSS
from datetime import datetime
import requests
from utils import render_sidebar

st.set_page_config(page_title="Doctor Dashboard", page_icon="🩺", layout="wide")
st.markdown(ANTI_GRAVITY_CSS, unsafe_allow_html=True)

if not st.session_state.get("token") or st.session_state.user["role"] != "doctor":
    st.warning("Please login as a doctor.")
    st.stop()

render_sidebar()
api = st.session_state.api
user = st.session_state.user

st.markdown(f"<h1 style='border-bottom: 2px solid #06B6D4; padding-bottom: 10px;'>{user['name']}</h1>", unsafe_allow_html=True)

def get_doc_queue():
    url = f"{api.base_url}/doctor/queue"
    res = requests.get(url, headers=api._headers())
    return res.json() if res.status_code == 200 else []

doc_q = get_doc_queue()

st.subheader("Live Queue")
if doc_q:
    for q in doc_q:
        bg_color = "rgba(124,58,237,0.3)" if q["status"] == "in_progress" else "rgba(255,255,255,0.05)"
        border_color = "#7C3AED" if q["status"] == "in_progress" else "rgba(255,255,255,0.1)"
        box_shadow = "0 0 20px rgba(124,58,237,0.5)" if q["status"] == "in_progress" else "none"
        
        st.markdown(f"""
        <div style="background:{bg_color}; border:1px solid {border_color}; box-shadow:{box_shadow}; border-radius:12px; padding:15px; margin-bottom:10px;">
            <h3>Token #{q['token']} — {q['patient_name']}</h3>
            <p><strong>Priority:</strong> {q['priority']}/5 | <strong>Wait:</strong> {int(q['wait_time'])} mins</p>
            <p><em>{q['symptoms']}</em></p>
        </div>
        """, unsafe_allow_html=True)
        
        if q["status"] == "in_progress":
            if st.button(f"Complete Appointment - Token {q['token']}", key=f"complete_{q['id']}"):
                api.call_next(0)
                st.rerun()
        elif q["status"] == "waiting" and doc_q[0] == q:
            if st.button(f"Call Next - Token {q['token']}", key=f"call_{q['id']}"):
                api.call_next(q["id"])
                st.rerun()
else:
    st.info("No patients in queue.")

st.markdown("---")
st.subheader("Today's Appointments")
appts = api.get_appointments("doctor")
if appts:
    st.dataframe([{
        "Token": a["token_number"],
        "Time": a["appointment_time"],
        "Patient ID": a["patient_id"],
        "Status": a["status"]
    } for a in appts])

st.markdown("---")
st.subheader("Manage Leaves & Utilization")

clinics = api.get_clinics()
col_u, col_l = st.columns(2)

with col_u:
    st.markdown("#### Doctor Utilization %")
    if clinics:
        c_opts = {c['name']: c['id'] for c in clinics}
        u_clinic = st.selectbox("Select Clinic", list(c_opts.keys()), key="u_clinic")
        if st.button("Check Utilization"):
            u_data = api.get_doctor_utilization(c_opts[u_clinic])
            if u_data:
                st.metric("Utilization", f"{u_data.get('utilization_percent', 0)}%")
                st.write(f"Booked Slots: {u_data.get('booked_slots', 0)} / Total Slots: {u_data.get('total_slots', 0)}")
    else:
        st.info("No clinics available")

with col_l:
    st.markdown("#### Add Leave")
    start_d = st.date_input("Start Date")
    end_d = st.date_input("End Date")
    reason = st.text_input("Reason")
    if st.button("Submit Leave"):
        res = api.add_doctor_leave(start_d.strftime("%Y-%m-%d"), end_d.strftime("%Y-%m-%d"), reason)
        if res:
            st.success("Leave Added successfully!")
