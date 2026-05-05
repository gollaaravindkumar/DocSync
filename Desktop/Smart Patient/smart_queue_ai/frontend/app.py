import streamlit as st
from config import ANTI_GRAVITY_CSS, API_BASE
from api_client import APIClient
from utils import render_sidebar

st.set_page_config(page_title="DocSync", page_icon="🏥", layout="wide")
st.markdown(ANTI_GRAVITY_CSS, unsafe_allow_html=True)

if "token" not in st.session_state:
    st.session_state.token = None
if "user" not in st.session_state:
    st.session_state.user = None
if "api" not in st.session_state:
    st.session_state.api = APIClient(API_BASE)

if not st.session_state.token:
    st.sidebar.markdown("<h1 style='color: #7C3AED; text-shadow: 0 0 10px #7C3AED;'>🏥 DocSync</h1>", unsafe_allow_html=True)
    st.sidebar.subheader("Authentication")
    auth_mode = st.sidebar.radio("Select Mode", ["Login", "Register"], horizontal=True)
    
    if auth_mode == "Login":
        with st.sidebar.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")
            
            if submit:
                res = st.session_state.api.login(email, password)
                if res:
                    st.session_state.token = res["access_token"]
                    st.session_state.user = res["user"]
                    st.session_state.api.token = res["access_token"]
                    st.rerun()
    else:
        with st.sidebar.form("register_form"):
            name = st.text_input("Name")
            email = st.text_input("Email")
            phone = st.text_input("Phone")
            password = st.text_input("Password", type="password")
            role = st.selectbox("Role", ["patient", "doctor", "receptionist", "admin"])
            submit = st.form_submit_button("Register")
            
            if submit:
                res = st.session_state.api.register(name, email, phone, password, role)
                if res:
                    st.success("Registration successful! Please login.")
                    

    st.title("Welcome to DocSync 🚀")
    st.write("Revolutionizing patient wait times with AI and real-time tracking.")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("<div class='metric-card'><h3>🤖 AI Wait Prediction</h3><p>Get accurate estimated wait times powered by scikit-learn.</p></div>", unsafe_allow_html=True)
    with col2:
        st.markdown("<div class='metric-card'><h3>🚨 Priority Queue</h3><p>Smart triaging based on symptoms severity.</p></div>", unsafe_allow_html=True)
    with col3:
        st.markdown("<div class='metric-card'><h3>📊 Real-Time Tracking</h3><p>Live queue status directly on your phone.</p></div>", unsafe_allow_html=True)

else:
    role = st.session_state.user.get('role', '')
    if role == "patient":
        st.switch_page("pages/1_patient.py")
    elif role == "doctor":
        st.switch_page("pages/2_doctor.py")
    elif role == "admin":
        st.switch_page("pages/3_admin.py")
    elif role == "receptionist":
        st.switch_page("pages/4_receptionist.py")
    else:
        render_sidebar()
        st.title("DocSync Dashboard")
        st.write("Role not recognized. Please use the sidebar to navigate.")
