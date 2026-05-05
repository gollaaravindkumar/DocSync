import streamlit as st
from config import ANTI_GRAVITY_CSS
from utils import render_sidebar

st.set_page_config(page_title="Admin Dashboard", page_icon="⚙️", layout="wide")
st.markdown(ANTI_GRAVITY_CSS, unsafe_allow_html=True)

if not st.session_state.get("token") or st.session_state.user["role"] != "admin":
    st.warning("Please login as an admin.")
    st.stop()

render_sidebar()
api = st.session_state.api
st.markdown("<h1 style='text-shadow: 0 0 15px #7C3AED;'>Admin Control Panel</h1>", unsafe_allow_html=True)

stats = api.get_admin_stats()
if stats:
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"<div class='metric-card'><h4>Total Patients</h4><h2>{stats.get('total_patients', 0)}</h2></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='metric-card'><h4>Avg Wait Time</h4><h2>{int(stats.get('avg_wait_time_today', 0))} mins</h2></div>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"<div class='metric-card'><h4>Total Doctors</h4><h2>{stats.get('total_doctors', 0)}</h2></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='metric-card'><h4>Currently Waiting</h4><h2>{stats.get('currently_waiting', 0)}</h2></div>", unsafe_allow_html=True)
    with col3:
        st.markdown(f"<div class='metric-card'><h4>Appointments Today</h4><h2>{stats.get('total_appointments_today', 0)}</h2></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='metric-card'><h4>Busiest Doctor</h4><h2>{stats.get('busiest_doctor', 'None')}</h2></div>", unsafe_allow_html=True)

st.markdown("---")
st.subheader("📈 Real-Time Analytics")

import requests
import pandas as pd

# Fetch Analytics
analytics_res = requests.get(f"{api.base_url}/admin/analytics", headers=api._headers())
if analytics_res.status_code == 200:
    analytics = analytics_res.json()
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Patient Priority Distribution")
        priority_data = analytics.get("priority_distribution", {})
        # Rename keys for better display
        labels = {1: "1-Low", 2: "2-Moderate", 3: "3-High", 4: "4-Urgent", 5: "5-Critical"}
        df_priority = pd.DataFrame({
            "Priority": [labels.get(int(k), k) for k in priority_data.keys()],
            "Count": list(priority_data.values())
        }).set_index("Priority")
        st.bar_chart(df_priority, color="#7C3AED")
        
    with col2:
        st.markdown("#### Appointment Statuses")
        status_data = analytics.get("status_distribution", {})
        df_status = pd.DataFrame({
            "Status": [k.capitalize() for k in status_data.keys()],
            "Count": list(status_data.values())
        }).set_index("Status")
        st.bar_chart(df_status, color="#06B6D4")

st.markdown("---")
st.subheader("All Appointments")
appts = api.get_appointments("admin")
if appts:
    st.dataframe([{
        "Date": a["appointment_date"],
        "Time": a["appointment_time"],
        "Doctor ID": a["doctor_id"],
        "Patient ID": a["patient_id"],
        "Status": a["status"]
    } for a in appts])

st.markdown("---")
st.subheader("🏥 Clinic & Doctor Management")

if "admin_msg" in st.session_state:
    st.success(st.session_state.admin_msg)
    del st.session_state.admin_msg

col_c, col_l, col_u = st.columns(3)

with col_c:
    st.markdown("#### Clinics")
    clinics = api.get_clinics()
    if clinics:
        st.dataframe([{"ID": c["id"], "Name": c["name"], "Address": c["address"]} for c in clinics], hide_index=True)
        
        st.markdown("##### Remove Clinic")
        del_c_opts = {c['name']: c['id'] for c in clinics}
        del_clinic_name = st.selectbox("Select Clinic to Remove", list(del_c_opts.keys()))
        if st.button("Remove Clinic"):
            res = api.delete_clinic(del_c_opts[del_clinic_name])
            if res:
                st.session_state.admin_msg = f"Clinic '{del_clinic_name}' removed successfully!"
                st.rerun()
    else:
        st.info("No clinics found.")
        
    st.markdown("##### Add New Clinic")
    new_c_name = st.text_input("Clinic Name")
    new_c_addr = st.text_input("Clinic Address")
    if st.button("Add Clinic"):
        if new_c_name and new_c_addr:
            res = api.add_clinic(new_c_name, new_c_addr)
            if res:
                st.session_state.admin_msg = "Clinic added successfully!"
                st.rerun()
        else:
            st.error("Please fill all fields")

with col_l:
    st.markdown("#### Doctors by Clinic")
    if clinics:
        c_opts_l = {c['name']: c['name'] for c in clinics}
        filter_clinic = st.selectbox("Filter by Clinic", ["All"] + list(c_opts_l.keys()))
        
        docs = api.search_doctor_availability()
        if docs:
            if filter_clinic != "All":
                docs = [d for d in docs if d["clinic_name"] == filter_clinic]
                
            unique_docs = {}
            for d in docs:
                unique_docs[d["doctor_name"]] = {"Name": d["doctor_name"], "Specialization": d["speciality"], "Clinic": d["clinic_name"]}
            
            if unique_docs:
                st.dataframe(list(unique_docs.values()), hide_index=True)
            else:
                st.info("No doctors found for this clinic.")
        else:
            st.info("No doctors scheduled yet.")
    else:
        st.info("Add a clinic first.")

with col_u:
    st.markdown("#### Add Doctor to Clinic")
    if clinics:
        c_opts = {c['name']: c['id'] for c in clinics}
        a_clinic = st.selectbox("Select Clinic", list(c_opts.keys()), key="a_clinic")
        
        a_name = st.text_input("Doctor Name")
        a_email = st.text_input("Doctor Email")
        a_pass = st.text_input("Password (min 6 chars)", type="password")
        a_spec = st.text_input("Specialization (e.g. Gynecology)")
        a_exp = st.number_input("Experience Years", min_value=1, value=5)
        
        days_opts = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        a_days = st.multiselect("Working Days", days_opts, default=["Monday", "Wednesday", "Friday"])
        
        if st.button("Add Doctor"):
            if not a_name or not a_email or not a_pass or not a_spec:
                st.error("Please fill all fields")
            else:
                res = api.add_doctor_to_clinic(a_name, a_email, a_pass, a_spec, a_exp, c_opts[a_clinic], a_days)
                if res:
                    st.session_state.admin_msg = f"Doctor {a_name} added to {a_clinic} successfully!"
                    st.rerun()
