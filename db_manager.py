"""
Database manager for persistent pattern storage.
Supports both PostgreSQL (via DATABASE_URL from Vercel/Supabase)
and local SQLite (fallback).
"""
import os
import json
from datetime import datetime

# Vercel filesystem read-only workaround for SQLite fallback
if os.environ.get("VERCEL"):
    LOCAL_DB_DIR = '/tmp'
else:
    LOCAL_DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database')

LOCAL_DB_PATH = os.path.join(LOCAL_DB_DIR, 'scheduler.db')
DB_URL = os.environ.get("DATABASE_URL")

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    pass

import sqlite3

def get_connection():
    """Get a connection to PostgreSQL if configured, otherwise SQLite."""
    if DB_URL:
        # Use Postgres
        conn = psycopg2.connect(DB_URL)
        _init_postgres_schema(conn)
        return {"conn": conn, "type": "postgres"}
    else:
        # Use SQLite
        os.makedirs(LOCAL_DB_DIR, exist_ok=True)
        conn = sqlite3.connect(LOCAL_DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        _init_sqlite_schema(conn)
        return {"conn": conn, "type": "sqlite"}

def execute_query(db, query, params=(), fetchall=False, fetchone=False, commit=False):
    """Executes a query abstracting differences between SQLite and Postgres."""
    conn = db["conn"]
    db_type = db["type"]
    
    if db_type == "postgres":
        # Translate '?' to '%s'
        pg_query = query.replace('?', '%s')
        
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(pg_query, params)
        res = None
        if fetchall:
            res = cur.fetchall()
        elif fetchone:
            res = cur.fetchone()
        
        if commit:
            conn.commit()
            
        cur.close()
        return res
        
    else:
        # SQLite
        cur = conn.execute(query, params)
        res = None
        if fetchall:
            res = cur.fetchall()
            # Convert to dicts to match Postgres RealDictCursor
            res = [dict(row) for row in res]
        elif fetchone:
            res = cur.fetchone()
            if res:
                res = dict(res)
                
        if commit:
            conn.commit()
        return res


def _init_postgres_schema(conn):
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS shift_patterns (
            id SERIAL PRIMARY KEY,
            segments_key TEXT UNIQUE NOT NULL,
            segments_json TEXT NOT NULL,
            total_min INTEGER NOT NULL,
            slot_type TEXT NOT NULL,
            frequency INTEGER DEFAULT 1,
            first_seen TEXT NOT NULL,
            last_seen TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS employee_preferences (
            id SERIAL PRIMARY KEY,
            employee_id TEXT NOT NULL,
            employee_name TEXT NOT NULL,
            pattern_key TEXT NOT NULL,
            day_of_week TEXT,
            frequency INTEGER DEFAULT 1,
            last_seen TEXT NOT NULL,
            UNIQUE(employee_id, pattern_key, day_of_week)
        );
        CREATE TABLE IF NOT EXISTS import_log (
            id SERIAL PRIMARY KEY,
            import_date TEXT NOT NULL,
            num_employees INTEGER,
            num_patterns_learned INTEGER,
            source_file TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_patterns_freq ON shift_patterns(frequency DESC);
        CREATE INDEX IF NOT EXISTS idx_emp_prefs_id ON employee_preferences(employee_id);
    """)
    conn.commit()
    cur.close()

def _init_sqlite_schema(conn):
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
            employee_id TEXT NOT NULL,
            employee_name TEXT NOT NULL,
            pattern_key TEXT NOT NULL,
            day_of_week TEXT,
            frequency INTEGER DEFAULT 1,
            last_seen TEXT NOT NULL,
            UNIQUE(employee_id, pattern_key, day_of_week)
        );
        CREATE TABLE IF NOT EXISTS import_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            import_date TEXT NOT NULL,
            num_employees INTEGER,
            num_patterns_learned INTEGER,
            source_file TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_patterns_freq ON shift_patterns(frequency DESC);
        CREATE INDEX IF NOT EXISTS idx_emp_prefs_id ON employee_preferences(employee_id);
    """)
    conn.commit()


def learn_patterns(employees, store_open_str='09:30', store_close_str='19:30', source_file='csv_import'):
    from cp_sat.solver import parse_shift_segments, classify_slot, time_to_min, DAY_NAMES
    
    store_open = time_to_min(store_open_str)
    store_close = time_to_min(store_close_str)
    
    db = get_connection()
    now = datetime.now().isoformat()
    patterns_learned = 0
    
    for emp in employees:
        emp_id = str(emp.get('ID', '')).strip()
        emp_name = emp.get('Nome Cognome', emp.get('Nome', 'Unknown')).strip()
        
        for day_name in DAY_NAMES:
            shift_str = (emp.get(day_name, '') or '').strip()
            if not shift_str or shift_str.lower() in ('riposo', 'chiuso', ''):
                continue
            
            segments = parse_shift_segments(shift_str)
            if not segments:
                continue
            
            seg_key = '|'.join(f"{s['start']}-{s['end']}" for s in sorted(segments, key=lambda x: x['start']))
            seg_json = json.dumps([{'start': s['start'], 'end': s['end']} for s in segments])
            total_min = sum(s['end'] - s['start'] for s in segments)
            slot = classify_slot(segments, store_open, store_close)
            
            query_sp = """
                INSERT INTO shift_patterns (segments_key, segments_json, total_min, slot_type, frequency, first_seen, last_seen)
                VALUES (?, ?, ?, ?, 1, ?, ?)
                ON CONFLICT(segments_key) DO UPDATE SET
                    frequency = shift_patterns.frequency + 1,
                    last_seen = excluded.last_seen
            """
            execute_query(db, query_sp, (seg_key, seg_json, total_min, slot, now, now))
            patterns_learned += 1
            
            query_ep = """
                INSERT INTO employee_preferences (employee_id, employee_name, pattern_key, day_of_week, frequency, last_seen)
                VALUES (?, ?, ?, ?, 1, ?)
                ON CONFLICT(employee_id, pattern_key, day_of_week) DO UPDATE SET
                    employee_name = excluded.employee_name,
                    frequency = employee_preferences.frequency + 1,
                    last_seen = excluded.last_seen
            """
            execute_query(db, query_ep, (emp_id, emp_name, seg_key, day_name, now))
    
    query_log = """
        INSERT INTO import_log (import_date, num_employees, num_patterns_learned, source_file)
        VALUES (?, ?, ?, ?)
    """
    execute_query(db, query_log, (now, len(employees), patterns_learned, source_file), commit=True)
    db["conn"].close()
    
    return patterns_learned


def get_top_patterns(limit=30, min_frequency=1):
    db = get_connection()
    query = """
        SELECT segments_key, segments_json, total_min, slot_type, frequency
        FROM shift_patterns
        WHERE frequency >= ?
        ORDER BY frequency DESC
        LIMIT ?
    """
    rows = execute_query(db, query, (min_frequency, limit), fetchall=True)
    db["conn"].close()
    
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


def get_employee_preferred_patterns(employee_id, limit=10):
    db = get_connection()
    query = """
        SELECT ep.pattern_key, sp.segments_json, sp.total_min, sp.slot_type,
               SUM(ep.frequency) as frequency
        FROM employee_preferences ep
        JOIN shift_patterns sp ON ep.pattern_key = sp.segments_key
        WHERE ep.employee_id = ?
        GROUP BY ep.pattern_key, sp.segments_json, sp.total_min, sp.slot_type
        ORDER BY frequency DESC
        LIMIT ?
    """
    rows = execute_query(db, query, (employee_id, limit), fetchall=True)
    db["conn"].close()
    
    return [
        {
            'segments': json.loads(row['segments_json']),
            'total_min': row['total_min'],
            'slot': row['slot_type'],
            'frequency': row['frequency'],
        }
        for row in rows
    ]


def get_employee_preferred_patterns_by_day(employee_id, day_of_week, limit=10, min_day_patterns=3):
    db = get_connection()

    query_day = """
        SELECT ep.pattern_key, sp.segments_json, sp.total_min, sp.slot_type, ep.frequency
        FROM employee_preferences ep
        JOIN shift_patterns sp ON ep.pattern_key = sp.segments_key
        WHERE ep.employee_id = ? AND ep.day_of_week = ?
        ORDER BY ep.frequency DESC
        LIMIT ?
    """
    day_rows = execute_query(db, query_day, (employee_id, day_of_week, limit), fetchall=True)

    results = [
        {
            'segments': json.loads(row['segments_json']),
            'total_min': row['total_min'],
            'slot': row['slot_type'],
            'frequency': row['frequency'],
            'day_specific': True,
        }
        for row in day_rows
    ]
    day_keys = {row['pattern_key'] for row in day_rows}

    if len(results) < min_day_patterns:
        remaining = limit - len(results)
        
        placeholders = ','.join('?' * len(day_keys)) if day_keys else "'__none__'"
        
        query_global = f"""
            SELECT ep.pattern_key, sp.segments_json, sp.total_min, sp.slot_type,
                   SUM(ep.frequency) as frequency
            FROM employee_preferences ep
            JOIN shift_patterns sp ON ep.pattern_key = sp.segments_key
            WHERE ep.employee_id = ? AND ep.pattern_key NOT IN ({placeholders})
            GROUP BY ep.pattern_key, sp.segments_json, sp.total_min, sp.slot_type
            ORDER BY frequency DESC
            LIMIT ?
        """
        params = [employee_id] + list(day_keys) + [remaining]
        global_rows = execute_query(db, query_global, params, fetchall=True)

        for row in global_rows:
            results.append({
                'segments': json.loads(row['segments_json']),
                'total_min': row['total_min'],
                'slot': row['slot_type'],
                'frequency': max(1, row['frequency'] // 2),
                'day_specific': False,
            })

    db["conn"].close()
    return results


def get_top_patterns_by_day(day_of_week, limit=30, min_frequency=1):
    db = get_connection()

    query = """
        SELECT sp.segments_key, sp.segments_json, sp.total_min, sp.slot_type,
               SUM(ep.frequency) as day_frequency
        FROM employee_preferences ep
        JOIN shift_patterns sp ON ep.pattern_key = sp.segments_key
        WHERE ep.day_of_week = ?
        GROUP BY sp.segments_key, sp.segments_json, sp.total_min, sp.slot_type
        HAVING SUM(ep.frequency) >= ?
        ORDER BY day_frequency DESC
        LIMIT ?
    """
    rows = execute_query(db, query, (day_of_week, min_frequency, limit), fetchall=True)

    db["conn"].close()

    patterns = []
    for row in rows:
        segments = json.loads(row['segments_json'])
        patterns.append({
            'name': f"db_{row['slot_type']}_{row['day_frequency']}x_{day_of_week}",
            'segments': segments,
            'total_min': row['total_min'],
            'slot': row['slot_type'],
            'frequency': row['day_frequency'],
            'from_db': True,
        })

    return patterns

def get_stats():
    db = get_connection()
    
    total_patterns = execute_query(db, "SELECT COUNT(*) as count FROM shift_patterns", fetchone=True)['count']
    total_imports = execute_query(db, "SELECT COUNT(*) as count FROM import_log", fetchone=True)['count']
    total_employees = execute_query(db, "SELECT COUNT(DISTINCT employee_id) as count FROM employee_preferences", fetchone=True)['count']
    top_pattern = execute_query(db, "SELECT segments_key, frequency FROM shift_patterns ORDER BY frequency DESC LIMIT 1", fetchone=True)
    
    db["conn"].close()
    
    return {
        'total_patterns': total_patterns,
        'total_imports': total_imports,
        'total_employees_tracked': total_employees,
        'top_pattern': dict(top_pattern) if top_pattern else None,
    }
