#!/usr/bin/env python3
"""
Advanced CP-SAT scheduler that GENERATES new shifts for the upcoming week.

Key design:
- LEARNS shift patterns from CSV historical data (real patterns used in the store).
- Supplements with auto-generated fallback patterns for full coverage.
- Uses optimization objective to ROTATE employees (vary morning/afternoon).
- GUARANTEES: full coverage, contract hours, opening/closing presence.
"""
from __future__ import print_function
import sys
import os
import csv
import random
from collections import defaultdict
from ortools.sat.python import cp_model

DAY_NAMES = ['Lun', 'Mar', 'Mer', 'Gio', 'Ven', 'Sab', 'Dom']
INTERVAL = 30  # 30-minute time blocks


def time_to_min(t):
    if not t or ':' not in t: return 0
    try:
        h, m = map(int, t.split(':'))
        return h * 60 + m
    except:
        return 0


def to_hhmm(mins):
    h = mins // 60
    m = mins % 60
    return f"{h:02d}:{m:02d}"


def parse_shift_segments(shift_str):
    """Parse a shift string like '09:30-12:30/15:00-19:30' into segment dicts."""
    shift_str = (shift_str or '').strip()
    if not shift_str or shift_str.lower() in ('riposo', 'chiuso', ''):
        return []
    parts = shift_str.split('/')
    segs = []
    for p in parts:
        if '-' not in p:
            continue
        try:
            a, b = p.split('-')
            start = time_to_min(a.strip())
            end = time_to_min(b.strip())
            if end > start:
                segs.append({'start': start, 'end': end})
        except:
            continue
    return segs


def segments_to_key(segments):
    """Create a hashable key from segments for deduplication."""
    return tuple(sorted((s['start'], s['end']) for s in segments))


def classify_slot(segments, store_open, store_close):
    """Classify a shift pattern as morning, afternoon, split, or full."""
    if not segments:
        return 'rest'
    
    total_dur = sum(s['end'] - s['start'] for s in segments)
    mid = store_open + (store_close - store_open) // 2
    
    if len(segments) >= 2:
        return 'split'
    
    store_dur = store_close - store_open
    if total_dur >= store_dur - 30:  # Within 30min of full day
        return 'full'
    
    avg_center = sum((s['start'] + s['end']) / 2 for s in segments) / len(segments)
    if avg_center <= mid:
        return 'morning'
    else:
        return 'afternoon'


def extract_patterns_from_data(employees, store_open, store_close):
    """
    Extract ALL unique shift patterns from CSV historical data.
    These are REAL patterns that the store uses.
    """
    seen_patterns = {}  # key -> { segments, count, slot, total_min }
    
    for emp in employees:
        for day in DAY_NAMES:
            shift_str = emp.get(day, '').strip()
            if not shift_str or shift_str.lower() in ('riposo', 'chiuso', ''):
                continue
            
            segments = parse_shift_segments(shift_str)
            if not segments:
                continue
            
            key = segments_to_key(segments)
            total_min = sum(s['end'] - s['start'] for s in segments)
            
            if key not in seen_patterns:
                slot = classify_slot(segments, store_open, store_close)
                seen_patterns[key] = {
                    'segments': [{'start': s['start'], 'end': s['end']} for s in segments],
                    'total_min': total_min,
                    'slot': slot,
                    'count': 0,
                    'name': f"pattern_{to_hhmm(segments[0]['start'])}",
                }
            seen_patterns[key]['count'] += 1
    
    # Sort by frequency (most used patterns first)
    patterns = sorted(seen_patterns.values(), key=lambda p: -p['count'])
    return patterns


