import streamlit as st
import time
from config import ANTI_GRAVITY_CSS
from utils import render_sidebar

st.set_page_config(page_title="Live Queue Board", page_icon="📺", layout="wide")
st.markdown(ANTI_GRAVITY_CSS, unsafe_allow_html=True)

api = st.session_state.get("api")
if not api:
    st.warning("Please login first on the main page.")
    st.stop()

render_sidebar()
st.title("Live Queue Board")

doctors = api.get_doctors()
doc_options = {f"{d['user']['name']} ({d['specialization']})": d['id'] for d in doctors}

if doc_options:
    doc_id = st.selectbox("Select Doctor", list(doc_options.values()), format_func=lambda x: [k for k, v in doc_options.items() if v == x][0])
    
    board = st.empty()
    
    with board.container():
        q_data = api.get_queue(doc_id)
        curr = q_data.get("current_token")
        
        st.markdown(f"""
        <div style='text-align:center; padding: 50px; background: rgba(6,182,212,0.1); border-radius: 20px; border: 2px solid #06B6D4; box-shadow: 0 0 30px rgba(6,182,212,0.4); margin-bottom: 30px;'>
            <h2 style='color:#ccc;'>Now Serving</h2>
            <h1 style='font-size: 72px; color: #06B6D4; text-shadow: 0 0 20px #06B6D4; margin:0;'>Token #{curr if curr else '--'}</h1>
        </div>
        """, unsafe_allow_html=True)
        
        st.subheader("Next in Queue")
        waiting = q_data.get("waiting", [])[:10]
        
        for w in waiting:
            color = "rgba(255,255,255,0.05)"
            border = "rgba(255,255,255,0.1)"
            if w['priority'] >= 4:
                color = "rgba(255,0,0,0.2)"
                border = "red"
            elif w['priority'] == 3:
                color = "rgba(255,165,0,0.2)"
                border = "orange"
            else:
                color = "rgba(0,128,0,0.2)"
                border = "green"
                
            st.markdown(f"""
            <div style='background:{color}; border-left: 5px solid {border}; padding: 15px; margin-bottom: 10px; border-radius: 5px;'>
                <h3 style='margin:0;'>Token #{w['token']} <span style='float:right; font-size:16px; color:#aaa;'>Est. Wait: {int(w['wait_time'])} mins</span></h3>
            </div>
            """, unsafe_allow_html=True)
            
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔄 Refresh Live Queue", use_container_width=True):
            st.rerun()
            
    import streamlit.components.v1 as components
    
    clean_doc_name = [k.split(" (")[0] for k, v in doc_options.items() if v == doc_id][0]
    
    components.html(f"""
    <script>
        // WebSockets Logic
        var ws = new WebSocket("ws://localhost:8000/queue/ws/{doc_id}");
        ws.onmessage = function(event) {{
            var buttons = window.parent.document.querySelectorAll('button');
            for (var i = 0; i < buttons.length; i++) {{
                if (buttons[i].innerText.includes('Refresh Live Queue')) {{
                    buttons[i].click();
                    break;
                }}
            }}
        }};

        // Text-to-Speech Logic
        const currToken = "{curr if curr else ''}";
        const doctorName = "{clean_doc_name}";
        const lastSpokenKey = "lastSpokenToken_{doc_id}";
        const lastSpoken = window.parent.sessionStorage.getItem(lastSpokenKey);
        
        if (currToken !== "" && currToken !== lastSpoken) {{
            window.parent.sessionStorage.setItem(lastSpokenKey, currToken);
            
            setTimeout(() => {{
                let msg = new SpeechSynthesisUtterance("Token Number " + currToken + ", please go to " + doctorName + "'s room.");
                msg.rate = 0.85;
                msg.pitch = 1.0;
                window.parent.speechSynthesis.speak(msg);
            }}, 500);
        }}
    </script>
    """, height=0)

