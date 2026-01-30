import streamlit as st
import mysql.connector
from pyngrok import ngrok
from datetime import datetime, timedelta
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration
import atexit

# Import custom modules
from config import NGROK_AUTH_TOKEN, NGROK_ADDR, TIMEZONE
from database import get_db_connection, create_tables
from audio_system import AudioSystem
from reminder_system import ReminderSystem
from video_processor import VideoProcessor

# ------------------ NGROK (FIXED) ------------------
def start_ngrok():
    try:
        ngrok.set_auth_token(NGROK_AUTH_TOKEN)
        ngrok.kill()
        tunnel = ngrok.connect(addr=NGROK_ADDR, bind_tls=True)
        return tunnel.public_url
    except Exception as e:
        return f"NGROK ERROR: {e}"

if "public_url" not in st.session_state:
    st.session_state.public_url = start_ngrok()

st.sidebar.success("🌐 Public Link")
st.sidebar.write(st.session_state.public_url)

# ------------------ DATABASE CONNECTION ------------------
db_conn, db_available = get_db_connection()

# ------------------ SESSION STATE ------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.current_user = ""
    st.session_state.video_processor = None
    st.session_state.audio_system = None
    st.session_state.reminder_system = None
    st.session_state.motion_alerts = []
    st.session_state.announcements = []
    st.session_state.reminders = []
    st.session_state.triggered_reminders = []
    st.session_state.start_time = None

# Initialize systems
if st.session_state.get("audio_system") is None:
    st.session_state.audio_system = AudioSystem()

if st.session_state.get("reminder_system") is None:
    st.session_state.reminder_system = ReminderSystem()
    st.session_state.reminder_system.start_background_check()

# ------------------ TITLE ------------------
st.markdown(
    "<h1 style='text-align:center; color:#4B0082;'>🏠 SmartHome CCTV + Reminders</h1>",
    unsafe_allow_html=True
)
st.markdown("---")

