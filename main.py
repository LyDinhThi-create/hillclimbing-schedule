# cách chạy:
# 1. mở terminal
# 2. nhập: streamlit run main.py

import streamlit as st
import pandas as pd
import random
import copy
from datetime import datetime, timedelta, time
import io
import re

# ==============================================================================
# 1. CẤU HÌNH & GIAO DIỆN (UI/CSS)
# ==============================================================================
st.set_page_config(
    page_title="Tạo Lịch Thi Trực Tuyến",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS để giống theme màu hồng của web gốc
st.markdown("""
    <style>
    .main {
        background-color: #fffafb;
    }
    h1, h2, h3 {
        color: #db2777 !important; /* Pink-600 */
    }
    .stButton>button {
        background-color: #db2777;
        color: white;
        border-radius: 8px;
        height: 3em;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #be185d;
        color: white;
    }
    .stDownloadButton>button {
        background-color: #16a34a; /* Green-600 */
        color: white;
    }
    div[data-testid="stExpander"] details summary p {
        font-weight: bold;
        color: #db2777;
    }
    </style>
""", unsafe_allow_html=True)

# Header
col_logo, col_title = st.columns([1, 6])
with col_logo:
    st.markdown("### 📅") # Placeholder cho logo
with col_title:
    st.title("Xếp Lịch Thi Thông Minh")

st.markdown("---")

# ==============================================================================
# 1.1 HƯỚNG DẪN SỬ DỤNG
# ==============================================================================
with st.expander("📖 Hướng Dẫn Sử Dụng Chi Tiết (Nhấn để xem)", expanded=False):
    st.markdown("""
    ### 1️⃣ Chuẩn bị dữ liệu đầu vào
    Bạn cần chuẩn bị file Excel (`.xlsx`) theo một trong hai định dạng sau:
    
    * **Dạng 1 (Cơ bản):** Header là tên môn, ô bên dưới chứa thời lượng (phút). Nếu học sinh không thi môn nào thì để trống ô đó.
        * *Ví dụ:* Cột `Toán`, ô chứa số `90`.
    * **Dạng 2 (Khuyên dùng):** Header chứa Tên môn và Thời lượng dạng `Môn(phút)`. Ô bên dưới đánh dấu `x` hoặc `✓` nếu thi.
        * *Ví dụ:* Cột `Toán(90)`, ô chứa chữ `x`.
    
    **Lưu ý:**
    * Cột đầu tiên phải là ID/Mã học sinh.
    * Cột thứ hai phải là Tên học sinh.
    * Thời lượng của cùng một môn phải giống nhau cho tất cả học sinh.

    ### 2️⃣ Thiết lập cấu hình (Sidebar bên trái)
    * **Thời gian:** Chọn ngày bắt đầu/kết thúc, giờ thi sáng/chiều và thời gian nghỉ giữa các ca.
    * **Ngày nghỉ:** Chọn các ngày không tổ chức thi (mặc định T7, CN).
    * **Phòng thi:** Nhập số lượng phòng và tên phòng.
    * **Ràng buộc:** Tùy chọn số lượng học sinh tối thiểu/tối đa trong một phòng (Min/Max) để cân bằng.

    ### 3️⃣ Tạo lịch và Xuất file
    * Tải file Excel lên ở mục bên dưới.
    * Nhấn nút **"Tạo Lịch Thi"**.
    * Sau khi lịch được tạo, bảng chi tiết sẽ hiện ra. Bạn có thể nhấn nút **"Xuất file Excel Kết Quả"** để tải về.
    """)
    
    st.info("💡 Mẹo: Nếu không tạo được lịch, hãy thử tăng số phòng, nới lỏng khoảng thời gian thi hoặc kiểm tra lại file dữ liệu xem có môn nào thời lượng không đồng nhất không.")

# ==============================================================================
# 2. LOGIC XỬ LÝ DỮ LIỆU (PARSING EXCEL)
# ==============================================================================
def parse_excel_data(df):
    """
    Chuyển đổi DataFrame từ Excel thành danh sách học sinh theo logic JS gốc.
    Hỗ trợ cả 2 định dạng:
    1. Header tên môn, ô chứa thời lượng.
    2. Header 'Môn(Thời lượng)', ô chứa dấu 'x' hoặc 'v'.
    """
    students = []
    headers = df.columns.tolist()
    
    # Kiểm tra định dạng 2: Header có dạng "Toán(60)"
    subjects_info = []
    is_format_2 = False
    
    for h in headers[2:]: # Bỏ qua ID và Name
        match = re.match(r"(.*)\((\d+)\)", str(h))
        if match:
            subjects_info.append({"name": match.group(1).strip(), "duration": int(match.group(2))})
            is_format_2 = True
        else:
            subjects_info.append(None)
    
    # Duyệt qua từng dòng
    for index, row in df.iterrows():
        student_id = row[headers[0]]
        student_name = row[headers[1]]
        
        if pd.isna(student_id) or pd.isna(student_name):
            continue
            
        student = {
            "student_id": student_id,
            "name": student_name,
            "subjects": {}
        }
        
        if is_format_2:
            # Định dạng 2: Check header lấy thời lượng, check ô lấy tích
            valid_headers = [h for h in headers[2:] if re.match(r".*\(\d+\)", str(h))]
            for i, h in enumerate(valid_headers):
                cell_value = row[h]
                # Lấy info từ subjects_info (lọc bỏ None)
                info = [x for x in subjects_info if x is not None][i]
                
                if pd.notna(cell_value) and str(cell_value).strip() != "":
                    student["subjects"][info["name"]] = info["duration"]
        else:
            # Định dạng 1: Header là tên môn, Cell là thời lượng
            for col in headers[2:]:
                cell_value = row[col]
                try:
                    duration = int(cell_value)
                    if duration > 0:
                        student["subjects"][str(col).strip()] = duration
                except:
                    continue
                    
        students.append(student)
        
    return students

# ==============================================================================
# 3. THUẬT TOÁN XẾP LỊCH (CORE LOGIC)
# ==============================================================================

def split_into_groups(arr, groups):
    """Chia mảng thành n nhóm cân bằng nhất có thể"""
    n = len(arr)
    result = [[] for _ in range(groups)]
    if groups <= 0: return result
    base = n // groups
    rem = n % groups
    idx = 0
    for i in range(groups):
        size = base + (1 if rem > 0 else 0)
        if rem > 0: rem -= 1
        result[i] = arr[idx : idx + size]
        idx += size
    return result

def generate_mock_schedule(students, config):
    """Tạo một lịch ngẫu nhiên ban đầu (Random Initialization)"""
    
    # 1. Tổng hợp môn thi
    all_subjects = {}
    for student in students:
        for subj_name, duration in student["subjects"].items():
            if subj_name not in all_subjects:
                all_subjects[subj_name] = {"duration": duration, "students": set()}
            # Kiểm tra ràng buộc thời lượng
            if all_subjects[subj_name]["duration"] != duration:
                raise ValueError(f"Lỗi: Môn '{subj_name}' có thời lượng không đồng nhất.")
            all_subjects[subj_name]["students"].add(student["student_id"])

    # Danh sách môn để xếp
    subject_list = []
    for name, info in all_subjects.items():
        subject_list.append({
            "name": name,
            "duration": info["duration"],
            "studentIds": list(info["students"])
        })
    
    # Xáo trộn ngẫu nhiên thứ tự môn (Cốt lõi của Random Restart)
    random.shuffle(subject_list)

    aggregated_schedule = []
    student_schedules = {s["student_id"]: [] for s in students}
    
    # 2. Xử lý ngày tháng
    start_date = config['start_date']
    end_date = config['end_date']
    dates = []
    current_d = start_date
    while current_d <= end_date:
        # Bỏ qua ngày nghỉ (config['rest_days'] là list các date object hoặc string yyyy-mm-dd)
        if str(current_d) not in [str(d) for d in config['rest_days']]:
            dates.append(current_d)
        current_d += timedelta(days=1)
    
    if not dates:
        raise ValueError("Không có ngày thi khả dụng.")

    date_load = {d: 0 for d in dates} # Để cân bằng tải giữa các ngày
    
    # Khởi tạo room availability
    room_availability = {}
    sessions = []
    if config['session_mode'] in ['morning', 'both']: sessions.append('Sáng')
    if config['session_mode'] in ['afternoon', 'both']: sessions.append('Chiều')

    for room in config['room_names']:
        room_availability[room] = {}
        for d in dates:
            room_availability[room][d] = {}
            for sess in sessions:
                t_str = config['morning_start'] if sess == 'Sáng' else config['afternoon_start']
                room_availability[room][d][sess] = datetime.combine(d, t_str)

    # 3. Xếp từng môn
    for subject in subject_list:
        placed = False
        # Sắp xếp ngày theo tải (load) tăng dần để cân bằng
        sorted_dates = sorted(dates, key=lambda x: date_load[x])
        
        for date in sorted_dates:
            for session in sessions:
                session_end_time = datetime.combine(date, config['morning_end'] if session == 'Sáng' else config['afternoon_end'])
                
                # Tìm các phòng còn trống cho môn này
                available_rooms = []
                for room in config['room_names']:
                    start_time = room_availability[room][date][session]
                    end_time = start_time + timedelta(minutes=subject['duration'])
                    
                    if end_time <= session_end_time:
                        available_rooms.append({
                            "room": room,
                            "startTime": start_time,
                            "endTime": end_time
                        })
                
                if not available_rooms:
                    continue

                # Chia sinh viên vào các phòng
                n_students = len(subject['studentIds'])
                max_rooms = len(available_rooms)
                groups = []
                
                # Logic chia nhóm (Min/Max constraints)
                if config['min_students'] and config['max_students'] and config['min_students'] <= config['max_students']:
                    min_s = config['min_students']
                    max_s = config['max_students']
                    min_r = (n_students + max_s - 1) // max_s
                    max_r = n_students // min_s
                    
                    best_r = -1
                    for r in range(min(max_r, max_rooms), min_r - 1, -1):
                        if r > 0:
                            best_r = r
                            break
                    
                    if best_r != -1:
                        groups = split_into_groups(subject['studentIds'], best_r)
                    else:
                        continue # Không thỏa mãn min/max
                else:
                    groups = split_into_groups(subject['studentIds'], max_rooms)

                # Kiểm tra xung đột thời gian của sinh viên
                any_conflict = False
                # (Logic đơn giản hóa: kiểm tra sơ bộ)
                # Trong Python, kiểm tra kỹ hơn lúc gán:
                
                temp_assignments = []
                
                for idx, grp in enumerate(groups):
                    if not grp: continue
                    room_info = available_rooms[idx]
                    
                    # Check conflict từng sv
                    grp_conflict = False
                    for sid in grp:
                        for s_sched in student_schedules[sid]:
                            # s_sched: {start, end}
                            if not (room_info['endTime'] <= s_sched['start'] or room_info['startTime'] >= s_sched['end']):
                                grp_conflict = True
                                break
                        if grp_conflict: break
                    
                    if grp_conflict:
                        any_conflict = True
                        break
                    
                    temp_assignments.append({
                        "room_info": room_info,
                        "students": grp
                    })

                if any_conflict:
                    continue # Thử session/date khác
                
                # Nếu OK, ghi vào lịch
                for assign in temp_assignments:
                    room = assign['room_info']['room']
                    start_t = assign['room_info']['startTime']
                    end_t = assign['room_info']['endTime']
                    grp = assign['students']
                    
                    aggregated_schedule.append({
                        "date": date,
                        "session": session,
                        "startTime": start_t, # datetime object
                        "endTime": end_t,     # datetime object
                        "room": room,
                        "subject": subject['name'],
                        "duration": subject['duration'],
                        "studentIds": grp
                    })
                    
                    # Update student schedules
                    for sid in grp:
                        student_schedules[sid].append({"start": start_t, "end": end_t})
                    
                    # Update room availability (+ break time)
                    next_start = end_t + timedelta(minutes=config['break_minutes'])
                    room_availability[room][date][session] = next_start
                    
                    # Update date load
                    date_load[date] += len(grp)
                
                placed = True
                break # Break session loop
            if placed: break # Break date loop
            
        if not placed:
            print(f"Cảnh báo: Không thể xếp lịch cho môn {subject['name']}")

    return aggregated_schedule

def calculate_cost(schedule, students, config):
    """Hàm mục tiêu: Tính điểm phạt cho lịch thi (Càng thấp càng tốt)"""
    cost = 0
    MAX_EXAMS_PER_DAY = 2
    
    # 1. Phạt cân bằng phòng & sĩ số (Min/Max)
    room_occupancy = {}
    for entry in schedule:
        count = len(entry['studentIds'])
        if config['min_students'] and count < config['min_students']: cost += 500
        if config['max_students'] and count > config['max_students']: cost += 1000
        
        if entry['room'] not in room_occupancy: room_occupancy[entry['room']] = []
        room_occupancy[entry['room']].append(count)
        
    # Tính phương sai sĩ số phòng (để cân bằng)
    all_counts = [c for r in room_occupancy.values() for c in r]
    if len(all_counts) > 1:
        mean = sum(all_counts) / len(all_counts)
        variance = sum((x - mean) ** 2 for x in all_counts) / len(all_counts)
        cost += (variance ** 0.5)

    # 2. Phạt xung đột & mật độ thi
    student_timeline = {} # sid -> {date -> [times]}
    
    for entry in schedule:
        d = entry['date']
        for sid in entry['studentIds']:
            if sid not in student_timeline: student_timeline[sid] = {}
            if d not in student_timeline[sid]: student_timeline[sid][d] = []
            
            # Check trùng giờ (đã xử lý ở bước tạo, nhưng check lại cho chắc)
            # Ở đây chỉ check mật độ
            student_timeline[sid][d].append((entry['startTime'], entry['endTime']))

    for sid, dates_data in student_timeline.items():
        for d, times in dates_data.items():
            # Phạt nếu > 2 môn/ngày
            if len(times) > MAX_EXAMS_PER_DAY:
                cost += 10 * (2 ** (len(times) - MAX_EXAMS_PER_DAY))
            
            # Phạt khoảng trống quá lớn
            if len(times) > 1:
                times.sort(key=lambda x: x[0])
                first_end = times[0][1]
                last_start = times[-1][0]
                gap_minutes = (last_start - first_end).total_seconds() / 60
                if gap_minutes > 120:
                    cost += (gap_minutes / 60) * 0.5

    return cost

def get_neighbor(schedule):
    """Tạo hàng xóm: Hoán đổi 2 môn thi bất kỳ"""
    new_schedule = copy.deepcopy(schedule)
    if len(new_schedule) < 2: return new_schedule
    
    idx1 = random.randint(0, len(new_schedule) - 1)
    idx2 = random.randint(0, len(new_schedule) - 1)
    while idx1 == idx2:
        idx2 = random.randint(0, len(new_schedule) - 1)
        
    # Swap nội dung (Môn, thời lượng, danh sách SV) nhưng giữ nguyên Slot (Ngày, Giờ, Phòng)
    # Lưu ý: Cần tính lại endTime vì duration có thể khác nhau
    entry1 = new_schedule[idx1]
    entry2 = new_schedule[idx2]
    
    # Swap data
    entry1['subject'], entry2['subject'] = entry2['subject'], entry1['subject']
    entry1['duration'], entry2['duration'] = entry2['duration'], entry1['duration']
    entry1['studentIds'], entry2['studentIds'] = entry2['studentIds'], entry1['studentIds']
    
    # Recalculate EndTime
    entry1['endTime'] = entry1['startTime'] + timedelta(minutes=entry1['duration'])
    entry2['endTime'] = entry2['startTime'] + timedelta(minutes=entry2['duration'])
    
    return new_schedule

async def hill_climbing_with_restart(students, config):
    """Thuật toán Hill Climbing với Random Restart"""
    MAX_RESTARTS = 10 # Giảm xuống 5 để demo nhanh hơn
    MAX_ITERATIONS = 5000
    
    global_best_schedule = None
    global_best_cost = float('inf')
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for restart in range(MAX_RESTARTS):
        status_text.text(f"Đang tối ưu hóa... Lần thử {restart + 1}/{MAX_RESTARTS}")
        try:
            current_schedule = generate_mock_schedule(students, config)
        except Exception as e:
            st.warning(f"Không thể tạo lịch ở lần thử {restart}: {e}")
            continue
            
        current_cost = calculate_cost(current_schedule, students, config)
        
        if global_best_schedule is None:
            global_best_schedule = copy.deepcopy(current_schedule)
            global_best_cost = current_cost
            
        # Hill Climbing
        for i in range(MAX_ITERATIONS):
            neighbor = get_neighbor(current_schedule)
            neighbor_cost = calculate_cost(neighbor, students, config)
            
            if neighbor_cost < current_cost:
                current_schedule = neighbor
                current_cost = neighbor_cost
            
            # Update Global
            if current_cost < global_best_cost:
                global_best_cost = current_cost
                global_best_schedule = copy.deepcopy(current_schedule)
                
            if global_best_cost == 0: break
        
        progress_bar.progress((restart + 1) / MAX_RESTARTS)
        if global_best_cost == 0: break
            
    status_text.text(f"Hoàn tất! Chi phí tối ưu: {round(global_best_cost, 2)}")
    return global_best_schedule

# ==============================================================================
# 4. FORM NHẬP LIỆU (SIDEBAR)
# ==============================================================================

with st.sidebar:
    st.header("1. Cấu hình thời gian")
    start_date = st.date_input("Ngày bắt đầu", datetime.now())
    end_date = st.date_input("Ngày kết thúc", datetime.now() + timedelta(days=5))
    
    st.subheader("Ngày nghỉ")
    # Tạo list ngày giữa start và end
    all_dates = []
    if start_date <= end_date:
        curr = start_date
        while curr <= end_date:
            all_dates.append(curr)
            curr += timedelta(days=1)
            
    # Mặc định nghỉ T7, CN
    default_rest = [d for d in all_dates if d.weekday() >= 5]
    rest_days = st.multiselect("Chọn ngày nghỉ", all_dates, default=default_rest, format_func=lambda x: f"{x} ({['T2','T3','T4','T5','T6','T7','CN'][x.weekday()]})")

    st.subheader("Ca thi")
    session_mode = st.selectbox("Chế độ", ["Sáng và Chiều", "Chỉ Sáng", "Chỉ Chiều"])
    
    col_m_1, col_m_2 = st.columns(2)
    with col_m_1:
        morning_start = st.time_input("Sáng Bắt đầu", time(7, 0))
    with col_m_2:
        morning_end = st.time_input("Sáng Kết thúc", time(11, 30))
        
    col_a_1, col_a_2 = st.columns(2)
    with col_a_1:
        afternoon_start = st.time_input("Chiều Bắt đầu", time(13, 30))
    with col_a_2:
        afternoon_end = st.time_input("Chiều Kết thúc", time(17, 0))
        
    break_minutes = st.number_input("Nghỉ giữa môn (phút)", value=10, min_value=0)

    st.header("2. Cấu hình phòng thi")
    num_rooms = st.number_input("Số lượng phòng", min_value=1, value=5)
    
    with st.expander("Đặt tên phòng"):
        room_names = []
        for i in range(int(num_rooms)):
            room_names.append(st.text_input(f"Tên phòng {i+1}", f"Phòng {i+1}", key=f"r_{i}"))
            
    st.caption("Ràng buộc số học sinh/phòng (Tùy chọn)")
    c1, c2 = st.columns(2)
    with c1:
        min_students = st.number_input("Min", min_value=0, value=0)
    with c2:
        max_students = st.number_input("Max", min_value=0, value=0)

# ==============================================================================
# 5. KHU VỰC UPLOAD VÀ CHẠY
# ==============================================================================

st.subheader("3. Dữ liệu học sinh")
uploaded_file = st.file_uploader("Tải lên file Excel (.xlsx)", type=['xlsx'])

# Nút tải file mẫu
# Tạo file mẫu giả lập trong bộ nhớ
def create_template():
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    
    # Sheet Hướng dẫn
    df_guide = pd.DataFrame(["Header dạng 'Môn(Thời lượng)' (VD: Toán(60)). Đánh dấu 'x' hoặc 'v' nếu thi."])
    df_guide.to_excel(writer, sheet_name='HuongDan', index=False, header=False)
    
    # Sheet Dữ liệu
    data = {
        'student_id': [1, 2, 3],
        'name': ['Nguyen Van A', 'Tran Thi B', 'Le Van C'],
        'Toán(90)': ['x', 'x', ''],
        'Văn(90)': ['x', '', 'x'],
        'Anh(60)': ['', 'x', 'x']
    }
    pd.DataFrame(data).to_excel(writer, sheet_name='DuLieu', index=False)
    writer.close()
    return output.getvalue()

st.download_button("📥 Tải file mẫu Excel", data=create_template(), file_name="mau_nhap_lieu.xlsx")

if st.button("🚀 TẠO LỊCH THI", type="primary"):
    if not uploaded_file:
        st.error("Vui lòng tải lên file dữ liệu!")
    else:
        try:
            # 1. Đọc dữ liệu
            df = pd.read_excel(uploaded_file)
            student_data = parse_excel_data(df)
            st.success(f"Đã đọc {len(student_data)} học sinh.")
            
            # 2. Map config
            config = {
                'start_date': start_date,
                'end_date': end_date,
                'rest_days': rest_days,
                'session_mode': 'both' if session_mode == "Sáng và Chiều" else ('morning' if session_mode == "Chỉ Sáng" else 'afternoon'),
                'morning_start': morning_start,
                'morning_end': morning_end,
                'afternoon_start': afternoon_start,
                'afternoon_end': afternoon_end,
                'break_minutes': break_minutes,
                'room_names': room_names,
                'min_students': min_students if min_students > 0 else None,
                'max_students': max_students if max_students > 0 else None
            }
            
            # 3. Chạy thuật toán (dùng asyncio run wrapper hoặc chạy thẳng vì streamlit sync)
            import asyncio
            final_schedule = asyncio.run(hill_climbing_with_restart(student_data, config))
            
            if not final_schedule:
                st.error("Không thể xếp lịch! Hãy kiểm tra lại ràng buộc (quá ít phòng, quá ít thời gian...).")
            else:
                # 4. Hiển thị kết quả
                st.markdown("---")
                st.header("✅ Kết quả Lịch Thi")
                
                # Flatten kết quả ra dạng bảng chi tiết
                detailed_rows = []
                # Map id -> name
                id_map = {s['student_id']: s['name'] for s in student_data}
                
                for entry in final_schedule:
                    for sid in entry['studentIds']:
                        detailed_rows.append({
                            "Học sinh": id_map.get(sid, "Unknown"),
                            "Mã SV": sid,
                            "Môn thi": entry['subject'],
                            "Thời lượng": entry['duration'],
                            "Ngày thi": entry['date'],
                            "Ca": entry['session'],
                            "Bắt đầu": entry['startTime'].strftime("%H:%M"),
                            "Kết thúc": entry['endTime'].strftime("%H:%M"),
                            "Phòng": entry['room']
                        })
                
                df_result = pd.DataFrame(detailed_rows)
                # Sort cho đẹp
                df_result = df_result.sort_values(by=["Ngày thi", "Bắt đầu", "Phòng", "Học sinh"])
                
                st.dataframe(df_result, use_container_width=True)
                
                # 5. Xuất Excel
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    df_result.to_excel(writer, index=False, sheet_name='LichThi')
                    
                    # Auto adjust columns width
                    worksheet = writer.sheets['LichThi']
                    for i, col in enumerate(df_result.columns):
                        width = max(df_result[col].astype(str).map(len).max(), len(col))
                        worksheet.set_column(i, i, width + 2)
                        
                st.download_button(
                    label="📥 Xuất file Excel Kết Quả",
                    data=buffer.getvalue(),
                    file_name="KetQua_LichThi.xlsx",
                    mime="application/vnd.ms-excel"
                )

        except Exception as e:
            st.error(f"Đã xảy ra lỗi: {str(e)}")
            st.exception(e)