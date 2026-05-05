import streamlit as st
from config import ANTI_GRAVITY_CSS
from datetime import datetime
from utils import render_sidebar

st.set_page_config(page_title="Patient Dashboard", page_icon="👤", layout="wide")
st.markdown(ANTI_GRAVITY_CSS, unsafe_allow_html=True)

if not st.session_state.get("token") or st.session_state.user["role"] != "patient":
    st.warning("Please login as a patient.")
    st.stop()

from api_client import APIClient
from config import API_BASE

api = APIClient(API_BASE, token=st.session_state.get("token"))
st.session_state.api = api
user = st.session_state.user

st.markdown(f"<h1>Welcome, {user['name']} 👋</h1>", unsafe_allow_html=True)

# Profile and Score
profile = api.get_patient_profile()
score = profile.get("priority_score", 1) if profile else 1

colors = {1: "green", 2: "green", 3: "yellow", 4: "orange", 5: "red"}
badge_color = colors.get(score, "gray")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(f"<div class='metric-card'><h4>Priority Score</h4><h2><span style='color:{badge_color};'>{score}</span>/5</h2></div>", unsafe_allow_html=True)
with col2:
    appts = api.get_appointments("patient")
    st.markdown(f"<div class='metric-card'><h4>Total Appointments</h4><h2>{len(appts)}</h2></div>", unsafe_allow_html=True)
with col3:
    today_str = datetime.today().strftime("%Y-%m-%d")
    next_appt = next((a for a in appts if a["status"] in ["booked", "scheduled", "waiting"] and a["appointment_date"] >= today_str), None)
    date_str = next_appt["appointment_date"] if next_appt else "None"
    st.markdown(f"<div class='metric-card'><h4>Next Appointment</h4><h2>{date_str}</h2></div>", unsafe_allow_html=True)
with col4:
    wait = next_appt["predicted_wait_mins"] if next_appt else 0
    st.markdown(f"<div class='metric-card'><h4>Estimated Wait</h4><h2>{int(wait)} mins</h2></div>", unsafe_allow_html=True)

st.markdown("---")

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Update Symptoms")
    current_symp = profile.get("symptoms", "") if profile else ""
    symptoms = st.text_area("Describe your symptoms", value=current_symp)
    if st.button("Analyze & Update"):
        res = api.update_patient_profile(symptoms)
        if res:
            st.success(f"Updated! New Priority Score: {res['priority_score']}")
            st.rerun()

    st.markdown("---")
    st.subheader("Browse Clinic Availability")
    search_spec = st.text_input("Search by Speciality (e.g. Cardiology)")
    search_doc = st.text_input("Search by Doctor Name")
    if st.button("Search Availability"):
        avail = api.search_doctor_availability(specialization=search_spec, doctor_name=search_doc)
        if avail:
            st.dataframe(avail)
        else:
            st.info("No availability found.")

    st.markdown("---")
    st.subheader("Book Appointment")
    clinics = api.get_clinics()
    if clinics:
        clinic_options = {c['name']: c['id'] for c in clinics}
        selected_clinic_name = st.selectbox("Select Clinic", list(clinic_options.keys()))
        clinic_id = clinic_options[selected_clinic_name]

        date = st.date_input("Date", min_value=datetime.today())
        day_name = date.strftime("%A")

        doctors = api.get_doctors(clinic_id=clinic_id, day_of_week=day_name)
        doc_options = {f"{d['user']['name']} ({d['specialization']})": d['id'] for d in doctors}
        
        if doc_options:
            selected_doc = st.selectbox("Select Doctor", list(doc_options.keys()))
            doc_id = doc_options[selected_doc]
            
            # Generate 15-min slots for UI (9 AM to 5 PM)
            time_slots = []
            for h in range(9, 17):
                for m in [0, 15, 30, 45]:
                    time_slots.append(f"{h:02d}:{m:02d}")
            
            selected_time = st.selectbox("Select 15-Min Slot", time_slots)
            
            book_symp = st.text_input("Symptoms for this visit", value=symptoms)
            
            if st.button("Book"):
                res = api.book_appointment(doc_id, clinic_id, date.strftime("%Y-%m-%d"), selected_time, book_symp)
                if res:
                    st.success(f"Booked! Token: {res['token_number']} at {selected_clinic_name}")
                    st.rerun()
    else:
        st.warning("No clinics available in the system yet.")

with col_right:
    st.subheader("Live Queue Position")
    if doc_options:
        sel_q_doc = st.selectbox("Check Queue for Doctor", list(doc_options.keys()), key="q_doc")
        doc_id = doc_options[sel_q_doc]
        if st.button("Refresh Queue"):
            q_res = api.get_queue(doc_id)
            curr = q_res.get("current_token")
            st.info(f"Currently Serving Token: **{curr if curr else 'None'}**")
            
            today_str = datetime.today().strftime("%Y-%m-%d")
            my_appt = next((a for a in appts if a["doctor_id"] == doc_id and a["status"] in ["booked", "scheduled", "waiting"] and a["appointment_date"] >= today_str), None)
            if my_appt:
                st.success(f"Your Token: **{my_appt['token_number']}**")
            else:
                st.warning("You have no active appointment today for this doctor.")

st.markdown("---")
st.subheader("My Appointments")
if appts:
    st.dataframe([{
        "Date": a["appointment_date"],
        "Time": a["appointment_time"],
        "Token": a["token_number"],
        "Wait (mins)": int(a["predicted_wait_mins"]),
        "Status": a["status"],
        "Priority": a["priority_score"]
    } for a in appts])
else:
    st.info("No appointments found.")
