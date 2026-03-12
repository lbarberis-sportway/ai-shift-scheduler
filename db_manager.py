"""
Database manager for persistent pattern storage.
Uses SQLite to store shift patterns learned from every CSV import.
The more CSVs are imported, the richer the pattern library becomes.
"""
import sqlite3
import os
import json
from datetime import datetime

DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database')
DB_PATH = os.path.join(DB_DIR, 'scheduler.db')


def get_connection():
    """Get a connection to the SQLite database, creating it if needed."""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    _init_schema(conn)
    return conn


def _init_schema(conn):
    """Create tables if they don't exist."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS shift_patterns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            segments_key TEXT UNIQUE NOT NULL,
            segments_json TEXT NOT NULL,
            total_min INTEGER NOT NULL,
            slot_type TEXT NOT NULL,
            frequency INTEGER DEFAULT 1,
            first_seen TEXT NOT NULL,
            last_seen TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS employee_preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_name TEXT NOT NULL,
            pattern_key TEXT NOT NULL,
            day_of_week TEXT,
            frequency INTEGER DEFAULT 1,
            last_seen TEXT NOT NULL,
            UNIQUE(employee_name, pattern_key, day_of_week)
        );

        CREATE TABLE IF NOT EXISTS import_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            import_date TEXT NOT NULL,
            num_employees INTEGER,
            num_patterns_learned INTEGER,
            source_file TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_patterns_freq
            ON shift_patterns(frequency DESC);
        CREATE INDEX IF NOT EXISTS idx_emp_prefs_name
            ON employee_preferences(employee_name);
    """)
    conn.commit()


def learn_patterns(employees, store_open_str='09:30', store_close_str='19:30', source_file='csv_import'):
    """
    Extract and store shift patterns from employee data.
    Called every time a CSV is imported.
    
    Args:
        employees: list of dicts with day columns (Lun, Mar, etc.)
        store_open_str: store opening time
        store_close_str: store closing time
        source_file: identifier for the import source
    
    Returns:
        Number of patterns learned/updated
    """
    from cp_sat.solver import parse_shift_segments, classify_slot, time_to_min, DAY_NAMES
    
    store_open = time_to_min(store_open_str)
    store_close = time_to_min(store_close_str)
    
    conn = get_connection()
    now = datetime.now().isoformat()
    patterns_learned = 0
    
    for emp in employees:
        emp_name = emp.get('Nome', 'Unknown')
        
        for day_name in DAY_NAMES:
            shift_str = (emp.get(day_name, '') or '').strip()
            if not shift_str or shift_str.lower() in ('riposo', 'chiuso', ''):
                continue
            
            segments = parse_shift_segments(shift_str)
            if not segments:
                continue
            
            # Create a canonical key for this pattern
            seg_key = '|'.join(f"{s['start']}-{s['end']}" for s in sorted(segments, key=lambda x: x['start']))
            seg_json = json.dumps([{'start': s['start'], 'end': s['end']} for s in segments])
            total_min = sum(s['end'] - s['start'] for s in segments)
            slot = classify_slot(segments, store_open, store_close)
            
            # Upsert the pattern
            conn.execute("""
                INSERT INTO shift_patterns (segments_key, segments_json, total_min, slot_type, frequency, first_seen, last_seen)
                VALUES (?, ?, ?, ?, 1, ?, ?)
                ON CONFLICT(segments_key) DO UPDATE SET
                    frequency = frequency + 1,
                    last_seen = ?
            """, (seg_key, seg_json, total_min, slot, now, now, now))
            patterns_learned += 1
            
            # Track employee-specific preferences
            conn.execute("""
                INSERT INTO employee_preferences (employee_name, pattern_key, day_of_week, frequency, last_seen)
                VALUES (?, ?, ?, 1, ?)
                ON CONFLICT(employee_name, pattern_key, day_of_week) DO UPDATE SET
                    frequency = frequency + 1,
                    last_seen = ?
            """, (emp_name, seg_key, day_name, now, now))
    
    # Log the import
    conn.execute("""
        INSERT INTO import_log (import_date, num_employees, num_patterns_learned, source_file)
        VALUES (?, ?, ?, ?)
    """, (now, len(employees), patterns_learned, source_file))
    
    conn.commit()
    conn.close()
    
    return patterns_learned


def get_top_patterns(limit=30, min_frequency=1):
    """
    Retrieve the most frequently used shift patterns from the database.
    
    Args:
        limit: maximum number of patterns to return
        min_frequency: minimum times a pattern must have appeared
    
    Returns:
        List of pattern dicts ready for the solver
    """
    conn = get_connection()
    
    rows = conn.execute("""
        SELECT segments_key, segments_json, total_min, slot_type, frequency
        FROM shift_patterns
        WHERE frequency >= ?
        ORDER BY frequency DESC
        LIMIT ?
    """, (min_frequency, limit)).fetchall()
    
    conn.close()
    
    patterns = []
    for row in rows:
        segments = json.loads(row['segments_json'])
        patterns.append({
            'name': f"db_{row['slot_type']}_{row['frequency']}x",
            'segments': segments,
            'total_min': row['total_min'],
            'slot': row['slot_type'],
            'frequency': row['frequency'],
            'from_db': True,
        })
    
    return patterns


def get_employee_preferred_patterns(employee_name, limit=10):
    """
    Get patterns that a specific employee has used most frequently.
    """
    conn = get_connection()
    
    rows = conn.execute("""
        SELECT ep.pattern_key, sp.segments_json, sp.total_min, sp.slot_type, ep.frequency
        FROM employee_preferences ep
        JOIN shift_patterns sp ON ep.pattern_key = sp.segments_key
        WHERE ep.employee_name = ?
        ORDER BY ep.frequency DESC
        LIMIT ?
    """, (employee_name, limit)).fetchall()
    
    conn.close()
    
    return [
        {
            'segments': json.loads(row['segments_json']),
            'total_min': row['total_min'],
            'slot': row['slot_type'],
            'frequency': row['frequency'],
        }
        for row in rows
    ]


def get_stats():
    """Get summary statistics of the pattern database."""
    conn = get_connection()
    
    total_patterns = conn.execute("SELECT COUNT(*) FROM shift_patterns").fetchone()[0]
    total_imports = conn.execute("SELECT COUNT(*) FROM import_log").fetchone()[0]
    total_employees = conn.execute("SELECT COUNT(DISTINCT employee_name) FROM employee_preferences").fetchone()[0]
    top_pattern = conn.execute(
        "SELECT segments_key, frequency FROM shift_patterns ORDER BY frequency DESC LIMIT 1"
    ).fetchone()
    
    conn.close()
    
    return {
        'total_patterns': total_patterns,
        'total_imports': total_imports,
        'total_employees_tracked': total_employees,
        'top_pattern': dict(top_pattern) if top_pattern else None,
    }
