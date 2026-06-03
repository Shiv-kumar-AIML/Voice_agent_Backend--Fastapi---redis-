import streamlit as st
import threading
from vapi_python import Vapi
import time
import requests
import os
from dotenv import load_dotenv

load_dotenv()

# --- Configuration ---
VAPI_API_KEY = os.getenv("VAPI_API_KEY")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")

# --- UI Setup ---
st.set_page_config(
    page_title="Voice Assistant",
    page_icon="🎙️",
    layout="centered"
)

if "call_active" not in st.session_state:
    st.session_state.call_active = False

if "vapi_instance" not in st.session_state:
    st.session_state.vapi_instance = None

# --- Advanced CSS Styling ---
st.markdown("""
<style>
/* Hide standard Streamlit header/footer */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* Deep dark background */
.stApp {
    background-color: #06070B;
}

/* Base text styling */
.title-text {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    color: white;
    text-align: center;
    font-weight: 600;
    font-size: 28px;
    margin-top: 20px;
}
.subtitle-text {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    color: #8b5cf6;
    text-align: center;
    font-size: 16px;
    font-weight: 400;
    margin-top: -10px;
    margin-bottom: 40px;
}

/* Glowing Orb */
.orb-container {
    display: flex;
    justify-content: center;
    align-items: center;
    margin: 40px 0;
}
.orb {
    width: 220px;
    height: 220px;
    border-radius: 50%;
    background: radial-gradient(circle, #0e1222 0%, #06070b 100%);
    box-shadow: 0 0 40px rgba(58, 130, 246, 0.4), inset 0 0 40px rgba(139, 92, 246, 0.4);
    border: 1px solid rgba(139, 92, 246, 0.3);
    display: flex;
    justify-content: center;
    align-items: center;
}

.orb.active {
    animation: pulse 2s infinite cubic-bezier(0.4, 0, 0.2, 1);
    box-shadow: 0 0 60px rgba(58, 130, 246, 0.9), inset 0 0 60px rgba(139, 92, 246, 0.9);
    border: 2px solid rgba(139, 92, 246, 0.8);
}

@keyframes pulse {
    0% { transform: scale(1); }
    50% { transform: scale(1.05); }
    100% { transform: scale(1); }
}

/* Soundwaves */
.soundwave {
    display: flex;
    align-items: center;
    gap: 6px;
}
.bar {
    width: 4px;
    background: #fff;
    border-radius: 2px;
    height: 4px;
}
.active .bar {
    background: linear-gradient(180deg, #3a82f6 0%, #8b5cf6 100%);
    animation: bounce 0.8s infinite alternate ease-in-out;
}
@keyframes bounce {
    0% { height: 10px; }
    100% { height: 60px; }
}
.active .bar:nth-child(1) { height: 20px; animation-delay: 0.1s; }
.active .bar:nth-child(2) { height: 40px; animation-delay: 0.2s; }
.active .bar:nth-child(3) { height: 30px; animation-delay: 0.3s; }
.active .bar:nth-child(4) { height: 50px; animation-delay: 0.4s; }
.active .bar:nth-child(5) { height: 60px; animation-delay: 0.5s; }
.active .bar:nth-child(6) { height: 40px; animation-delay: 0.6s; }
.active .bar:nth-child(7) { height: 30px; animation-delay: 0.7s; }
.active .bar:nth-child(8) { height: 50px; animation-delay: 0.8s; }
.active .bar:nth-child(9) { height: 20px; animation-delay: 0.9s; }

/* Mic Button Override */
div.stButton {
    display: flex;
    justify-content: center;
    margin-top: 30px;
}
div.stButton > button {
    border-radius: 50px !important;
    width: 70px !important;
    height: 70px !important;
    border: none !important;
    color: transparent !important;
    transition: all 0.3s ease !important;
    display: flex !important;
    justify-content: center !important;
    align-items: center !important;
}
div.stButton > button p {
    font-size: 28px !important;
    margin: 0 !important;
    color: white !important;
}
div.stButton > button:hover {
    transform: scale(1.1);
}
</style>
""", unsafe_allow_html=True)

