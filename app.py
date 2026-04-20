import streamlit as st
import firebase_admin
from firebase_admin import credentials, auth, firestore
import pyrebase
import json
import time
from datetime import datetime, timedelta
from AI_analysis import analyze_checkin, analyze_stability

firebaseConfig = {
    "apiKey": "AIzaSyCGgmnZB8ozlOz_4hVT_ONNeG1n1ITcQwU",
    "authDomain": "mentalmagic-10000.firebaseapp.com",
    "projectId": "mentalmagic-10000",
    "storageBucket": "mentalmagic-10000.appspot.com",
    "messagingSenderId": "146708371318",
    "appId": "1:146708371318:web:3fb7f3e8c3feacfc5bcc57",
    "databaseURL": ""
}

firebase = pyrebase.initialize_app(firebaseConfig)
pyrebase_auth = firebase.auth()

try:
    if not firebase_admin._apps:
        cred = credentials.Certificate('serviceAccountKey.json')
        firebase_admin.initialize_app(cred)
except Exception as e:
    st.error(f"Failed to initialize Firebase Admin SDK: {e}")
    st.stop()

db = firestore.client()

st.set_page_config(
    page_title="MentalMagic",
    layout="wide",
    initial_sidebar_state="expanded"
)


def save_mood_entry(user_uid, happiness_level, feeling_text):
    try:
        analysis = analyze_checkin(happiness_level, feeling_text)

        mood_entry = {
            'date': datetime.now().strftime("%Y-%m-%d"),
            'time': datetime.now().strftime("%H:%M:%S"),
            'datetime': datetime.now(),
            'happiness_level': happiness_level,
            'feeling_text': feeling_text,
            'summary': analysis.get("summary", ""),
            'recommendation': analysis.get("recommendation", ""),
            'created_at': firestore.SERVER_TIMESTAMP
        }

        doc_ref = db.collection('users').document(user_uid).collection('mood_entries').add(mood_entry)
        return True, doc_ref[1].id

    except Exception as e:
        st.error(f"Error saving mood entry: {e}")
        return False, None


def load_mood_entries(user_uid):
    try:
        entries_ref = (db.collection('users')
                       .document(user_uid)
                       .collection('mood_entries')
                       .order_by('created_at', direction=firestore.Query.DESCENDING))

        entries = entries_ref.get()

        data = []
        for entry in entries:
            entry_data = entry.to_dict()
            entry_data['id'] = entry.id

            if entry_data.get('initialized', False):
                continue

            if 'happiness_level' not in entry_data:
                continue

            if 'datetime' in entry_data and entry_data['datetime']:
                entry_data['datetime'] = entry_data['datetime'].strftime("%Y-%m-%d %H:%M:%S")
            data.append(entry_data)

        return data

    except Exception as e:
        st.error(f"Error loading mood entries: {e}")
        return []


def get_user_profile(user_uid):
    try:
        user_doc = db.collection('users').document(user_uid).get()
        if user_doc.exists:
            return user_doc.to_dict()
        return None
    except Exception as e:
        st.error(f"Error loading user profile: {e}")
        return None


def initialize_session_state():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'user_uid' not in st.session_state:
        st.session_state.user_uid = None
    if 'user_email' not in st.session_state:
        st.session_state.user_email = None
    if 'page' not in st.session_state:
        st.session_state.page = "Home"
    if 'error' not in st.session_state:
        st.session_state.error = None


def login_user(email, password):
    try:
        user = pyrebase_auth.sign_in_with_email_and_password(email, password)

        st.session_state.logged_in = True
        st.session_state.user = user
        st.session_state.user_uid = user['localId']
        st.session_state.user_email = user['email']
        st.session_state.error = None

        st.success("✅ Login successful!")
        st.rerun()

    except Exception as e:
        try:
            if len(e.args) > 1 and isinstance(e.args[1], str):
                error_json = e.args[1]
                error_message = json.loads(error_json)['error']['message']
                if "INVALID_PASSWORD" in error_message or "EMAIL_NOT_FOUND" in error_message:
                    st.session_state.error = "Invalid email or password. Please try again."
                elif "INVALID_EMAIL" in error_message:
                    st.session_state.error = "Please enter a valid email address."
                else:
                    st.session_state.error = f"Login failed: {error_message}"
            else:
                st.session_state.error = f"Login failed: {str(e)}"
        except (json.JSONDecodeError, KeyError, IndexError):
            st.session_state.error = f"An error occurred during login: {str(e)}"


