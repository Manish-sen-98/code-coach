import sqlite3
import json
import os

# Project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "code_coach.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            mindset TEXT,
            level TEXT,
            domain TEXT,
            onboarding_step INTEGER DEFAULT 0,
            current_mode TEXT DEFAULT 'knowledge',
            current_topic TEXT,
            history TEXT DEFAULT '[]',
            last_interaction TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Migration: Add columns if they don't exist
    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]
    if "domain" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN domain TEXT")
    if "onboarding_step" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN onboarding_step INTEGER DEFAULT 0")
    if "current_mode" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN current_mode TEXT DEFAULT 'knowledge'")
    
    # Solved questions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS session_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            interaction_type TEXT,
            content TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def get_user_state(user_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row # This allows us to access columns by name
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (str(user_id),))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            "user_id": row["user_id"],
            "mindset": row["mindset"],
            "level": row["level"],
            "domain": row["domain"],
            "onboarding_step": row["onboarding_step"],
            "current_mode": row["current_mode"],
            "current_topic": row["current_topic"],
            "history": json.loads(row["history"])
        }
    return None

def update_user_state(user_id, mindset=None, level=None, domain=None, onboarding_step=None, current_mode=None, current_topic=None, history=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if user exists
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (str(user_id),))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (user_id, history) VALUES (?, ?)", (str(user_id), '[]'))
    
    if mindset is not None:
        cursor.execute("UPDATE users SET mindset = ? WHERE user_id = ?", (mindset, str(user_id)))
    if level is not None:
        cursor.execute("UPDATE users SET level = ? WHERE user_id = ?", (level, str(user_id)))
    if domain is not None:
        cursor.execute("UPDATE users SET domain = ? WHERE user_id = ?", (domain, str(user_id)))
    if onboarding_step is not None:
        cursor.execute("UPDATE users SET onboarding_step = ? WHERE user_id = ?", (onboarding_step, str(user_id)))
    if current_mode is not None:
        cursor.execute("UPDATE users SET current_mode = ? WHERE user_id = ?", (current_mode, str(user_id)))
    if current_topic is not None:
        cursor.execute("UPDATE users SET current_topic = ? WHERE user_id = ?", (current_topic, str(user_id)))
    if history is not None:
        cursor.execute("UPDATE users SET history = ? WHERE user_id = ?", (json.dumps(history), str(user_id)))
    
    conn.commit()
    conn.close()

def log_interaction(user_id, interaction_type, content):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO session_logs (user_id, interaction_type, content) VALUES (?, ?, ?)",
        (str(user_id), interaction_type, json.dumps(content))
    )
    conn.commit()
    conn.close()

def get_user_history_logs(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT interaction_type, content, timestamp FROM session_logs WHERE user_id = ? ORDER BY timestamp ASC", (str(user_id),))
    rows = cursor.fetchall()
    conn.close()
    return rows

# Initialize on import
init_db()
