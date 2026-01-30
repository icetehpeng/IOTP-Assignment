import mysql.connector
import streamlit as st
from config import DB_CONFIG

def get_db_connection():
    """Try to connect to MySQL database"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn, True
    except mysql.connector.Error as e:
        st.sidebar.warning(f"⚠️ MySQL not available: {e}")
        return None, False

def create_tables(db_conn):
    """Create database tables automatically"""
    try:
        cursor = db_conn.cursor()
        
        # Create users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create activity_log table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS activity_log (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50),
                activity VARCHAR(255),
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create reminders table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50),
                title VARCHAR(100),
                message TEXT,
                trigger_time DATETIME,
                repeat_type VARCHAR(20),
                audio_data LONGBLOB,
                status VARCHAR(20),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        db_conn.commit()
        return True, "✅ Tables created successfully!"
        
    except Exception as e:
        return False, f"❌ Error creating tables: {e}"
