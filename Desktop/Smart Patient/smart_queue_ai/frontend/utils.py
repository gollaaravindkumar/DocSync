import streamlit as st

def render_sidebar():
    st.sidebar.markdown("<h1 style='color: #7C3AED; text-shadow: 0 0 10px #7C3AED;'>🏥 DocSync</h1>", unsafe_allow_html=True)
    
    if st.session_state.get("token") and st.session_state.get("user"):
        user = st.session_state.user
        st.sidebar.markdown(f"**Logged in as:** {user['name']}")
        st.sidebar.markdown(f"<span style='background:#7C3AED; color: white; padding:2px 8px; border-radius:10px;'>{user['role'].upper()}</span>", unsafe_allow_html=True)
        st.sidebar.markdown("<br>", unsafe_allow_html=True)
        if st.sidebar.button("Logout", key="logout_btn"):
            st.session_state.token = None
            st.session_state.user = None
            if "api" in st.session_state:
                st.session_state.api.token = None
            st.rerun()
