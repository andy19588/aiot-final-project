import sqlite3
import os
from datetime import datetime

DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "sensor_data.db")

def get_connection(db_path=DEFAULT_DB_PATH):
    """Returns a connection to the SQLite database."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path=DEFAULT_DB_PATH):
    """Initializes the database schema if it doesn't already exist."""
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    
    with get_connection(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                current_rms REAL NOT NULL,
                apparent_power REAL NOT NULL,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)
        
        # Index on timestamp for faster time-range querying
        conn.execute("CREATE INDEX IF NOT EXISTS idx_readings_timestamp ON readings(timestamp)")
        conn.commit()
    print(f"Database initialized at: {db_path}")

def insert_reading(timestamp, current_rms, apparent_power, db_path=DEFAULT_DB_PATH):
    """Inserts a single sensor reading into the database."""
    with get_connection(db_path) as conn:
        conn.execute(
            "INSERT INTO readings (timestamp, current_rms, apparent_power) VALUES (?, ?, ?)",
            (timestamp, current_rms, apparent_power)
        )
        conn.commit()

def get_readings(limit=100, offset=0, start_date=None, end_date=None, db_path=DEFAULT_DB_PATH):
    """Retrieves list of readings filtered by date and paginated."""
    query = "SELECT id, timestamp, current_rms, apparent_power, created_at FROM readings WHERE 1=1"
    params = []
    
    if start_date:
        query += " AND timestamp >= ?"
        params.append(start_date)
    if end_date:
        query += " AND timestamp <= ?"
        params.append(end_date)
        
    query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def get_stats(db_path=DEFAULT_DB_PATH):
    """Retrieves aggregate statistics for dashboard metrics."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        
        # Total records count
        cursor.execute("SELECT COUNT(*) as count FROM readings")
        total_count = cursor.fetchone()['count']
        
        if total_count == 0:
            return {
                "count": 0,
                "max_current": 0.0,
                "avg_power": 0.0,
                "total_energy_kwh": 0.0,
                "latest_reading": None
            }
            
        # Max current and avg power
        cursor.execute("""
            SELECT 
                MAX(current_rms) as max_current, 
                AVG(apparent_power) as avg_power 
            FROM readings
        """)
        stats_row = cursor.fetchone()
        
        # Latest reading
        cursor.execute("""
            SELECT timestamp, current_rms, apparent_power 
            FROM readings 
            ORDER BY timestamp DESC 
            LIMIT 1
        """)
        latest_row = cursor.fetchone()
        latest_reading = dict(latest_row) if latest_row else None
        
        # Estimate total energy consumed (kWh)
        # Approximate: Average Power (W) * total time elapsed in hours / 1000
        # First, find time span in seconds
        cursor.execute("""
            SELECT 
                (strftime('%s', MAX(timestamp)) - strftime('%s', MIN(timestamp))) as duration_seconds 
            FROM readings
        """)
        duration_row = cursor.fetchone()
        duration_seconds = duration_row['duration_seconds'] if duration_row and duration_row['duration_seconds'] else 0
        
        # Energy = Avg Power (W) * (seconds / 3600) / 1000 = Avg Power * seconds / 3600000
        avg_power = stats_row['avg_power'] or 0.0
        total_energy_kwh = (avg_power * duration_seconds) / 3600000.0
        
        return {
            "count": total_count,
            "max_current": round(stats_row['max_current'] or 0.0, 3),
            "avg_power": round(avg_power, 2),
            "total_energy_kwh": round(total_energy_kwh, 4),
            "latest_reading": latest_reading
        }

if __name__ == "__main__":
    init_db()
