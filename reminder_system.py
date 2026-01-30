import threading
import time
import streamlit as st
from datetime import datetime, timedelta
from config import TIMEZONE

class ReminderSystem:
    def __init__(self):
        self.reminders = []
        self.active_reminders = []
        self.reminder_thread = None
        self.running = False
        self.timezone = TIMEZONE
        
    def add_reminder(self, title, message, trigger_time, repeat="once", audio_message=None):
        """Add a new reminder"""
        reminder = {
            "id": len(self.reminders) + 1,
            "title": title,
            "message": message,
            "trigger_time": trigger_time,
            "repeat": repeat,
            "audio_message": audio_message,
            "created_at": datetime.now(self.timezone),
            "status": "pending",
            "triggered": False
        }
        
        self.reminders.append(reminder)
        
        # Add to active reminders if not triggered
        if trigger_time > datetime.now(self.timezone):
            self.active_reminders.append(reminder)
        
        return reminder
    
    def check_reminders(self):
        """Check and trigger reminders"""
        current_time = datetime.now(self.timezone)
        triggered = []
        
        for reminder in self.active_reminders[:]:
            if reminder["trigger_time"] <= current_time and not reminder["triggered"]:
                # Trigger this reminder
                reminder["triggered"] = True
                reminder["triggered_at"] = current_time
                reminder["status"] = "triggered"
                triggered.append(reminder)
                
                # Handle repeat
                if reminder["repeat"] == "daily":
                    # Schedule for next day
                    new_time = reminder["trigger_time"] + timedelta(days=1)
                    new_reminder = reminder.copy()
                    new_reminder["trigger_time"] = new_time
                    new_reminder["triggered"] = False
                    new_reminder["status"] = "pending"
                    self.active_reminders.append(new_reminder)
                elif reminder["repeat"] == "hourly":
                    # Schedule for next hour
                    new_time = reminder["trigger_time"] + timedelta(hours=1)
                    new_reminder = reminder.copy()
                    new_reminder["trigger_time"] = new_time
                    new_reminder["triggered"] = False
                    new_reminder["status"] = "pending"
                    self.active_reminders.append(new_reminder)
        
        # Remove triggered reminders from active list
        self.active_reminders = [r for r in self.active_reminders if not r.get("triggered", False)]
        
        return triggered
    
    def get_pending_reminders(self):
        """Get reminders that are still pending"""
        return [r for r in self.reminders if r["status"] == "pending"]
    
    def get_upcoming_reminders(self, count=5):
        """Get upcoming reminders"""
        pending = self.get_pending_reminders()
        pending.sort(key=lambda x: x["trigger_time"])
        return pending[:count]
    
    def cancel_reminder(self, reminder_id):
        """Cancel a reminder"""
        for reminder in self.reminders:
            if reminder["id"] == reminder_id:
                reminder["status"] = "cancelled"
                self.active_reminders = [r for r in self.active_reminders if r["id"] != reminder_id]
                return True
        return False
    
    def start_background_check(self):
        """Start background thread to check reminders"""
        if not self.running:
            self.running = True
            self.reminder_thread = threading.Thread(target=self._background_check, daemon=True)
            self.reminder_thread.start()
    
    def _background_check(self):
        """Background thread to check reminders"""
        while self.running:
            triggered = self.check_reminders()
            if triggered:
                # Store triggered reminders for UI
                if "triggered_reminders" not in st.session_state:
                    st.session_state.triggered_reminders = []
                st.session_state.triggered_reminders.extend(triggered)
            
            time.sleep(1)  # Check every second
    
    def stop(self):
        """Stop the reminder system"""
        self.running = False
        if self.reminder_thread:
            self.reminder_thread.join(timeout=1)