def create_user_account(email, password, age):
    try:
        user = auth.create_user(email=email, password=password)

        user_doc = {
            'email': email,
            'age': age,
            'created_at': firestore.SERVER_TIMESTAMP,
            'profile': {
                'display_name': email.split('@')[0],
                'preferences': {
                    'notifications': True,
                    'privacy': 'private'
                }
            },
            'therapist_access': {
                'enabled': False,
                'status': 'not_requested'
            }
        }

        db.collection('users').document(user.uid).set(user_doc)

        db.collection('users').document(user.uid).collection('mood_entries').document('_init').set({
            'initialized': True,
            'created_at': firestore.SERVER_TIMESTAMP
        })

        st.success("🎉 Account created successfully! Please login to continue.")
        st.session_state.error = None

    except Exception as e:
        error_str = str(e)
        if "EMAIL_EXISTS" in error_str:
            st.session_state.error = "This email address is already in use."
        elif "WEAK_PASSWORD" in error_str:
            st.session_state.error = "Password should be at least 6 characters."
        elif "INVALID_EMAIL" in error_str:
            st.session_state.error = "Please enter a valid email address."
        else:
            st.session_state.error = f"Account creation failed: {error_str}"


def logout_user():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()


def show_login_page():
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.title("Welcome to :rainbow[Mental Magic!] ")
        st.markdown("*Your safe space for mental wellness tracking*")

        # Important disclaimers
        st.warning("""
         **IMPORTANT DISCLAIMER**

        This app is a **wellness tracking tool only** and is NOT:
        - A substitute for professional medical advice, diagnosis, or treatment
        - A therapy or counseling service
        - Intended to diagnose, treat, cure, or prevent any mental health condition

        **If you are experiencing a mental health crisis, please:**
        -  Call 988 (Suicide & Crisis Lifeline) in the US
        -  Contact your local emergency services (911)
        -  Visit your nearest emergency room
        -  Consult with a licensed mental health professional

        By using this app, you acknowledge that it is for personal wellness tracking only.
        """)
        st.divider()

        tab1, tab2 = st.tabs(["🔑 Login", "📝 Sign Up"])

        with tab1:
            with st.form("login_form", clear_on_submit=False):
                st.subheader("Login to Your Account")
                email = st.text_input("📧 Email Address", key="login_email")
                password = st.text_input("🔒 Password", type="password", key="login_password")

                login_button = st.form_submit_button("🚀 Login", type="primary", use_container_width=True)

                if login_button:
                    if not email or not password:
                        st.session_state.error = "Please enter both email and password."
                    else:
                        login_user(email, password)

        with tab2:
            with st.form("signup_form", clear_on_submit=True):
                st.subheader("Create New Account")
                email = st.text_input("📧 Email Address", key="signup_email")
                password = st.text_input("🔒 Password (min 6 characters)", type="password", key="signup_password")
                age = st.number_input("🎂 Age", min_value=13, max_value=120, value=25, key="signup_age")

                signup_button = st.form_submit_button("✨ Create Account", type="primary", use_container_width=True)

                if signup_button:
                    if not email or not password:
                        st.session_state.error = "Please enter both email and password."
                    else:
                        create_user_account(email, password, age)

        if st.session_state.error:
            st.error(st.session_state.error)
            st.session_state.error = None


def show_home_page():
    user_uid = st.session_state.user_uid

    st.title("🏠 MentalMagic Dashboard")
    st.markdown("*Welcome back! Ready to check in with yourself?*")

    # Health disclaimer banner
    with st.expander("⚠️ Health & Safety Disclaimer - Please Read", expanded=False):
        st.error("""
        **MENTAL HEALTH CRISIS RESOURCES:**
        - 🆘 **988 Suicide & Crisis Lifeline** (US): Call or text 988
        - 🌍 **International**: Find your local crisis line at findahelpline.com
        - 📞 **Emergency**: Call 911 or your local emergency number

        **IMPORTANT REMINDERS:**
        - This app does NOT provide medical advice or mental health treatment
        - AI-generated insights are NOT clinical assessments
        - Always consult licensed healthcare professionals for medical concerns
        - If you're in crisis or having thoughts of self-harm, seek immediate professional help
        - This tool is for personal wellness tracking and reflection only
        """)

    data = load_mood_entries(user_uid)
    if data:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Check-ins", len(data))
        with col2:
            mood_sum = sum(entry['happiness_level'] for entry in data)
            avg_mood = mood_sum / len(data) if data else 0
            st.metric("Average Mood", f"{avg_mood:.1f}/10")
        with col3:
            unique_dates = set(entry['date'] for entry in data)
            st.metric("Active Days", len(unique_dates))
        with col4:
            latest_mood = data[0]['happiness_level'] if data else 0
            st.metric("Last Mood", f"{latest_mood}/10")

    st.divider()

    st.subheader("💬 How are you feeling right now?")

    col1, col2 = st.columns([1, 2])

    with col1:
        happiness = st.slider(
            "Happiness Level",
            min_value=1,
            max_value=10,
            value=5,
            help="1 = Very unhappy, 10 = Very happy"
        )

        if happiness >= 8:
            mood_emoji = "😄"
        elif happiness >= 6:
            mood_emoji = "😊"
        elif happiness >= 4:
            mood_emoji = "😐"
        elif happiness >= 2:
            mood_emoji = "😔"
        else:
            mood_emoji = "😢"

        st.markdown(f"### {mood_emoji} {happiness}/10")

    with col2:
        feeling_text = st.text_area(
            "What's on your mind?",
            placeholder="Tell me about your day, your thoughts, or how you're feeling...",
            height=120
        )

    if st.button("💾 Save Check-in", type="primary", use_container_width=True):
        if feeling_text.strip():
            success, entry_id = save_mood_entry(user_uid, happiness, feeling_text)
            if success:
                st.success("Check-in saved successfully!")
                st.balloons()
                st.rerun()
        else:
            st.warning("Please share what's on your mind before saving!!!!")

    if data:
        st.divider()
        st.subheader("Recent Check-ins")

        recent_entries = data[:3]
        for entry in recent_entries:
            with st.expander(f"📅 {entry['date']} at {entry['time']} - Mood: {entry['happiness_level']}/10"):
                st.markdown(f"**💭 You said:** {entry['feeling_text']}")
                if entry.get('summary'):
                    st.markdown(f"**AI Summary:** {entry['summary']}")
                if entry.get('recommendation'):
                    st.markdown(f"**Suggestion:** {entry['recommendation']}")

        if len(data) > 3:
            st.info(f"📊 View all {len(data)} check-ins in the Mood Tracking section")