def build_fallback_shifts(store_open, store_close):
    """
    Generate essential shift types to guarantee full coverage.
    These complement the extracted patterns.
    """
    total_store_min = store_close - store_open
    mid = store_open + total_store_min // 2
    
    shifts = []
    
    # Morning: covers opening till mid
    shifts.append({
        'name': 'fb_mattina',
        'segments': [{'start': store_open, 'end': mid}],
        'total_min': mid - store_open,
        'slot': 'morning'
    })
    
    # Afternoon: covers mid till closing
    shifts.append({
        'name': 'fb_pomeriggio',
        'segments': [{'start': mid, 'end': store_close}],
        'total_min': store_close - mid,
        'slot': 'afternoon'
    })
    
    # Full day (if <= 9h)
    if total_store_min <= 9 * 60:
        shifts.append({
            'name': 'fb_giornata',
            'segments': [{'start': store_open, 'end': store_close}],
            'total_min': total_store_min,
            'slot': 'full'
        })
    
    # Generate overlapping shifts to guarantee coverage of mid-day
    # These are critical: they ensure no gaps around the midpoint
    
    # Morning extended (covers past midpoint)
    ext_morning_end = min(mid + 60, store_close)
    if ext_morning_end != mid:
        shifts.append({
            'name': 'fb_mattina_lunga',
            'segments': [{'start': store_open, 'end': ext_morning_end}],
            'total_min': ext_morning_end - store_open,
            'slot': 'morning'
        })
    
    # Afternoon extended (starts before midpoint)
    ext_afternoon_start = max(mid - 60, store_open)
    if ext_afternoon_start != mid:
        shifts.append({
            'name': 'fb_pomeriggio_lungo',
            'segments': [{'start': ext_afternoon_start, 'end': store_close}],
            'total_min': store_close - ext_afternoon_start,
            'slot': 'afternoon'
        })
    
    # Short morning (4h from open)
    short_m_end = store_open + 4 * 60
    if short_m_end < mid:
        shifts.append({
            'name': 'fb_mattina_corta',
            'segments': [{'start': store_open, 'end': short_m_end}],
            'total_min': 4 * 60,
            'slot': 'morning'
        })
    
    # Short afternoon (last 4h)
    short_a_start = store_close - 4 * 60
    if short_a_start > mid:
        shifts.append({
            'name': 'fb_pomeriggio_corto',
            'segments': [{'start': short_a_start, 'end': store_close}],
            'total_min': 4 * 60,
            'slot': 'afternoon'
        })
    
    # Central shift that bridges the midpoint (crucial for coverage!)
    central_start = mid - 2 * 60
    central_end = mid + 2 * 60
    if central_start >= store_open and central_end <= store_close:
        shifts.append({
            'name': 'fb_centrale',
            'segments': [{'start': central_start, 'end': central_end}],
            'total_min': 4 * 60,
            'slot': 'morning'  # technically middle
        })
    
    # Spezzato: opening + closing
    split_m_end = store_open + 4 * 60
    split_a_start = store_close - 4 * 60
    if split_m_end < split_a_start:
        shifts.append({
            'name': 'fb_spezzato',
            'segments': [
                {'start': store_open, 'end': split_m_end},
                {'start': split_a_start, 'end': store_close}
            ],
            'total_min': 8 * 60,
            'slot': 'split'
        })
    
    # Additional hour variants for flexibility
    for extra_h in [1, 2, 3]:
        # Morning + extra hours
        m_end = mid + extra_h * 60
        if m_end <= store_close and m_end - store_open <= 8 * 60:
            name = f'fb_mattina_+{extra_h}h'
            shifts.append({
                'name': name,
                'segments': [{'start': store_open, 'end': m_end}],
                'total_min': m_end - store_open,
                'slot': 'morning'
            })
        
        # Afternoon - extra hours (start earlier)
        a_start = mid - extra_h * 60
        if a_start >= store_open and store_close - a_start <= 8 * 60:
            name = f'fb_pomeriggio_-{extra_h}h'
            shifts.append({
                'name': name,
                'segments': [{'start': a_start, 'end': store_close}],
                'total_min': store_close - a_start,
                'slot': 'afternoon'
            })
    
    return shifts


def extract_fixed_schedules(people, store_open, store_close):
    """
    Identifies employees with 'partime fisso' in preferences and
    extracts their schedule directly from the CSV (raw data).
    """
    fixed_patterns = []
    fixed_map = {} # i -> {day_idx: segments}
    
    for i, p in enumerate(people):
        prefs = (p.get('preferences', '') or '').lower()
        if 'partime fisso' in prefs:
            day_segs = {}
            raw = p.get('raw', {})
            for d_idx, d_name in enumerate(DAY_NAMES):
                # We try 'Lun' or 'Lun_W1' as keys
                shift_str = raw.get(d_name, '') or raw.get(f"{d_name}_W1", '')
                segs = parse_shift_segments(shift_str)
                day_segs[d_idx] = segs
                
                if segs:
                    total_min = sum(s['end'] - s['start'] for s in segs)
                    slot = classify_slot(segs, store_open, store_close)
                    fixed_patterns.append({
                        'name': f"fixed_{d_name}",
                        'segments': segs,
                        'total_min': total_min,
                        'slot': slot,
                        'count': 100
                    })
            fixed_map[i] = day_segs
            
    return fixed_patterns, fixed_map