# Dynamic CSS based on state
if st.session_state.call_active:
    st.markdown("""
    <style>
    div.stButton > button {
        background: linear-gradient(135deg, #f87171 0%, #ef4444 100%) !important;
        box-shadow: 0 0 30px rgba(239, 68, 68, 0.6) !important;
    }
    </style>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <style>
    div.stButton > button {
        background: linear-gradient(135deg, #3a82f6 0%, #8b5cf6 100%) !important;
        box-shadow: 0 0 30px rgba(139, 92, 246, 0.6) !important;
    }
    </style>
    """, unsafe_allow_html=True)


# --- Layout ---
st.markdown('<div class="title-text">Voice Assistant</div>', unsafe_allow_html=True)

if st.session_state.call_active:
    st.markdown('<div class="subtitle-text">I\'m listening...</div>', unsafe_allow_html=True)
    orb_html = """
    <div class="orb-container">
        <div class="orb active">
            <div class="soundwave">
                <div class="bar"></div><div class="bar"></div><div class="bar"></div>
                <div class="bar"></div><div class="bar"></div><div class="bar"></div>
                <div class="bar"></div><div class="bar"></div><div class="bar"></div>
            </div>
        </div>
    </div>
    """
else:
    st.markdown('<div class="subtitle-text" style="color: #666;">Ready to connect</div>', unsafe_allow_html=True)
    orb_html = """
    <div class="orb-container">
        <div class="orb">
            <div style="width: 80px; height: 3px; background: #333; border-radius: 2px;"></div>
        </div>
    </div>
    """

st.markdown(orb_html, unsafe_allow_html=True)


# --- Calling Logic ---
def start_vapi_thread():
    try:
        if not VAPI_API_KEY:
            print("API Key missing!")
            return
        vapi = Vapi(api_key=VAPI_API_KEY)
        st.session_state.vapi_instance = vapi
        
        vapi.start(
            assistant_id=ASSISTANT_ID,
            assistant_overrides={
                "variableValues": {
                    "name": "shivam",
                }
            }
        )
    except Exception as e:
        print(f"Call ended or errored: {e}")
    finally:
        st.session_state.call_active = False
        st.session_state.vapi_instance = None


if not st.session_state.call_active:
    if st.button("🎤", use_container_width=False, type="primary", key="start_btn"):
        st.session_state.call_active = True
        thread = threading.Thread(target=start_vapi_thread, daemon=True)
        thread.start()
        time.sleep(0.5)
        st.rerun()
else:
    if st.button("🛑", use_container_width=False, type="primary", key="stop_btn"):
        if st.session_state.vapi_instance is not None:
            try:
                st.session_state.vapi_instance.stop()
            except Exception:
                pass
        st.session_state.call_active = False
        st.session_state.vapi_instance = None
        st.rerun()

st.markdown("<br>", unsafe_allow_html=True)
col_a, col_b, col_c = st.columns([1, 1, 1])
with col_b:
    if st.session_state.call_active:
        st.toggle("Show Live Transcript", key="show_transcript")

# --- Real-Time Transcript Viewer ---
if st.session_state.call_active and st.session_state.vapi_instance:
    call_id = getattr(st.session_state.vapi_instance, "call_id", None)
    
    # Only render chat container if toggle is True
    if call_id and VAPI_API_KEY and st.session_state.get("show_transcript", False):
        st.markdown("<br><br>", unsafe_allow_html=True)
        chat_container = st.container(height=250)
        
        headers = {"Authorization": f"Bearer {VAPI_API_KEY}"}
        try:
            res = requests.get(f"https://api.vapi.ai/call/{call_id}", headers=headers)
            if res.status_code == 200:
                data = res.json()
                messages = data.get("messages", [])
                
                with chat_container:
                    for msg in messages:
                        role = msg.get("role")
                        text = msg.get("message")
                        if not text:
                            text = msg.get("text") or msg.get("transcript")
                            
                        # Hide backend logic payloads to keep the UI clean
                        if role == "system" or role == "tool_calls" or role == "function_call":
                            continue
                        elif text:
                            with st.chat_message(role):
                                st.write(text)
        except Exception:
            pass
            
    # Always sleep and rerun if call is active to keep state alive
    time.sleep(1.5)
    st.rerun()