def show_mood_tracking_page():
    user_uid = st.session_state.user_uid

    st.title("📊 Mood Tracking History")

    data = load_mood_entries(user_uid)
    if not data:
        st.info("📝 No mood entries yet. Add your first check-in from the Home page!")
        return

    col1, col2, col3 = st.columns(3)
    with col1:
        date_range = st.selectbox("Time Range",
                                  ["All Time", "Last 7 Days", "Last 30 Days", "Last 90 Days"])
    with col2:
        mood_filter = st.selectbox(" Mood Filter",
                                   ["All Moods", "High (7-10)", "Medium (4-6)", "Low (1-3)"])
    with col3:
        sort_order = st.selectbox("📈 Sort Order", ["Newest First", "Oldest First"])

    filtered_data = data.copy()

    if date_range != "All Time":
        days_map = {"Last 7 Days": 7, "Last 30 Days": 30, "Last 90 Days": 90}
        days = days_map[date_range]
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        filtered_data = [entry for entry in filtered_data if entry['date'] >= cutoff_date]

    if mood_filter != "All Moods":
        if mood_filter == "High (7-10)":
            filtered_data = [entry for entry in filtered_data if entry['happiness_level'] >= 7]
        elif mood_filter == "Medium (4-6)":
            filtered_data = [entry for entry in filtered_data if 4 <= entry['happiness_level'] <= 6]
        elif mood_filter == "Low (1-3)":
            filtered_data = [entry for entry in filtered_data if entry['happiness_level'] <= 3]

    if sort_order == "Oldest First":
        filtered_data = sorted(filtered_data, key=lambda x: x['datetime'])

    st.write(f"Showing **{len(filtered_data)}** entries")

    for entry in filtered_data:
        if entry['happiness_level'] >= 7:
            mood_color = "🟢"
        elif entry['happiness_level'] >= 4:
            mood_color = "🟡"
        else:
            mood_color = "🔴"

        with st.expander(f"{mood_color} {entry['date']} at {entry['time']} - Happiness: {entry['happiness_level']}/10"):
            col1, col2 = st.columns([3, 1])

            with col1:
                st.markdown(f"**💭 Your feelings:** {entry['feeling_text']}")
                if entry.get('summary'):
                    st.markdown(f"**🤖 AI Analysis:** {entry['summary']}")
                if entry.get('recommendation'):
                    st.markdown(f"**💡 Recommendation:** {entry['recommendation']}")

            with col2:
                st.metric("Mood Level", f"{entry['happiness_level']}/10")


def save_breathing_session(user_uid, duration_minutes, start_time):
    """Save breathing session to Firestore"""
    try:
        breathing_entry = {
            'date': start_time.strftime("%Y-%m-%d"),
            'time': start_time.strftime("%H:%M:%S"),
            'datetime': start_time,
            'duration_minutes': int(duration_minutes),
            'activity_type': 'breathing',
            'created_at': firestore.SERVER_TIMESTAMP
        }

        doc_ref = db.collection('users').document(user_uid).collection('activities').add(breathing_entry)
        doc_id = doc_ref[1].id
        st.success(f"✅ Breathing session saved! ({duration_minutes} minutes)")
        return True
    except Exception as e:
        st.error(f"❌ Error saving breathing session: {str(e)}")
        return False