def merge_and_deduplicate(db_patterns, extracted, fallback):
    """Merge patterns from 3 sources: DB (highest priority) > CSV > fallback."""
    seen_keys = set()
    merged = []
    
    # 1. DB patterns get highest priority (accumulated knowledge)
    for p in db_patterns:
        key = segments_to_key(p['segments'])
        if key not in seen_keys:
            seen_keys.add(key)
            merged.append(p)
    
    # 2. CSV-extracted patterns (current import)
    for p in extracted:
        key = segments_to_key(p['segments'])
        if key not in seen_keys:
            seen_keys.add(key)
            merged.append(p)
    
    # 3. Fallback patterns (auto-generated for coverage)
    for p in fallback:
        key = segments_to_key(p['segments'])
        if key not in seen_keys:
            seen_keys.add(key)
            merged.append(p)
    
    return merged


def analyze_history(emp_data):
    """Analyze historical shifts to extract preference patterns."""
    morning_count = 0
    afternoon_count = 0
    split_count = 0
    total_shifts = 0
    rest_days = {}
    
    for day in DAY_NAMES:
        shift = emp_data.get(day, '').strip()
        if not shift or shift.lower() in ('riposo', 'chiuso', ''):
            rest_days[day] = 1
            continue
        
        segs = parse_shift_segments(shift)
        if not segs:
            rest_days[day] = 1
            continue
        
        total_shifts += 1
        
        if len(segs) >= 2:
            split_count += 1
        else:
            avg_start = sum(s['start'] for s in segs) / len(segs)
            if avg_start < 13 * 60:
                morning_count += 1
            else:
                afternoon_count += 1
    
    return {
        'morning_ratio': morning_count / max(total_shifts, 1),
        'afternoon_ratio': afternoon_count / max(total_shifts, 1),
        'split_ratio': split_count / max(total_shifts, 1),
        'rest_days': rest_days,
        'total_shifts': total_shifts,
        'prefers_split': split_count > morning_count and split_count > afternoon_count,
    }


def verify_coverage(shift_types, store_open, store_close):
    """
    Verify that the available shift types can, collectively, cover every interval.
    Returns a list of uncovered intervals (should be empty).
    """
    intervals = list(range(store_open, store_close, INTERVAL))
    uncovered = []
    for t_start in intervals:
        t_end = t_start + INTERVAL
        covered = False
        for st in shift_types:
            for seg in st['segments']:
                if seg['start'] < t_end and seg['end'] > t_start:
                    covered = True
                    break
            if covered:
                break
        if not covered:
            uncovered.append((to_hhmm(t_start), to_hhmm(t_end)))
    return uncovered


