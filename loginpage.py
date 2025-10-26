import streamlit as st
import firebase_admin
from firebase_admin import credentials, auth, firestore
import pyrebase
import json

# --- Firebase Configuration ---
firebaseConfig = {
    "apiKey": "AIzaSyCGgmnZB8ozlOz_4hVT_ONNeG1n1ITcQwU",
    "authDomain": "mentalmagic-10000.firebaseapp.com",
    "projectId": "mentalmagic-10000",
    "storageBucket": "mentalmagic-10000.appspot.com",
    "messagingSenderId": "146708371318",
    "appId": "1:146708371318:web:3fb7f3e8c3feacfc5bcc57",
    "databaseURL": ""
}

# Initialize Firebase
firebase = pyrebase.initialize_app(firebaseConfig)
pyrebase_auth = firebase.auth()

# Initialize Firebase Admin SDK
try:
    if not firebase_admin._apps:
        cred = credentials.Certificate('serviceAccountKey.json')
        firebase_admin.initialize_app(cred)
except Exception as e:
    st.error(f"Failed to initialize Firebase Admin SDK: {e}")
    st.stop()

db = firestore.client()

# Configure Streamlit (only main app can use set_page_config)
st.set_page_config(
    page_title="Mental Magic - Login",
    layout="centered",
    initial_sidebar_state="collapsed"
)


def login_page():
    """Handles login and sign-up"""
    st.title("Welcome to :rainbow[Mental Magic!] 🧠")
    st.text("Your safe space.")

    # Initialize session state
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'error' not in st.session_state:
        st.session_state.error = None

    # Check if already logged in - show redirect message
    if st.session_state.get('logged_in', False):
        st.success("✅ Login successful!")
        st.info("📱 Now open your main app: **app.py**")
        st.markdown("Run this command in your terminal:")
        st.code("streamlit run app.py")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🚪 Logout"):
                st.session_state.clear()
                st.rerun()
        with col2:
            st.markdown("*Or just open app.py directly*")
        return

    choice = st.selectbox("Login/Sign-Up", ["Login", "Sign Up"], key="login_signup_choice")

    # Login Logic
    if choice == "Login":
        email = st.text_input("Enter your Email Address", key="login_email")
        password = st.text_input("Enter your password", type="password", key="login_password")

        if st.button("Login", key="login_button"):
            if not email or not password:
                st.session_state.error = "Please enter both email and password."
            else:
                try:
                    # Authenticate with Pyrebase
                    user = pyrebase_auth.sign_in_with_email_and_password(email, password)

                    # Store user data in session state
                    st.session_state.logged_in = True
                    st.session_state.user = user
                    st.session_state.user_uid = user['localId']
                    st.session_state.user_email = user['email']
                    st.session_state.error = None

                    st.success("✅ Login successful!")
                    st.rerun()

                except Exception as e:
                    try:
                        # Try to parse Pyrebase error format
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
                            # Handle other error formats
                            st.session_state.error = f"Login failed: {str(e)}"
                    except (json.JSONDecodeError, KeyError, IndexError):
                        # Fallback for any parsing errors
                        st.session_state.error = f"An error occurred during login: {str(e)}"

    # Sign-Up Logic
    else:
        email = st.text_input("Enter your Email Address", key="signup_email")
        password = st.text_input("Enter your password", type="password", key="signup_password")
        age = st.number_input("Enter your age", min_value=1, max_value=120, key="signup_age")

        if st.button("Create my account", key="signup_button"):
            if not email or not password:
                st.session_state.error = "Please enter both email and password."
            else:
                try:
                    # Create user with Firebase Admin SDK
                    user = auth.create_user(email=email, password=password)

                    # Create user document with mood_entries subcollection structure
                    user_doc = {
                        'email': email,
                        'age': age,
                        'created_at': firestore.SERVER_TIMESTAMP,
                        'profile': {
                            'display_name': email.split('@')[0],  # Default display name
                            'preferences': {
                                'notifications': True,
                                'privacy': 'private'
                            }
                        }
                    }

                    # Set user document
                    db.collection('users').document(user.uid).set(user_doc)

                    # Initialize empty mood_entries subcollection with a placeholder doc
                    db.collection('users').document(user.uid).collection('mood_entries').document('_init').set({
                        'initialized': True,
                        'created_at': firestore.SERVER_TIMESTAMP
                    })

                    st.success("🎉 Account created successfully! Please login to continue.")
                    st.session_state.error = None

                except Exception as e:
                    try:
                        # Handle Firebase Admin SDK errors
                        error_str = str(e)
                        if "EMAIL_EXISTS" in error_str:
                            st.session_state.error = "This email address is already in use."
                        elif "WEAK_PASSWORD" in error_str:
                            st.session_state.error = "Password should be at least 6 characters."
                        elif "INVALID_EMAIL" in error_str:
                            st.session_state.error = "Please enter a valid email address."
                        else:
                            st.session_state.error = f"Account creation failed: {error_str}"
                    except Exception:
                        st.session_state.error = f"An error occurred during account creation: {str(e)}"

    # Display errors
    if st.session_state.error:
        st.error(st.session_state.error)
        st.session_state.error = None


if __name__ == "__main__":
    login_page()