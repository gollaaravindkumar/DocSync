import streamlit as st
from config import ANTI_GRAVITY_CSS
import requests
from utils import render_sidebar

st.set_page_config(page_title="Receptionist Dashboard", page_icon="💁", layout="wide")
st.markdown(ANTI_GRAVITY_CSS, unsafe_allow_html=True)

if not st.session_state.get("token") or st.session_state.user["role"] != "receptionist":
    st.warning("Please login as a receptionist.")
    st.stop()

render_sidebar()
api = st.session_state.api
st.markdown("<h1 style='text-shadow: 0 0 15px #06B6D4;'>Reception Desk</h1>", unsafe_allow_html=True)

st.subheader("Today's Appointments")
appts = api.get_appointments("receptionist")

if appts:
    for a in appts:
        col1, col2, col3, col4, col5 = st.columns([1,2,2,2,2])
        col1.write(f"#{a['token_number']}")
        col2.write(a['appointment_time'])
        col3.write(f"Doc: {a['doctor_id']} | Pat: {a['patient_id']}")
        col4.write(a['status'])
        
        if a['status'] in ["scheduled", "booked"]:
            if col5.button("Check-In", key=f"chk_{a['id']}"):
                api.checkin(a['id'])
                st.rerun()
        elif a['status'] == "waiting":
            col5.success("Checked In ✓")
else:
    st.info("No appointments today.")

st.markdown("---")
st.subheader("All Doctor Queues")
def get_all_queues():
    url = f"{api.base_url}/receptionist/queue"
    res = requests.get(url, headers=api._headers())
    return res.json() if res.status_code == 200 else []

queues = get_all_queues()
if queues:
    cols = st.columns(len(queues))
    for i, q in enumerate(queues):
        with cols[i]:
            st.markdown(f"""
            <div class='metric-card'>
                <h4>{q['doctor_name']}</h4>
                <p>Waiting: <strong>{q['waiting_count']}</strong></p>
                <p>Now Serving: <strong>#{q['current_token'] if q['current_token'] else 'None'}</strong></p>
            </div>
            """, unsafe_allow_html=True)