def solve_schedule(people, settings, db_patterns=None, employee_day_patterns=None):
    """
    Core solving function: GENERATES new shifts using learned patterns.
    Uses patterns from 3 sources (priority order):
      1. Database (accumulated from all past imports)
      2. CSV (current import)
      3. Auto-generated fallbacks (for coverage)
    """
    model = cp_model.CpModel()
    n = len(people)
    num_days = 7
    
    store_open = time_to_min(settings.get('openTime', '09:30'))
    store_close = time_to_min(settings.get('closeTime', '19:30'))
    closed_days_names = settings.get('closedDays', [])
    closed_days = set(DAY_NAMES.index(d) for d in closed_days_names if d in DAY_NAMES)
    
    if db_patterns is None:
        db_patterns = []
    if employee_day_patterns is None:
        employee_day_patterns = {}
    
    # ===== BUILD SHIFT TYPE POOL =====
    # 1. Extract real patterns from current CSV data
    emp_dicts = []
    for p in people:
        d = {}
        if 'raw' in p:
            d = p['raw']
        else:
            d = p.get('emp_data', {})
        emp_dicts.append(d)
    
    extracted = extract_patterns_from_data(emp_dicts, store_open, store_close)
    
    # 2. Generate fallback patterns for complete coverage
    fallback = build_fallback_shifts(store_open, store_close)
    
    # 2.5 Extract part-time fixed schedules from CSV if requested
    fixed_pats, fixed_schedules_map = extract_fixed_schedules(people, store_open, store_close)

    # 3. Merge: DB (accumulated) > CSV (current) > Fallback (generated) > Fixed (PT)
    shift_types = merge_and_deduplicate(db_patterns, extracted, fallback + fixed_pats)
    
    # Filter: only shifts that fit within store hours and <= 8h
    shift_types = [
        st for st in shift_types
        if st['total_min'] <= 8 * 60
        and all(s['start'] >= store_open and s['end'] <= store_close for s in st['segments'])
    ]
    
    # Verify coverage
    uncovered = verify_coverage(shift_types, store_open, store_close)
    if uncovered:
        print(f"WARNING: Uncovered intervals: {uncovered}")
    
    num_shift_types = len(shift_types)
    
    # Debug: print available shift types
    print(f"\n=== Available shift types ({num_shift_types}) ===")
    for idx, st in enumerate(shift_types):
        segs_str = " / ".join(f"{to_hhmm(s['start'])}-{to_hhmm(s['end'])}" for s in st['segments'])
        print(f"  [{idx}] {st['name']:25s} | {segs_str:30s} | {st['total_min']/60:.1f}h | {st['slot']}")
    
    # Time intervals for coverage
    intervals = list(range(store_open, store_close, INTERVAL))
    num_intervals = len(intervals)
    
    # Pre-compute coverage matrix
    shift_covers = []
    for st in shift_types:
        covers = []
        for t_start in intervals:
            t_end = t_start + INTERVAL
            is_covered = any(
                seg['start'] < t_end and seg['end'] > t_start
                for seg in st['segments']
            )
            covers.append(is_covered)
        shift_covers.append(covers)
    
    # ===== DECISION VARIABLES =====
    # assign[i][d][s] = 1 if person i works shift type s on day d
    assign = [[[model.NewBoolVar(f"a_{i}_{d}_{s}")
                for s in range(num_shift_types)]
               for d in range(num_days)]
              for i in range(n)]
    
    # works[i][d] = 1 if person i works on day d
    works = [[model.NewBoolVar(f"w_{i}_{d}") for d in range(num_days)] for i in range(n)]
    for i in range(n):
        for d in range(num_days):
            model.Add(sum(assign[i][d][s] for s in range(num_shift_types)) >= 1).OnlyEnforceIf(works[i][d])
            model.Add(sum(assign[i][d][s] for s in range(num_shift_types)) == 0).OnlyEnforceIf(works[i][d].Not())
    
    # ===== HARD CONSTRAINTS =====
    
    # C1. At most ONE shift per person per day
    for i in range(n):
        for d in range(num_days):
            model.Add(sum(assign[i][d][s] for s in range(num_shift_types)) <= 1)
    
    # C2. Closed days
    for d in closed_days:
        for i in range(n):
            for s in range(num_shift_types):
                model.Add(assign[i][d][s] == 0)
    
    # C3. Exact contract hours
    for i in range(n):
        vacations = (people[i].get('vacation_days', '') or '').lower()
        deduction = 0
        if vacations:
            for d_idx, d_name in enumerate(DAY_NAMES):
                if d_name.lower() in vacations:
                    if d_name.lower() == 'lun':
                        deduction += 5 * 60
                    else:
                        deduction += 7 * 60
        
        if i in fixed_schedules_map:
            # For fixed part-timers, base target is their CSV sum
            base_target = sum(
                sum(s['end'] - s['start'] for s in segs)
                for segs in fixed_schedules_map[i].values()
            )
            target_min = max(0, base_target - deduction)
        else:
            target_min = max(0, people[i]['contract_min'] - deduction)

        total_min = sum(
            shift_types[s]['total_min'] * assign[i][d][s]
            for d in range(num_days) for s in range(num_shift_types)
        )
        model.Add(total_min == target_min)
    
    # C4. Daily max 8h (already filtered shift types, but enforce)
    for i in range(n):
        for d in range(num_days):
            day_min = sum(shift_types[s]['total_min'] * assign[i][d][s] for s in range(num_shift_types))
            model.Add(day_min <= 8 * 60)
    
    # C5. At least 1 rest day
    for i in range(n):
        model.Add(sum(works[i][d] for d in range(num_days)) <= 6)
    
    # C6. FULL COVERAGE: at least 1 person at EVERY time interval on open days
    for d in range(num_days):
        if d in closed_days:
            continue
        for t_idx in range(num_intervals):
            staff_at_t = []
            for i in range(n):
                for s in range(num_shift_types):
                    if shift_covers[s][t_idx]:
                        staff_at_t.append(assign[i][d][s])
            if staff_at_t:
                model.Add(sum(staff_at_t) >= 1)
            else:
                print(f"ERROR: No shift type covers interval {to_hhmm(intervals[t_idx])} on day {DAY_NAMES[d]}")
    
    # C7. Preferences / blocked days / fixed rests
    for i in range(n):
        if i in fixed_schedules_map:
            continue # Skip preferences for fixed part-timers, they follow their CSV schedule
            
        prefs = (people[i].get('preferences', '') or '').lower()
        fixed_rests = (people[i].get('fixed_rests', '') or '').lower()
        
        if prefs:
            for d_idx, d_name in enumerate(DAY_NAMES):
                if f"no {d_name.lower()}" in prefs:
                    for s in range(num_shift_types):
                        model.Add(assign[i][d_idx][s] == 0)
            if "no weekend" in prefs:
                for d_idx in [5, 6]:
                    for s in range(num_shift_types):
                        model.Add(assign[i][d_idx][s] == 0)
                        
        if fixed_rests:
            for d_idx, d_name in enumerate(DAY_NAMES):
                if d_name.lower() in fixed_rests:
                    for s in range(num_shift_types):
                        model.Add(assign[i][d_idx][s] == 0)
                        
        vacations = (people[i].get('vacation_days', '') or '').lower()
        if vacations:
            for d_idx, d_name in enumerate(DAY_NAMES):
                if d_name.lower() in vacations:
                    for s in range(num_shift_types):
                        model.Add(assign[i][d_idx][s] == 0)
                        
    # C8. Mondays: exactly 5 hours, no split shifts
    if 'Lun' in DAY_NAMES:
        lun_idx = DAY_NAMES.index('Lun')
        for i in range(n):
            if i in fixed_schedules_map:
                continue # Skip PT fixed
            for s in range(num_shift_types):
                st = shift_types[s]
                if st['total_min'] != 5 * 60 or st['slot'] == 'split':
                    model.Add(assign[i][lun_idx][s] == 0)

    # C9. Assignment Lock for Fixed Part-timers
    for i, day_map in fixed_schedules_map.items():
        vacations = (people[i].get('vacation_days', '') or '').lower()
        for d_idx, segs in day_map.items():
            d_name = DAY_NAMES[d_idx].lower()
            if not segs or d_name in vacations:
                # Must rest (either CSV was empty or they have Ferie)
                for s in range(num_shift_types):
                    model.Add(assign[i][d_idx][s] == 0)
            else:
                target_key = segments_to_key(segs)
                found = False
                for s in range(num_shift_types):
                    st_key = segments_to_key(shift_types[s]['segments'])
                    if st_key == target_key:
                        model.Add(assign[i][d_idx][s] == 1)
                        found = True
                    else:
                        model.Add(assign[i][d_idx][s] == 0)
                if not found:
                    print(f"CRITICAL: Could not find shift type for fixed PT {people[i]['name']} on day {d_idx}")
    
    # ===== OBJECTIVE: ROTATION + PATTERN PREFERENCE =====
    objective = []
    
    morning_idxs = [s for s, st in enumerate(shift_types) if st['slot'] == 'morning']
    afternoon_idxs = [s for s, st in enumerate(shift_types) if st['slot'] == 'afternoon']
    split_idxs = [s for s, st in enumerate(shift_types) if st['slot'] == 'split']
    
    # Identify DB patterns and their indices (with frequency weights) — global pool
    db_pattern_keys = set(segments_to_key(p['segments']) for p in db_patterns)
    db_pattern_freq = {segments_to_key(p['segments']): p.get('frequency', 1) for p in db_patterns}
    db_idxs = [s for s, st in enumerate(shift_types) if segments_to_key(st['segments']) in db_pattern_keys]

    # Also identify CSV-extracted patterns
    extracted_keys = set(segments_to_key(p['segments']) for p in extracted)
    historical_idxs = [s for s, st in enumerate(shift_types) if segments_to_key(st['segments']) in extracted_keys]

    # Pre-build per-(employee, day) reward maps from employee_day_patterns
    # Structure: emp_day_reward[i][d] = {shift_type_index: reward_value}
    emp_day_reward = [{} for _ in range(n)]
    for i, p in enumerate(people):
        emp_id = p.get('employee_id', '')
        if not emp_id or emp_id not in employee_day_patterns:
            emp_day_reward[i] = None  # will fall back to global DB rewards
            continue
        day_rewards = {}
        for d_idx, d_name in enumerate(DAY_NAMES):
            day_pats = employee_day_patterns[emp_id].get(d_name, [])
            # Build a key -> frequency map for this employee+day
            day_freq_map = {
                segments_to_key(dp['segments']): dp.get('frequency', 1)
                for dp in day_pats
            }
            reward_for_day = {}
            for s_idx, st in enumerate(shift_types):
                key = segments_to_key(st['segments'])
                if key in day_freq_map:
                    freq = min(day_freq_map[key], 20)
                    reward_for_day[s_idx] = -1 * (2 + freq // 3)  # negative = reward
            if reward_for_day:
                day_rewards[d_idx] = reward_for_day
        emp_day_reward[i] = day_rewards if day_rewards else None

    for i in range(n):
        # --- Rotation: balance morning and afternoon ---
        open_days = [d for d in range(num_days) if d not in closed_days]
        morning_days = []
        afternoon_days = []
        for d in open_days:
            m = model.NewBoolVar(f"m_{i}_{d}")
            a = model.NewBoolVar(f"a_{i}_{d}")
            if morning_idxs:
                model.Add(sum(assign[i][d][s] for s in morning_idxs) >= 1).OnlyEnforceIf(m)
                model.Add(sum(assign[i][d][s] for s in morning_idxs) == 0).OnlyEnforceIf(m.Not())
            else:
                model.Add(m == 0)
            if afternoon_idxs:
                model.Add(sum(assign[i][d][s] for s in afternoon_idxs) >= 1).OnlyEnforceIf(a)
                model.Add(sum(assign[i][d][s] for s in afternoon_idxs) == 0).OnlyEnforceIf(a.Not())
            else:
                model.Add(a == 0)
            morning_days.append(m)
            afternoon_days.append(a)

        diff = model.NewIntVar(-7, 7, f"bal_{i}")
        model.Add(diff == sum(morning_days) - sum(afternoon_days))
        abs_diff = model.NewIntVar(0, 7, f"abs_bal_{i}")
        model.AddAbsEquality(abs_diff, diff)
        objective.append(10 * abs_diff)  # Penalize imbalance

        # --- Reward patterns: per-employee-per-day if available, else global DB ---
        per_day_map = emp_day_reward[i]  # None or {d_idx: {s_idx: reward}}
        if per_day_map is not None:
            # Use fine-grained per-day rewards from employee history
            for d in range(num_days):
                day_rewards = per_day_map.get(d, {})
                if day_rewards:
                    for s_idx, reward in day_rewards.items():
                        objective.append(reward * assign[i][d][s_idx])
                else:
                    # No day-specific data for this day: fall back to global DB reward
                    for s in db_idxs:
                        key = segments_to_key(shift_types[s]['segments'])
                        freq = min(db_pattern_freq.get(key, 1), 20)
                        objective.append(-1 * (1 + freq // 4) * assign[i][d][s])
        else:
            # No employee history at all — use global DB rewards
            for d in range(num_days):
                for s in db_idxs:
                    key = segments_to_key(shift_types[s]['segments'])
                    freq = min(db_pattern_freq.get(key, 1), 20)
                    reward = -1 * (2 + freq // 3)
                    objective.append(reward * assign[i][d][s])

        # --- Also reward CSV-extracted patterns (weaker than DB) ---
        for d in range(num_days):
            for s in historical_idxs:
                if s not in db_idxs:  # Don't double-count
                    objective.append(-2 * assign[i][d][s])

        
        # --- Soft: prefers split if history shows that ---
        history = people[i].get('history', {})
        if history.get('prefers_split', False) and split_idxs:
            for d in open_days:
                for s in split_idxs:
                    objective.append(-3 * assign[i][d][s])
        
        # --- Soft: respect historical rest days ---
        rest_days_hist = history.get('rest_days', {})
        for d_idx, d_name in enumerate(DAY_NAMES):
            if rest_days_hist.get(d_name, 0) > 0:
                objective.append(1 * works[i][d_idx])  # Mild penalty
    
    # Random noise for variety between runs
    random.seed()
    for i in range(n):
        for d in range(num_days):
            for s in range(num_shift_types):
                noise = random.randint(-1, 1)
                if noise != 0:
                    objective.append(noise * assign[i][d][s])
    
    model.Minimize(sum(objective))
    
    # ===== SOLVE =====
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 30
    status = solver.Solve(model)
    
    results = []
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for i, p in enumerate(people):
            emp_shifts = {}
            total_worked_min = 0
            for d in range(num_days):
                day_name = DAY_NAMES[d]
                if d in closed_days:
                    emp_shifts[day_name] = "CHIUSO"
                    continue
                
                assigned = None
                for s in range(num_shift_types):
                    if solver.Value(assign[i][d][s]) == 1:
                        assigned = shift_types[s]
                        break
                
                if assigned is None:
                    emp_shifts[day_name] = ""
                else:
                    parts = [f"{to_hhmm(seg['start'])} - {to_hhmm(seg['end'])}" for seg in assigned['segments']]
                    emp_shifts[day_name] = " / ".join(parts)
                    total_worked_min += assigned['total_min']
            
            results.append({
                "ID": p.get('employee_id', ''),
                "Nome": p['name'],
                "shifts": emp_shifts,
                "assignedHours": round(total_worked_min / 60, 2),
                "Ore Contratto": p.get('contract_hours', p['contract_min'] / 60)
            })
    
    return results, solver.StatusName(status)


def read_input(path):
    with open(path, 'r', newline='', encoding='utf-8') as f:
        sample = f.read(1024)
        f.seek(0)
        dialect = csv.Sniffer().sniff(sample, delimiters=';,')
        rdr = csv.reader(f, dialect)
        rows = list(rdr)
    
    header = rows[0]
    people = []
    for r in rows[1:]:
        if not r or len(r) < 2:
            continue
        name = r[0]
        try:
            contract_hours = float(r[1].replace(',', '.') or '0')
        except:
            contract_hours = 0
        
        emp = {'Nome': name, 'Ore Contratto': str(contract_hours)}
        for idx, col in enumerate(header[2:], start=2):
            if idx < len(r):
                emp[col] = r[idx]
        
        history = analyze_history(emp)
        
        people.append({
            'name': name,
            'contract_min': int(contract_hours * 60),
            'contract_hours': contract_hours,
            'preferences': emp.get('Esigenze/Preferenze', ''),
            'fixed_rests': str(emp.get('Riposo Fisso', '')).strip(),
            'vacation_days': str(emp.get('Ferie', '')).strip(),
            'history': history,
            'raw': emp,  # Keep original data for pattern extraction
        })
    return header, people


def main():
    input_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join('..', 'Turni-Test.csv')
    if not os.path.exists(input_path):
        input_path = 'Turni-Test.csv'
    
    header, people = read_input(input_path)
    settings = {'openTime': '09:30', 'closeTime': '19:30', 'closedDays': []}
    
    results, status_name = solve_schedule(people, settings)
    
    if results:
        header_out = 'Nome;Lun;Mar;Mer;Gio;Ven;Sab;Dom;Totale Ore'
        lines = [header_out]
        for res in results:
            shifts = res['shifts']
            row = [res['Nome']] + [shifts[d] for d in DAY_NAMES] + [f"{res['assignedHours']:.2f}"]
            lines.append(';'.join(row))
        
        os.makedirs('outputs', exist_ok=True)
        with open(os.path.join('outputs', 'cp_sat_schedule.csv'), 'w', newline='', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        print(f"\nSuccess! status: {status_name}")
        print('Wrote outputs/cp_sat_schedule.csv')
        
        # Coverage verification
        print("\n--- Schedule Summary ---")
        for res in results:
            print(f"\n{res['Nome']} ({res['assignedHours']:.1f}h / {res.get('Ore Contratto', '?')}h):")
            for d in DAY_NAMES:
                print(f"  {d}: {res['shifts'][d]}")
    else:
        print(f"No solution found. status: {status_name}")


if __name__ == '__main__':
    main()
