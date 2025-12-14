import pandas as pd
import random
import math
import json
import re
from datetime import timedelta, datetime
from typing import List, Dict, Any, Set, Tuple
from backend.models.schema import ScheduleConfig, StudentData, ScheduleResult

class HillClimbingScheduler:
    def __init__(self, config: ScheduleConfig, students: List[StudentData]):
        self.config = config
        self.students = students
        # Pre-process subjects: Name -> {duration, student_ids}
        self.all_subjects = self._preprocess_subjects()
        self.dates = self._generate_dates()
        
        # Auto-calculate rooms if not provided
        if not self.config.rooms:
            self._auto_generate_rooms()

    def _auto_generate_rooms(self):
        # Logic:
        # If max_students_per_room is NOT set (None or 0), default to 50 (per user request).
        if not self.config.max_students_per_room:
            self.config.max_students_per_room = 50
            
        # Calculate demand
        total_minutes_needed = 0
        max_s = self.config.max_students_per_room
        max_concurrent_needed = 1
        
        for sub_name, info in self.all_subjects.items():
            n_students = len(info["student_ids"])
            # Number of "batches" or "slots" needed for this subject
            n_batches = math.ceil(n_students / max_s)
            total_minutes_needed += n_batches * info["duration"]
            
            # Track peak concurrent rooms needed (assuming subject scheduled in one slot)
            if n_batches > max_concurrent_needed:
                max_concurrent_needed = n_batches
            
        # Calculate capacity per room
        # Days * Shifts * (End - Start)
        minutes_per_room = 0
        for date in self.dates:
            for shift in self.config.shifts:
                times = self.config.shift_times.get(shift)
                if times:
                    start = datetime.strptime(times["start"], "%H:%M")
                    end = datetime.strptime(times["end"], "%H:%M")
                    duration = (end - start).total_seconds() / 60
                    minutes_per_room += duration
        
        if minutes_per_room == 0:
            estimated_rooms = 1
        else:
            # Add 20% buffer for fragmentation and breaks
            estimated_rooms = math.ceil((total_minutes_needed * 1.2) / minutes_per_room)
            
        # Ensure we have at least enough rooms for the largest class split
        estimated_rooms = max(1, estimated_rooms, max_concurrent_needed)
        print(f"Auto-generating {estimated_rooms} rooms (Peak needed: {max_concurrent_needed})...")
        
        self.config.rooms = [{"name": f"Phòng {i+1}"} for i in range(estimated_rooms)]

    def _preprocess_subjects(self) -> Dict[str, Any]:
        subjects = {}
        for s in self.students:
            for sub_name, duration in s.subjects.items():
                if sub_name not in subjects:
                    subjects[sub_name] = {
                        "duration": duration,
                        "student_ids": set()
                    }
                subjects[sub_name]["student_ids"].add(s.student_id)
                
                # Check duration consistency
                if subjects[sub_name]["duration"] != duration:
                    # In a real app, we might raise an error or warn. 
                    # For now, keep the first duration found or max.
                    pass 
        return subjects

    def _generate_dates(self) -> List[str]:
        dates = []
        current_date = self.config.start_date
        while current_date <= self.config.end_date:
            # config.off_days is list of ints (0=Mon, 6=Sun)
            if current_date.weekday() not in self.config.off_days:
                dates.append(current_date.strftime("%Y-%m-%d"))
            current_date += timedelta(days=1)
        return dates

    def schedule(self) -> Tuple[List[ScheduleResult], List[str]]:
        # Hill Climbing with Random Restart
        MAX_RESTARTS = 5
        MAX_ITERATIONS = 1000
        
        best_solution = []
        best_cost = float('inf')
        best_warnings = []
        
        print(f"Starting Hill Climbing with {MAX_RESTARTS} restarts...")
        
        for restart in range(MAX_RESTARTS):
            try:
                current_solution, current_warnings = self._generate_initial_solution()
            except Exception as e:
                print(f"Error generating initial solution: {e}")
                import traceback
                traceback.print_exc()
                continue
                
            current_cost = self._calculate_cost(current_solution)
            
            if not best_solution:
                best_solution = current_solution
                best_cost = current_cost
                best_warnings = current_warnings
            
            # Hill Climbing
            for i in range(MAX_ITERATIONS):
                neighbor = self._get_neighbor(current_solution)
                neighbor_cost = self._calculate_cost(neighbor)
                
                if neighbor_cost < current_cost:
                    current_solution = neighbor
                    current_cost = neighbor_cost
            
            print(f"Restart {restart+1}: Cost = {current_cost}")
            
            if current_cost < best_cost:
                best_cost = current_cost
                best_solution = current_solution
                best_warnings = current_warnings
                
            if best_cost == 0:
                break
                
        return self._format_results(best_solution), best_warnings

    def _generate_initial_solution(self) -> Tuple[List[Dict[str, Any]], List[str]]:
        # Greedy construction similar to JS logic
        schedule = []
        warnings = []
        
        # Prepare subject list and shuffle
        subject_list = []
        for name, info in self.all_subjects.items():
            subject_list.append({
                "name": name,
                "duration": info["duration"],
                "studentIds": list(info["student_ids"])
            })
        random.shuffle(subject_list)
        
        # Track room availability: room -> date -> session -> available_time_str
        room_availability = {}
        sessions = []
        if "Morning" in self.config.shifts: sessions.append("Morning")
        if "Afternoon" in self.config.shifts: sessions.append("Afternoon")
        
        for room in self.config.rooms:
            if isinstance(room, dict):
                room_name = room.get('name', str(room))
            else:
                room_name = str(room)
                
            room_availability[room_name] = {}
            for date in self.dates:
                room_availability[room_name][date] = {}
                for session in sessions:
                    times = self.config.shift_times.get(session)
                    if times:
                        room_availability[room_name][date][session] = times["start"]

        # Track date load to balance days
        date_load = {d: 0 for d in self.dates}
        
        for subject in subject_list:
            placed = False
            # Sort dates by load (least loaded first)
            sorted_dates = sorted(self.dates, key=lambda d: date_load[d])
            
            for date in sorted_dates:
                for session in sessions:
                    # Find available rooms for this session
                    session_end_str = self.config.shift_times[session]["end"]
                    available_rooms = []
                    
                    for room in self.config.rooms:
                        # Room is a dict from Pydantic model (List[Dict[str, str]])
                        if isinstance(room, dict):
                            room_name = room.get('name', str(room))
                        else:
                            room_name = str(room)
                            
                        next_avail_str = room_availability[room_name][date].get(session)
                        
                        if not next_avail_str: continue
                        
                        # Calculate times
                        start_dt = datetime.strptime(f"{date} {next_avail_str}", "%Y-%m-%d %H:%M")
                        end_dt = start_dt + timedelta(minutes=subject["duration"])
                        session_end_dt = datetime.strptime(f"{date} {session_end_str}", "%Y-%m-%d %H:%M")
                        
                        if end_dt <= session_end_dt:
                            available_rooms.append({
                                "room": room_name,
                                "start_str": next_avail_str,
                                "end_str": end_dt.strftime("%H:%M"),
                                "end_dt": end_dt
                            })
                            
                    if not available_rooms:
                        continue
                        
                    # Split students into groups if needed
                    n_students = len(subject["studentIds"])
                    max_rooms = len(available_rooms)
                    groups = []
                    
                    # Logic to split students (simplified from JS)
                    # If min/max constraints exist, try to respect them
                    min_s = self.config.min_students_per_room
                    max_s = self.config.max_students_per_room
                    
                    target_rooms = max_rooms
                    if min_s and max_s and min_s <= max_s:
                        if n_students < min_s:
                            target_rooms = 1
                        else:
                            # Try to find best number of rooms
                            min_r = math.ceil(n_students / max_s)
                            max_r = math.floor(n_students / min_s)
                            
                            # Debug
                            # print(f"DEBUG: Sub={subject['name']} N={n_students} MinS={min_s} MaxS={max_s} MinR={min_r} MaxR={max_r} Avail={max_rooms}")

                            best_r = -1
                            # Try to respect both min and max
                            for r in range(min(max_r, max_rooms), min_r - 1, -1):
                                if r > 0:
                                    best_r = r
                                    break
                            
                            if best_r != -1:
                                target_rooms = best_r
                            else:
                                # Fallback: If we can't satisfy min_students, just ensure we satisfy max_students
                                # i.e. use at least min_r rooms.
                                if min_r <= max_rooms:
                                    target_rooms = min_r # Use minimum rooms needed to fit max_s
                                else:
                                    # Not enough rooms to fit students even at max capacity!
                                    # print(f"DEBUG: Not enough rooms! Need {min_r}, have {max_rooms}")
                                    continue 
                    elif max_s:
                        # Only max_students is set (or min_s is invalid)
                        # We must split into enough groups to satisfy max_s
                        min_groups = math.ceil(n_students / max_s)
                        
                        if min_groups > max_rooms:
                            # Not enough rooms in this slot to satisfy max_students constraint
                            continue
                            
                        # If we have many rooms, we can spread out (use max_rooms).
                        # But we must at least use min_groups.
                        target_rooms = max(max_rooms, min_groups)
                        # Correction: target_rooms cannot exceed max_rooms!
                        target_rooms = max_rooms
                    
                    # Split students
                    groups = self._split_into_groups(subject["studentIds"], target_rooms)
                    
                    # Check conflicts for all groups
                    any_conflict = False
                    # (Skipping detailed conflict check during initial generation for speed, 
                    # relying on cost function to fix later, OR implement simple check)
                    # Let's implement simple check
                    
                    # Assign groups
                    for i, grp in enumerate(groups):
                        if not grp: continue
                        avail = available_rooms[i]
                        
                        # Add to schedule
                        schedule.append({
                            "date": date,
                            "session": session,
                            "startTime": avail["start_str"],
                            "endTime": avail["end_str"],
                            "room": avail["room"],
                            "subject": subject["name"],
                            "duration": subject["duration"],
                            "studentIds": grp
                        })
                        
                        # Update room availability
                        next_start_dt = avail["end_dt"] + timedelta(minutes=self.config.break_time)
                        room_availability[avail["room"]][date][session] = next_start_dt.strftime("%H:%M")
                        
                        # Update load
                        date_load[date] += len(grp)
                        
                    placed = True
                    break
                if placed: break
            
            if not placed:
                msg = f"Không thể xếp lịch cho môn: {subject['name']} (Số lượng: {len(subject['studentIds'])})"
                print(f"Warning: {msg}")
                warnings.append(msg)
                
        return schedule, warnings

    def _split_into_groups(self, items: List[Any], n_groups: int) -> List[List[Any]]:
        if n_groups <= 0: return []
        base = len(items) // n_groups
        rem = len(items) % n_groups
        groups = []
        idx = 0
        for i in range(n_groups):
            size = base + (1 if rem > 0 else 0)
            if rem > 0: rem -= 1
            groups.append(items[idx : idx + size])
            idx += size
        return groups

    def _get_neighbor(self, solution: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # Swap move
        neighbor = [s.copy() for s in solution]
        if len(neighbor) < 2:
            return neighbor
            
        idx1 = random.randint(0, len(neighbor) - 1)
        idx2 = random.randint(0, len(neighbor) - 1)
        while idx1 == idx2:
            idx2 = random.randint(0, len(neighbor) - 1)
            
        # Swap content (subject, duration, students) but keep time/room slot info
        # Actually, if we swap content, we must ensure duration fits? 
        # JS logic swaps content and re-calculates endTime.
        
        temp_content = {
            "subject": neighbor[idx1]["subject"],
            "duration": neighbor[idx1]["duration"],
            "studentIds": neighbor[idx1]["studentIds"]
        }
        
        neighbor[idx1]["subject"] = neighbor[idx2]["subject"]
        neighbor[idx1]["duration"] = neighbor[idx2]["duration"]
        neighbor[idx1]["studentIds"] = neighbor[idx2]["studentIds"]
        
        neighbor[idx2]["subject"] = temp_content["subject"]
        neighbor[idx2]["duration"] = temp_content["duration"]
        neighbor[idx2]["studentIds"] = temp_content["studentIds"]
        
        # Recalculate End Times
        for idx in [idx1, idx2]:
            entry = neighbor[idx]
            start_dt = datetime.strptime(f"{entry['date']} {entry['startTime']}", "%Y-%m-%d %H:%M")
            end_dt = start_dt + timedelta(minutes=entry["duration"])
            entry["endTime"] = end_dt.strftime("%H:%M")
            
        return neighbor

    def _calculate_cost(self, solution: List[Dict[str, Any]]) -> float:
        cost = 0.0
        
        # 1. Room Constraints (Min/Max) & Balance
        room_occupancy = {}
        for entry in solution:
            n_students = len(entry["studentIds"])
            if self.config.min_students_per_room and n_students < self.config.min_students_per_room:
                cost += 500
            if self.config.max_students_per_room and n_students > self.config.max_students_per_room:
                cost += 1000
                
            if entry["room"] not in room_occupancy:
                room_occupancy[entry["room"]] = []
            room_occupancy[entry["room"]].append(n_students)
            
        # Variance (Soft)
        all_counts = [c for counts in room_occupancy.values() for c in counts]
        if len(all_counts) > 1:
            mean = sum(all_counts) / len(all_counts)
            variance = sum((x - mean) ** 2 for x in all_counts) / len(all_counts)
            cost += math.sqrt(variance)

        # 2. Student Conflicts & Density & Room Overlaps
        student_schedule = {} # student_id -> list of (start_dt, end_dt)
        student_exams_per_day = {} # student_id -> date -> count
        room_schedule = {} # room -> date -> list of (start_dt, end_dt)

        for entry in solution:
            start_dt = datetime.strptime(f"{entry['date']} {entry['startTime']}", "%Y-%m-%d %H:%M")
            end_dt = datetime.strptime(f"{entry['date']} {entry['endTime']}", "%Y-%m-%d %H:%M")
            
            # Check Room Overlaps
            r_key = entry["room"]
            d_key = entry["date"]
            if r_key not in room_schedule: room_schedule[r_key] = {}
            if d_key not in room_schedule[r_key]: room_schedule[r_key][d_key] = []
            
            # We will sort and check overlaps later or check incrementally
            # Incremental check is O(N) per room if sorted, but here we iterate.
            # Let's just add to list and check later for efficiency? 
            # Actually, N is small per room/day.
            for exist_start, exist_end in room_schedule[r_key][d_key]:
                if start_dt < exist_end and end_dt > exist_start:
                    cost += 5000 # HUGE penalty for room overlap
            room_schedule[r_key][d_key].append((start_dt, end_dt))

            for s_id in entry["studentIds"]:
                if s_id not in student_schedule:
                    student_schedule[s_id] = []
                    student_exams_per_day[s_id] = {}
                
                # Check conflict
                for exist_start, exist_end in student_schedule[s_id]:
                    if start_dt < exist_end and end_dt > exist_start:
                        cost += 2000 # Hard conflict (increased weight)
                        
                student_schedule[s_id].append((start_dt, end_dt))
                
                # Count per day
                d_str = entry["date"]
                student_exams_per_day[s_id][d_str] = student_exams_per_day[s_id].get(d_str, 0) + 1

        # Density & Gaps
        MAX_EXAMS = 2
        for s_id, days in student_exams_per_day.items():
            for d_str, count in days.items():
                if count > MAX_EXAMS:
                    cost += 50 * (2 ** (count - MAX_EXAMS)) # Increased weight
                
                if count > 1:
                    # Check gaps
                    exams_today = []
                    for s, e in student_schedule[s_id]:
                        if s.strftime("%Y-%m-%d") == d_str:
                            exams_today.append((s, e))
                    exams_today.sort()
                    
                    # Gap between last start and first end (simplified from JS logic)
                    # JS: lastExamStart - firstExamEnd
                    first_end = exams_today[0][1]
                    last_start = exams_today[-1][0]
                    gap_minutes = (last_start - first_end).total_seconds() / 60
                    
                    if gap_minutes > 120:
                        cost += (gap_minutes / 60) * 1.0 # Increased weight

        return cost

    def _format_results(self, solution: List[Dict[str, Any]]) -> List[ScheduleResult]:
        results = []
        # Need to map student ID back to Name
        student_map = {s.student_id: s.name for s in self.students}
        
        for entry in solution:
            for s_id in entry["studentIds"]:
                results.append(ScheduleResult(
                    student_id=s_id,
                    student_name=student_map.get(s_id, "Unknown"),
                    subject=entry["subject"],
                    exam_date=datetime.strptime(entry["date"], "%Y-%m-%d").date(),
                    shift=entry["session"],
                    start_time=entry["startTime"],
                    end_time=entry["endTime"],
                    room=entry["room"]
                ))
        return results

def parse_json(file_content: bytes) -> List[StudentData]:
    try:
        data = json.loads(file_content.decode('utf-8'))
        students = []
        # Expected format: List of dicts or Dict with 'students' key?
        # JS says: { "student_id": 1, "name": "SV1", "subjects": { "Toán": 60 } }
        # If data is list
        if isinstance(data, list):
            raw_list = data
        elif isinstance(data, dict) and "students" in data:
            raw_list = data["students"]
        else:
            raw_list = []
            
        for item in raw_list:
            # Handle subjects being a list or dict
            raw_subjects = item.get("subjects", {})
            subjects_dict = {}
            
            if isinstance(raw_subjects, dict):
                subjects_dict = raw_subjects
            elif isinstance(raw_subjects, list):
                # Assume list of objects with name/duration keys
                # e.g. [{"name": "Math", "duration": 60}, ...]
                for sub in raw_subjects:
                    # Try various common keys
                    name = sub.get("name") or sub.get("subject") or sub.get("subject_name")
                    duration = sub.get("duration") or sub.get("time") or sub.get("minutes")
                    if name and duration:
                        subjects_dict[name] = int(duration)
            
            s = StudentData(
                student_id=str(item.get("student_id", "")),
                name=item.get("name", ""),
                subjects=subjects_dict
            )
            students.append(s)
        return students
    except Exception as e:
        print(f"JSON Parse Error: {e}")
        return []

def parse_excel(file_content: bytes) -> List[StudentData]:
    try:
        df = pd.read_excel(file_content)
    except:
        return []

    students = []
    # Logic to detect format
    # Format 2: Header has "Subject (Duration)"
    is_format_2 = False
    subject_map = {} # col_name -> {name, duration}
    
    for col in df.columns[2:]: # Skip ID, Name
        col_str = str(col)
        match = re.match(r"(.*)\((\d+)\)", col_str)
        if match:
            is_format_2 = True
            subject_map[col] = {
                "name": match.group(1).strip(),
                "duration": int(match.group(2))
            }
        else:
            # Format 1 or unknown
            subject_map[col] = {
                "name": col_str.strip(),
                "duration": 60 # Default or read from cell
            }
            
    for _, row in df.iterrows():
        s_id = str(row.iloc[0])
        s_name = str(row.iloc[1])
        subs = {}
        
        for col, info in subject_map.items():
            val = row[col]
            if pd.notna(val) and str(val).strip() != "":
                if is_format_2:
                    # Value is checkmark or anything
                    subs[info["name"]] = info["duration"]
                else:
                    # Format 1: Value is duration
                    try:
                        dur = int(val)
                        if dur > 0:
                            subs[info["name"]] = dur
                    except:
                        pass
                        
        students.append(StudentData(student_id=s_id, name=s_name, subjects=subs))
        
    return students