def show_breathing_page(minutes: int):
    """Deep breathing exercise page with visual guidance"""

    # Initialize breathing state tracking
    if "breathing_completed" not in st.session_state:
        st.session_state["breathing_completed"] = False

    if "breathing_elapsed" not in st.session_state:
        st.session_state["breathing_elapsed"] = 0

    # Full-screen breathing styling
    st.markdown(
        """
        <style>
        /* Hide EVERYTHING */
        #MainMenu {display: none !important;}
        footer {display: none !important;}
        header {display: none !important;}
        .stDeployButton {display: none !important;}
        [data-testid="stSidebar"] {display: none !important;}
        [data-testid="stHeader"] {display: none !important;}
        [data-testid="stExpander"] {display: none !important;}
        .stSelectbox {display: none !important;}
        .stNumberInput {display: none !important;}

        /* Full screen background */
        .stApp {
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%) !important;
        }

        .main .block-container {
            padding: 0 !important;
            max-width: 100% !important;
        }

        /* Timer styling */
        .breathing-timer {
            font-size: 80px;
            text-align: center;
            color: white;
            font-weight: 300;
            text-shadow: 0 4px 20px rgba(0,0,0,0.2);
            font-family: 'Helvetica Neue', sans-serif;
            margin: 20px 0;
        }

        /* Title styling */
        .breathing-title {
            font-size: 32px;
            text-align: center;
            color: rgba(255, 255, 255, 0.95);
            font-weight: 300;
            margin-bottom: 20px;
            letter-spacing: 2px;
        }

        /* Breathing instruction */
        .breathing-instruction {
            font-size: 40px;
            text-align: center;
            color: white;
            margin-top: 30px;
            font-weight: 400;
            text-shadow: 0 2px 10px rgba(0,0,0,0.2);
        }

        /* Breathing circle */
        .breathing-circle {
            width: 200px;
            height: 200px;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.3);
            margin: 40px auto;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
        }

        /* Button styling */
        .stButton button {
            background-color: rgba(255, 255, 255, 0.25) !important;
            color: white !important;
            border: 2px solid rgba(255, 255, 255, 0.6) !important;
            border-radius: 30px !important;
            padding: 12px 30px !important;
            font-size: 18px !important;
            font-weight: 400 !important;
            transition: all 0.3s ease !important;
        }

        .stButton button:hover {
            background-color: rgba(255, 255, 255, 0.35) !important;
            border-color: rgba(255, 255, 255, 0.9) !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # Title
    st.markdown("<div class='breathing-title'>🌬️ Deep Breathing Exercise 🌬️</div>", unsafe_allow_html=True)

    # Check if breathing is completed
    if st.session_state["breathing_completed"]:
        st.markdown("<div class='breathing-timer'>✨</div>", unsafe_allow_html=True)
        st.markdown("<div class='breathing-instruction'>Session Complete! You did great!</div>", unsafe_allow_html=True)

        # Save breathing data once
        if st.session_state.get("breathing_start") and not st.session_state.get("breathing_saved", False):
            success = save_breathing_session(
                st.session_state.user_uid,
                minutes,
                st.session_state["breathing_start"]
            )
            if success:
                st.session_state["breathing_saved"] = True
                st.balloons()

        # Finish button
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("✅ Finish & Return", key="finish_breathing", type="primary", use_container_width=True):
                st.session_state["doing_breathing"] = False
                st.session_state["breathing_completed"] = False
                st.session_state["breathing_elapsed"] = 0
                for key in ["breathing_time", "breathing_start", "breathing_saved"]:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()
        return

    # Exit button
    col1, col2, col3 = st.columns([2, 1, 2])
    with col2:
        if st.button("❌ Exit Early", key="exit_breathing", use_container_width=True):
            st.session_state["doing_breathing"] = False
            st.session_state["breathing_completed"] = False
            st.session_state["breathing_elapsed"] = 0
            for key in ["breathing_time", "breathing_start", "breathing_saved"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

    # Timer and instruction placeholders
    timer_placeholder = st.empty()
    instruction_placeholder = st.empty()
    circle_placeholder = st.empty()

    # Run the breathing exercise
    total_seconds = minutes * 60
    elapsed = st.session_state["breathing_elapsed"]

    # Breathing pattern: 4 seconds in, 4 seconds hold, 4 seconds out, 4 seconds hold (16 second cycle)
    for remaining in range(total_seconds - elapsed, -1, -1):
        mins, secs = divmod(remaining, 60)
        timer_display = f"{mins:02d}:{secs:02d}"

        # Update timer
        timer_placeholder.markdown(
            f"<div class='breathing-timer'>{timer_display}</div>",
            unsafe_allow_html=True
        )

        # Breathing cycle (16 seconds total)
        cycle_position = (total_seconds - remaining) % 16

        if cycle_position < 4:
            instruction = "Breathe In... 🌬️"
            circle_size = 200 + (cycle_position * 25)  # Grow from 200 to 300
        elif cycle_position < 8:
            instruction = "Hold... ⏸️"
            circle_size = 300  # Stay large
        elif cycle_position < 12:
            instruction = "Breathe Out... 💨"
            circle_size = 300 - ((cycle_position - 8) * 25)  # Shrink from 300 to 200
        else:
            instruction = "Hold... ⏸️"
            circle_size = 200  # Stay small

        instruction_placeholder.markdown(
            f"<div class='breathing-instruction'>{instruction}</div>",
            unsafe_allow_html=True
        )

        circle_placeholder.markdown(
            f"""
            <div style='text-align: center;'>
                <div style='width: {circle_size}px; height: {circle_size}px; border-radius: 50%; 
                     background: rgba(255, 255, 255, 0.3); margin: 40px auto; 
                     transition: all 1s ease; box-shadow: 0 8px 32px rgba(0,0,0,0.1);'></div>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.session_state["breathing_elapsed"] += 1
        time.sleep(1)

    # Mark breathing as completed
    st.session_state["breathing_completed"] = True
    st.rerun()


def save_meditation_session(user_uid, duration_minutes, start_time):
    """Save meditation session to Firestore"""
    try:
        meditation_entry = {
            'date': start_time.strftime("%Y-%m-%d"),
            'time': start_time.strftime("%H:%M:%S"),
            'datetime': start_time,
            'duration_minutes': int(duration_minutes),
            'activity_type': 'meditation',
            'created_at': firestore.SERVER_TIMESTAMP
        }

        doc_ref = db.collection('users').document(user_uid).collection('activities').add(meditation_entry)
        doc_id = doc_ref[1].id
        st.success(f"✅ Meditation session saved! ({duration_minutes} minutes)")
        return True
    except Exception as e:
        st.error(f"❌ Error saving meditation session: {str(e)}")
        return False


def show_meditation_page(minutes: int):
    """Minimalist meditation timer page - clean and distraction-free"""

    # Initialize meditation state tracking
    if "meditation_completed" not in st.session_state:
        st.session_state["meditation_completed"] = False

    if "meditation_elapsed" not in st.session_state:
        st.session_state["meditation_elapsed"] = 0

    # Full-screen meditation styling - AGGRESSIVE HIDING
    st.markdown(
        """
        <style>
        /* Hide EVERYTHING */
        #MainMenu {display: none !important;}
        footer {display: none !important;}
        header {display: none !important;}
        .stDeployButton {display: none !important;}
        [data-testid="stSidebar"] {display: none !important;}
        [data-testid="stHeader"] {display: none !important;}

        /* Hide all expanders, dropdowns, and form elements */
        [data-testid="stExpander"] {display: none !important;}
        .stSelectbox {display: none !important;}
        .stNumberInput {display: none !important;}
        .stTextInput {display: none !important;}
        .stTextArea {display: none !important;}
        div[data-baseweb="select"] {display: none !important;}
        div[data-baseweb="popover"] {display: none !important;}

        /* Hide all page content except meditation */
        .main > div:not(:has(.meditation-timer)):not(:has(.stButton)) {
            display: none !important;
        }

        /* Full screen background */
        .stApp {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        }

        /* Hide original page title and content */
        h1:not(.meditation-title), .stMarkdown h1:not(.meditation-title) {
            display: none !important;
        }

        /* Hide info/warning messages */
        .stAlert {
            display: none !important;
        }

        .main .block-container {
            padding: 0 !important;
            max-width: 100% !important;
        }

        /* Timer styling */
        .meditation-timer {
            font-size: 120px;
            text-align: center;
            color: white;
            font-weight: 300;
            text-shadow: 0 4px 20px rgba(0,0,0,0.3);
            font-family: 'Helvetica Neue', sans-serif;
            margin: 20px 0;
        }

        /* Title styling */
        .meditation-title {
            font-size: 32px;
            text-align: center;
            color: rgba(255, 255, 255, 0.9);
            font-weight: 300;
            margin-bottom: 20px;
            letter-spacing: 2px;
        }

        /* Breathing guide */
        .meditation-text {
            font-size: 24px;
            text-align: center;
            color: rgba(255, 255, 255, 0.7);
            margin-top: 20px;
            font-weight: 300;
        }

        /* Button styling */
        .stButton button {
            background-color: rgba(255, 255, 255, 0.2) !important;
            color: white !important;
            border: 2px solid rgba(255, 255, 255, 0.5) !important;
            border-radius: 30px !important;
            padding: 12px 30px !important;
            font-size: 18px !important;
            font-weight: 400 !important;
            transition: all 0.3s ease !important;
        }

        .stButton button:hover {
            background-color: rgba(255, 255, 255, 0.3) !important;
            border-color: rgba(255, 255, 255, 0.8) !important;
        }

        /* Show only buttons and meditation elements */
        .element-container:has(.stButton) {
            display: block !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # Title
    st.markdown("<div class='meditation-title'>✨ Meditation in Progress ✨</div>", unsafe_allow_html=True)

    # Check if meditation is completed
    if st.session_state["meditation_completed"]:
        # Show completion screen
        st.markdown("<div class='meditation-timer'>✨</div>", unsafe_allow_html=True)
        st.markdown("<div class='meditation-text'>Meditation Complete!</div>", unsafe_allow_html=True)

        # Save meditation data once
        if st.session_state.get("meditation_start") and not st.session_state.get("meditation_saved", False):
            success = save_meditation_session(
                st.session_state.user_uid,
                minutes,
                st.session_state["meditation_start"]
            )
            if success:
                st.session_state["meditation_saved"] = True
                st.balloons()

        # Finish button
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("✅ Finish & Return", key="finish_meditation", type="primary", use_container_width=True):
                # Clean up all meditation session state
                st.session_state["meditating"] = False
                st.session_state["meditation_completed"] = False
                st.session_state["meditation_elapsed"] = 0
                for key in ["meditation_time", "meditation_start", "meditation_saved"]:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()
        return

    # Exit button (only show during meditation)
    col1, col2, col3 = st.columns([2, 1, 2])
    with col2:
        if st.button("❌ Exit Early", key="exit_meditation", use_container_width=True):
            # Clean up all meditation session state
            st.session_state["meditating"] = False
            st.session_state["meditation_completed"] = False
            st.session_state["meditation_elapsed"] = 0
            for key in ["meditation_time", "meditation_start", "meditation_saved"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

    # Timer placeholders
    timer_placeholder = st.empty()
    breathing_placeholder = st.empty()

    # Run the countdown
    total_seconds = minutes * 60
    elapsed = st.session_state["meditation_elapsed"]

    for remaining in range(total_seconds - elapsed, -1, -1):
        mins, secs = divmod(remaining, 60)
        timer_display = f"{mins:02d}:{secs:02d}"

        # Update timer
        timer_placeholder.markdown(
            f"<div class='meditation-timer'>{timer_display}</div>",
            unsafe_allow_html=True
        )

        # Breathing guide (changes every 4 seconds)
        cycle = (total_seconds - remaining) % 8
        if cycle < 4:
            ambiencemeditiationtext = "Let your mind relax"
        else:
            ambiencemeditiationtext = "Focus on thinking 1 thing and close your eyes"

        breathing_placeholder.markdown(
            f"<div class='meditation-text'>{ambiencemeditiationtext}</div>",
            unsafe_allow_html=True
        )

        st.session_state["meditation_elapsed"] += 1
        time.sleep(1)

    # Mark meditation as completed
    st.session_state["meditation_completed"] = True
    st.rerun()


def show_activities_page():
    """Display wellness activities and self-care techniques"""

    # Check if currently meditating
    if st.session_state.get("meditating", False):
        show_meditation_page(st.session_state["meditation_time"])
        return

    # Check if currently doing breathing exercise
    if st.session_state.get("doing_breathing", False):
        show_breathing_page(st.session_state["breathing_time"])
        return

    st.title("🌟 Wellness Activities")
    st.markdown("*Choose an activity to help you relax, recharge, and take care of yourself*")

    # Medical disclaimer for activities
    st.warning("""
    ⚠️ **Medical Disclaimer for Wellness Activities:**
    - These breathing and meditation exercises are for general wellness only
    - Consult your healthcare provider before starting any new wellness routine
    - Stop immediately if you experience dizziness, discomfort, or breathing difficulties
    - Not suitable for individuals with certain medical conditions (e.g., severe respiratory issues)
    - Seek emergency help if you experience chest pain, severe shortness of breath, or other concerning symptoms
    """)

    # Display activity statistics
    user_uid = st.session_state.user_uid
    meditation_sessions = []
    breathing_sessions = []

    try:
        # Query all activities
        activities_ref = (db.collection('users')
                          .document(user_uid)
                          .collection('activities'))

        activities = activities_ref.get()

        # Filter for meditation and breathing activities
        for act in activities:
            act_data = act.to_dict()
            if act_data.get('activity_type') == 'meditation':
                meditation_sessions.append(act_data)
            elif act_data.get('activity_type') == 'breathing':
                breathing_sessions.append(act_data)

        # Sort by date (most recent first)
        meditation_sessions.sort(key=lambda x: x.get('datetime', datetime.min), reverse=True)
        breathing_sessions.sort(key=lambda x: x.get('datetime', datetime.min), reverse=True)

    except Exception as e:
        st.error(f"Error loading activity history: {e}")

    # Display stats if we have any sessions
    if meditation_sessions or breathing_sessions:
        st.subheader("📊 Your Wellness Stats")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            total_sessions = len(meditation_sessions) + len(breathing_sessions)
            st.metric("Total Sessions", total_sessions)

        with col2:
            meditation_minutes = sum(session.get('duration_minutes', 0) for session in meditation_sessions)
            breathing_minutes = sum(session.get('duration_minutes', 0) for session in breathing_sessions)
            total_minutes = meditation_minutes + breathing_minutes
            st.metric("Total Minutes", total_minutes)

        with col3:
            st.metric("Meditation Sessions", len(meditation_sessions))

        with col4:
            st.metric("Breathing Sessions", len(breathing_sessions))

        st.divider()

        # Show recent sessions
        if meditation_sessions:
            st.subheader("🕉️ Recent Meditation Sessions")
            for session in meditation_sessions[:3]:
                with st.expander(
                        f"📅 {session.get('date')} at {session.get('time')} - {session.get('duration_minutes')} minutes"):
                    st.markdown(f"**Duration:** {session.get('duration_minutes')} minutes")
                    st.markdown(f"**Date:** {session.get('date')}")
                    st.markdown(f"**Time:** {session.get('time')}")

        if breathing_sessions:
            st.subheader("🌬️ Recent Breathing Sessions")
            for session in breathing_sessions[:3]:
                with st.expander(
                        f"📅 {session.get('date')} at {session.get('time')} - {session.get('duration_minutes')} minutes"):
                    st.markdown(f"**Duration:** {session.get('duration_minutes')} minutes")
                    st.markdown(f"**Date:** {session.get('date')}")
                    st.markdown(f"**Time:** {session.get('time')}")

        st.divider()
    else:
        st.info("No activity history yet. Start your first session below!")

    # Meditation section
    with st.expander("🧘 Meditation & Mindfulness", expanded=False):
        st.markdown("Meditation has been proven to be beneficial for the mind and body. "
                    "If you feel overwhelmed, how about trying some meditation?")

        med = st.number_input("Enter minutes for Meditation:", min_value=1, max_value=120, value=5,
                              key="meditation_minutes_input")
        if st.button(f"Begin Meditating for {med} minutes", key="start_meditation_btn"):
            st.session_state["meditating"] = True
            st.session_state["meditation_time"] = med
            st.session_state["meditation_start"] = datetime.now()
            st.rerun()

    # Breathing exercise section
    with st.expander("🌬️ Deep Breathing Exercise", expanded=False):
        st.markdown("Deep breathing exercises help reduce stress, lower blood pressure, and promote relaxation. "
                    "Follow the guided breathing pattern to calm your mind and body.")
        st.markdown("**Pattern:** 4 seconds in → 4 seconds hold → 4 seconds out → 4 seconds hold")

        breath = st.number_input("Enter minutes for Breathing:", min_value=1, max_value=30, value=3,
                                 key="breathing_minutes_input")
        if st.button(f"Start Breathing Exercise for {breath} minutes", key="start_breathing_btn"):
            st.session_state["doing_breathing"] = True
            st.session_state["breathing_time"] = breath
            st.session_state["breathing_start"] = datetime.now()
            st.rerun()


def show_analytics_page():
    user_uid = st.session_state.user_uid

    st.title("📈 Mood Analytics & Insights")

    # Analytics disclaimer
    st.info("""
    ℹ️ **About This Analysis:**
    These insights are based on statistical patterns in your mood entries and AI analysis. 
    They are NOT clinical diagnoses or professional medical assessments. 
    Always consult a licensed mental health professional for clinical evaluation and treatment.
    """)

    data = load_mood_entries(user_uid)
    if not data:
        st.info("📊 No data available for analysis. Start tracking your mood to see insights!")
        return

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        mood_sum = sum(entry['happiness_level'] for entry in data)
        avg_mood = mood_sum / len(data)
        st.metric("Average Mood", f"{avg_mood:.1f}/10")

    with col2:
        highest_mood = max(entry['happiness_level'] for entry in data)
        st.metric("Highest Recorded", f"{highest_mood}/10")

    with col3:
        lowest_mood = min(entry['happiness_level'] for entry in data)
        st.metric("Lowest Recorded", f"{lowest_mood}/10")

    with col4:
        mood_levels = [entry['happiness_level'] for entry in data]
        variance = sum((x - avg_mood) ** 2 for x in mood_levels) / len(mood_levels)
        stability_score = max(0, 10 - variance)
        st.metric("Mood Stability", f"{stability_score:.1f}/10")

    if len(data) >= 5:
        recent_avg = sum(data[i]['happiness_level'] for i in range(5)) / 5
        older_data = data[-5:]
        older_avg = sum(entry['happiness_level'] for entry in older_data) / 5
        trend = "📈 Improving" if recent_avg > older_avg else "📉 Declining" if recent_avg < older_avg else "➡️ Stable"

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Recent Trend (Last 5 entries)", trend)
        with col2:
            trend_diff = recent_avg - older_avg
            st.metric("Trend Change", f"{trend_diff:+.1f} points")

    st.divider()
    st.subheader("🤖 AI Stability Analysis")

    with st.spinner("Analyzing your mood patterns..."):
        try:
            stability_analysis = analyze_stability(data)
            st.success("✅ Analysis complete!")
            st.markdown(f"**AI Insights:**\n\n{stability_analysis}")
        except Exception as e:
            st.error(f"Error generating analysis: {e}")


def show_settings_page():
    user_uid = st.session_state.user_uid
    user_email = st.session_state.user_email

    st.title("⚙️ Settings")

    user_profile = get_user_profile(user_uid)
    if not user_profile:
        st.error("Could not load user profile.")
        return

    st.subheader("👤 Profile Settings")
    current_name = user_profile.get('profile', {}).get('display_name', user_email.split('@')[0])

    with st.form("profile_form"):
        col1, col2 = st.columns(2)
        with col1:
            display_name = st.text_input("Display Name", value=current_name)
        with col2:
            age = st.number_input("Age", value=user_profile.get('age', 25), min_value=13, max_value=120)

        if st.form_submit_button("💾 Save Profile", type="primary"):
            try:
                db.collection('users').document(user_uid).update({
                    'profile.display_name': display_name,
                    'age': age,
                    'updated_at': firestore.SERVER_TIMESTAMP
                })
                st.success("✅ Profile updated successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Error updating profile: {e}")

    st.divider()

    st.subheader("📊 Data Management")

    st.info("""
    **Privacy & Data Information:**
    - Your data is stored securely in Firebase
    - We do not share your personal information with third parties
    - You can export or request deletion of your data at any time
    - This app is for personal use only
    """)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("📥 Export My Data", use_container_width=True):
            data = load_mood_entries(user_uid)
            if data:
                csv_content = "date,time,happiness_level,feeling_text,summary,recommendation\n"
                for entry in data:
                    csv_content += f"{entry['date']},{entry['time']},{entry['happiness_level']},\"{entry['feeling_text']}\",\"{entry.get('summary', '')}\",\"{entry.get('recommendation', '')}\"\n"

                st.download_button(
                    label="⬇️ Download CSV",
                    data=csv_content,
                    file_name=f"mentalmagic_data_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            else:
                st.info("No data to export yet!")

    with col2:
        if st.button("🗑️ Delete All Data", use_container_width=True, type="secondary"):
            st.warning("⚠️ This action cannot be undone! Contact support if you need this feature.")


def show_main_app():
    user_uid = st.session_state.user_uid
    user_email = st.session_state.user_email

    user_profile = get_user_profile(user_uid)
    display_name = user_profile.get('profile', {}).get('display_name', user_email.split('@')[0]) if user_profile else \
    user_email.split('@')[0]

    with st.sidebar:
        st.title("🧠 MentalMagic")
        st.markdown(f"Welcome back, **{display_name}**! ✨")

        st.markdown("---")
        pages = {
            "🏠 Home": "Home",
            "📊 Mood Tracking": "Mood Tracking",
            "🌟 Activities": "Activities",
            "📈 Analytics": "Analytics",
            "⚙️ Settings": "Settings"
        }

        st.markdown("""
        **⚠️ Important Reminders:**
        - This app tracks wellness, it does NOT cure or treat mental health conditions
        - Always consult licensed professionals for medical advice
        - In crisis? Call 988 (US) or your local emergency services
        """)

        st.markdown("---")

        for button_text, page_name in pages.items():
            if st.button(button_text, key=f"nav_{page_name}", use_container_width=True):
                st.session_state.page = page_name
                st.rerun()

        st.markdown("---")

        if st.button("🚪 Logout", type="secondary", use_container_width=True):
            logout_user()

        st.markdown("---")
        st.caption(
            "⚠️ **Medical Disclaimer:** This app provides wellness tracking only, not medical advice, diagnosis, or treatment. Always seek professional help for mental health concerns.")
        st.caption("🔒 **Privacy:** Your data is stored securely. We do not share your information.")
        st.caption(
            "📧 **Questions?** This is a personal wellness tool. For clinical support, contact a licensed healthcare provider.")

    current_page = st.session_state.page

    if current_page == "Home":
        show_home_page()
    elif current_page == "Mood Tracking":
        show_mood_tracking_page()
    elif current_page == "Analytics":
        show_analytics_page()
    elif current_page == "Settings":
        show_settings_page()
    elif current_page == "Activities":
        show_activities_page()


def main():
    st.markdown("""
    <meta name="google-site-verification" content="u1JrKrjlembDn6YYN9ZENcIklcU16MuwvOPXowPoRmo" />
    <style>
    .chat-message {
        margin: 10px 0;
        padding: 10px;
        border-radius: 15px;
        max-width: 70%;
        word-wrap: break-word;
    }

    .client-message {
        background-color: #007acc;
        color: white;
        margin-left: auto;
        text-align: right;
    }

    .therapist-message {
        background-color: #f0f2f6;
        color: black;
        margin-right: auto;
        text-align: left;
    }

    .stTextArea textarea {
        font-size: 16px;
    }
    </style>
    """, unsafe_allow_html=True)

    initialize_session_state()

    if st.session_state.logged_in:
        show_main_app()
    else:
        show_login_page()


if __name__ == "__main__":

    main()