# ------------------ LOGIN / REGISTER PAGE ------------------
if not st.session_state.logged_in:
    st.subheader("🔐 System Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    col1, col2 = st.columns(2)

    # Login
    with col1:
        if st.button("🔓 Login", use_container_width=True, type="primary"):
            if username and password:
                if db_available:
                    try:
                        cursor = db_conn.cursor()
                        cursor.execute(
                            "SELECT * FROM users WHERE username=%s AND password_hash=%s",
                            (username, password)
                        )
                        user = cursor.fetchone()
                        
                        if user:
                            st.session_state.logged_in = True
                            st.session_state.current_user = username
                            st.session_state.video_processor = VideoProcessor()
                            st.session_state.motion_alerts = []
                            st.session_state.announcements = []
                            st.session_state.reminders = []
                            st.session_state.start_time = datetime.now()
                            
                            # Create reminders table if it doesn't exist
                            create_tables(db_conn)
                            
                            st.success(f"✅ Welcome {username}!")
                            st.rerun()
                        else:
                            st.error("❌ Invalid username or password")
                    except Exception as e:
                        st.error(f"Login error: {e}")
                else:
                    st.session_state.logged_in = True
                    st.session_state.current_user = username
                    st.session_state.video_processor = VideoProcessor()
                    st.session_state.motion_alerts = []
                    st.session_state.announcements = []
                    st.session_state.reminders = []
                    st.session_state.start_time = datetime.now()
                    st.success(f"✅ Welcome {username}!")
                    st.rerun()
            else:
                st.warning("Please enter username and password")

    # Register
    with col2:
        if st.button("📝 Register", use_container_width=True):
            if username and password:
                if db_available:
                    try:
                        cursor = db_conn.cursor()
                        cursor.execute(
                            "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
                            (username, password)
                        )
                        db_conn.commit()
                        st.success("✅ Account created! You can now login.")
                    except mysql.connector.Error as e:
                        if e.errno == 1062:
                            st.error("⚠️ Username already exists")
                        else:
                            st.error(f"Registration error: {e}")
                else:
                    if "local_users" not in st.session_state:
                        st.session_state.local_users = {}
                    
                    if username in st.session_state.local_users:
                        st.error("⚠️ Username already exists")
                    else:
                        st.session_state.local_users[username] = password
                        st.success("✅ Account created! You can now login.")
            else:
                st.warning("Please enter username and password")

# ------------------ MAIN SYSTEM ------------------
else:
    # Check for triggered reminders
    if hasattr(st.session_state, 'triggered_reminders') and st.session_state.triggered_reminders:
        for reminder in st.session_state.triggered_reminders[:]:
            if reminder.get("audio_message"):
                st.session_state.audio_system.play_audio(reminder["audio_message"])
            
            st.toast(f"🔔 REMINDER: {reminder['title']}\n{reminder['message']}", icon="⏰")
            
            st.session_state.announcements.append({
                "user": "REMINDER SYSTEM",
                "text": f"Reminder: {reminder['title']} - {reminder['message']}",
                "time": datetime.now().strftime("%H:%M:%S"),
                "type": "reminder"
            })
        st.session_state.triggered_reminders = []
    
    # Sidebar Navigation
    st.sidebar.markdown(f"**👤 User: {st.session_state.current_user}**")
    st.sidebar.markdown("---")
    
    page = st.sidebar.radio("Navigation", ["🎥 CCTV", "📢 Talk", "⏰ Reminders", "📊 Dashboard"])
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("📊 Status")
    
    if st.session_state.video_processor:
        st.sidebar.metric("Motion Events", st.session_state.video_processor.motion_count)
    
    if st.session_state.reminder_system:
        pending_reminders = len(st.session_state.reminder_system.get_pending_reminders())
        st.sidebar.metric("Active Reminders", pending_reminders)
    else:
        st.sidebar.metric("Active Reminders", 0)
    
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.current_user = ""
        st.rerun()
    
    # ------------------ CCTV PAGE ------------------
    if page == "🎥 CCTV":
        st.markdown(f"<h2 style='color:#FF5733;'>📹 CCTV MONITORING</h2>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("📢 Go to Talk", use_container_width=True):
                page = "📢 Talk"
                st.rerun()
        with col2:
            if st.button("⏰ Go to Reminders", use_container_width=True):
                page = "⏰ Reminders"
                st.rerun()
        with col3:
            current_time = datetime.now().strftime("%H:%M:%S")
            st.metric("Current Time", current_time)
        
        st.markdown("---")
        st.subheader("🎥 Live Camera Feed")
        
        RTC_CONFIGURATION = RTCConfiguration(
            {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
        )
        
        webrtc_ctx = webrtc_streamer(
            key="cctv-monitoring",
            mode=WebRtcMode.SENDRECV,
            rtc_configuration=RTC_CONFIGURATION,
            media_stream_constraints={
                "video": {"width": {"ideal": 1280}, "height": {"ideal": 720}, "frameRate": {"ideal": 30}},
                "audio": False
            },
            video_processor_factory=VideoProcessor,
            async_processing=True,
        )
        
        if not webrtc_ctx.state.playing:
            st.warning("⚠️ Camera feed not active")
            st.image("https://via.placeholder.com/640x360/333333/FFFFFF?text=Live+Camera+Feed")
    
    # ------------------ TALK PAGE ------------------
    elif page == "📢 Talk":
        st.markdown(f"<h2 style='color:#FF5733;'>📢 TALK & INTERCOM</h2>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🎤 Record Message")
            message_text = st.text_area("Message to broadcast", value="Take your medicine on time!", height=100)
            record_duration = st.slider("Recording time (seconds)", 3, 30, 10)
            
            if st.button("🎤 Record & Broadcast", use_container_width=True, type="primary"):
                with st.spinner(f"Recording for {record_duration} seconds..."):
                    audio_data = st.session_state.audio_system.record_audio(record_duration)
                    if audio_data:
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        st.session_state.announcements.append({
                            "user": st.session_state.current_user,
                            "text": message_text,
                            "time": timestamp,
                            "audio": audio_data,
                            "type": "broadcast"
                        })
                        st.success(f"✅ Message recorded! ({record_duration}s)")
                        st.session_state.audio_system.play_audio(audio_data)
                    else:
                        st.error("❌ Failed to record audio")
        
        with col2:
            st.subheader("📢 Quick Announcements")
            quick_msgs = st.columns(2)
            with quick_msgs[0]:
                if st.button("💊 Medicine Time", use_container_width=True):
                    msg = "Time to take your medicine! 💊"
                    audio = st.session_state.audio_system.text_to_speech(msg)
                    st.session_state.announcements.append({
                        "user": "SYSTEM", "text": msg, "time": datetime.now().strftime("%H:%M:%S"),
                        "audio": audio, "type": "quick"
                    })
                    st.session_state.audio_system.play_audio(audio)
                    st.success("Medicine reminder announced!")
            
            with quick_msgs[1]:
                if st.button("🍽️ Meal Time", use_container_width=True):
                    msg = "Time for your meal! 🍽️"
                    audio = st.session_state.audio_system.text_to_speech(msg)
                    st.session_state.announcements.append({
                        "user": "SYSTEM", "text": msg, "time": datetime.now().strftime("%H:%M:%S"),
                        "audio": audio, "type": "quick"
                    })
                    st.session_state.audio_system.play_audio(audio)
                    st.success("Meal reminder announced!")
            
            st.subheader("📋 Recent Messages")
            if st.session_state.announcements:
                for ann in reversed(st.session_state.announcements[-5:]):
                    st.write(f"**{ann['user']}** ({ann['time']}): {ann['text'][:50]}...")
            else:
                st.write("No messages yet")
    
    # ------------------ REMINDERS PAGE ------------------
    elif page == "⏰ Reminders":
        st.markdown(f"<h2 style='color:#FF5733;'>⏰ SMART REMINDERS</h2>", unsafe_allow_html=True)
        tab1, tab2, tab3 = st.tabs(["➕ Set New Reminder", "📋 Active Reminders", "🎯 Quick Presets"])
        
        with tab1:
            st.subheader("➕ Set New Reminder")
            reminder_title = st.text_input("Reminder Title", "Medicine Reminder")
            reminder_message = st.text_area("Reminder Message", "Time to take your medicine! 💊")
            
            col1, col2 = st.columns(2)
            with col1:
                schedule_type = st.radio("Schedule Type", ["In X minutes", "Specific Time", "Daily", "Hourly"])
                if schedule_type == "In X minutes":
                    minutes = st.number_input("Minutes from now", min_value=1, max_value=1440, value=5)
                    trigger_time = datetime.now() + timedelta(minutes=minutes)
                elif schedule_type == "Specific Time":
                    date = st.date_input("Date", datetime.now())
                    time_input = st.time_input("Time", datetime.now().time())
                    trigger_time = datetime.combine(date, time_input)
                elif schedule_type == "Daily":
                    time_input = st.time_input("Daily at", datetime.now().time())
                    trigger_time = datetime.combine(datetime.now().date(), time_input)
                    if trigger_time < datetime.now(): trigger_time += timedelta(days=1)
                elif schedule_type == "Hourly":
                    minute = st.number_input("Minute past each hour", min_value=0, max_value=59, value=0)
                    trigger_time = datetime.now().replace(minute=minute, second=0, microsecond=0)
                    if trigger_time < datetime.now(): trigger_time += timedelta(hours=1)
            
            with col2:
                st.subheader("🔊 Audio Settings")
                audio_option = st.radio("Audio Announcement", ["Text-to-Speech", "Record Voice", "Beep Sound", "No Audio"])
                audio_data = None
                if audio_option == "Text-to-Speech":
                    audio_data = st.session_state.audio_system.text_to_speech(reminder_message)
                elif audio_option == "Record Voice":
                    record_seconds = st.slider("Record for (seconds)", 3, 30, 10)
                    if st.button("🎤 Record Now"):
                        with st.spinner("Recording..."):
                            audio_data = st.session_state.audio_system.record_audio(record_seconds)
                            if audio_data: st.success("✅ Voice recorded!")
                            else: st.error("❌ Recording failed")
                elif audio_option == "Beep Sound":
                    beep_duration = st.slider("Beep duration (seconds)", 1, 10, 3)
                    audio_data = st.session_state.audio_system.generate_beep_sound(duration=beep_duration)
            
            repeat_option = "once"
            if schedule_type in ["Daily", "Hourly"]: repeat_option = schedule_type.lower()
            else: repeat_option = st.selectbox("Repeat", ["once", "daily", "hourly"])
            
            if st.button("✅ SET REMINDER", use_container_width=True, type="primary"):
                reminder = st.session_state.reminder_system.add_reminder(
                    title=reminder_title, message=reminder_message, trigger_time=trigger_time,
                    repeat=repeat_option, audio_message=audio_data
                )
                st.session_state.reminders.append(reminder)
                
                if db_available:
                    try:
                        cursor = db_conn.cursor()
                        cursor.execute(
                            "INSERT INTO reminders (username, title, message, trigger_time, repeat_type, audio_data, status) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                            (st.session_state.current_user, reminder_title, reminder_message, trigger_time, repeat_option, audio_data.getvalue() if audio_data else None, "pending")
                        )
                        db_conn.commit()
                    except Exception as e:
                        st.warning(f"⚠️ Could not save to database: {e}")
                
                st.success(f"✅ Reminder set for {trigger_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        with tab2:
            st.subheader("📋 Active Reminders")
            pending_reminders = st.session_state.reminder_system.get_pending_reminders()
            if pending_reminders:
                for reminder in pending_reminders:
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        st.write(f"**{reminder['title']}**")
                        st.write(reminder['message'])
                    with col2:
                        if st.button("▶️ Test", key=f"test_{reminder['id']}"):
                            if reminder.get("audio_message"): st.session_state.audio_system.play_audio(reminder["audio_message"])
                    with col3:
                        if st.button("❌ Cancel", key=f"cancel_{reminder['id']}"):
                            if st.session_state.reminder_system.cancel_reminder(reminder['id']):
                                st.success("Reminder cancelled!")
                                st.rerun()
                    st.markdown("---")
            else:
                st.info("📭 No active reminders")
        
        with tab3:
            st.subheader("🎯 Quick Preset Reminders")
            presets = st.columns(3)
            with presets[0]:
                if st.button("💊 Medicine\n(5 minutes)", use_container_width=True):
                    trigger_time = datetime.now() + timedelta(minutes=5)
                    audio = st.session_state.audio_system.text_to_speech("Time to take your medicine! 💊")
                    reminder = st.session_state.reminder_system.add_reminder(
                        title="Medicine Time", message="Take your prescribed medicine",
                        trigger_time=trigger_time, audio_message=audio
                    )
                    st.session_state.reminders.append(reminder)
                    st.success(f"✅ Medicine reminder set for 5 minutes!")
    
    # ------------------ DASHBOARD PAGE ------------------
    elif page == "📊 Dashboard":
        st.markdown(f"<h2 style='color:#FF5733;'>📊 SYSTEM DASHBOARD</h2>", unsafe_allow_html=True)
        col1, col2, col3, col4 = st.columns(4)
        
        # Stats with safety checks
        with col1:
            active_val = len(st.session_state.reminder_system.get_pending_reminders()) if st.session_state.reminder_system else 0
            st.metric("Active Reminders", active_val)
        with col2:
            motion_val = st.session_state.video_processor.motion_count if st.session_state.video_processor else 0
            st.metric("Motion Events", motion_val)
        with col3:
            st.metric("Announcements", len(st.session_state.announcements))
        with col4:
            uptime = f"{(datetime.now() - st.session_state.start_time).seconds // 60}m" if st.session_state.start_time else "0m"
            st.metric("System Uptime", uptime)
        
        st.subheader("⏰ Upcoming Reminders")
        if st.session_state.reminder_system:
            upcoming = st.session_state.reminder_system.get_upcoming_reminders(5)
            if upcoming:
                for reminder in upcoming:
                    st.write(f"**{reminder['title']}** - {reminder['message']}")
            else:
                st.info("No upcoming reminders")
        else:
            st.info("Reminder system restricted")

# ------------------ DATABASE SETUP ------------------
with st.sidebar.expander("🔧 Database Setup"):
    if st.button("🛠️ Create Tables Automatically"):
        if db_available:
            success, msg = create_tables(db_conn)
            if success: st.success(msg)
            else: st.error(msg)
        else:
            st.error("❌ Database not available")

# Cleanup on app close
@atexit.register
def cleanup():
    if "reminder_system" in st.session_state:
        st.session_state.reminder_system.stop()
    if 'db_conn' in locals() and db_conn:
        db_conn.close()
