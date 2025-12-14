document.addEventListener('DOMContentLoaded', () => {

    // === GLOBAL VARIABLES ===
    let scheduleConfig = {};
    let generatedSchedule = [];
    let detailedScheduleData = [];
    let currentPage = 1;
    const rowsPerPage = 20;
    let sortConfig = { key: 'studentName', direction: 'asc' };

    // === 1. SMOOTH SCROLL ===
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const targetId = this.getAttribute('href');
            const targetElement = document.querySelector(targetId);
            if (targetElement) {
                targetElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });

    // === 2. DYNAMIC FORM FIELDS ===
    const startDate = document.getElementById('start_date');
    const endDate = document.getElementById('end_date');
    const timeSlotsContainer = document.getElementById('time-slots-container');
    const restDaysContainer = document.getElementById('rest-days-container');
    const restDaysCheckboxes = document.getElementById('rest-days-checkboxes');

    function checkDates() {
        restDaysCheckboxes.innerHTML = '';
        if (startDate.value && endDate.value) {
            const startParts = startDate.value.split('-');
            const endParts = endDate.value.split('-');
            const start = new Date(startParts[0], startParts[1] - 1, startParts[2]);
            const end = new Date(endParts[0], endParts[1] - 1, endParts[2]);

            if (start > end) {
                alert("Ngày kết thúc phải sau ngày bắt đầu.");
                endDate.value = '';
                timeSlotsContainer.classList.add('hidden');
                restDaysContainer.classList.add('hidden');
                return;
            }

            const dayNames = ['Chủ Nhật', 'Thứ Hai', 'Thứ Ba', 'Thứ Tư', 'Thứ Năm', 'Thứ Sáu', 'Thứ Bảy'];
            let currentDate = new Date(start);

            while (currentDate <= end) {
                const year = currentDate.getFullYear();
                const month = String(currentDate.getMonth() + 1).padStart(2, '0');
                const day = String(currentDate.getDate()).padStart(2, '0');
                const dateString = `${year}-${month}-${day}`;
                const dayName = dayNames[currentDate.getDay()];

                const checkboxId = `rest-day-${dateString}`;
                const label = document.createElement('label');
                label.className = "flex items-center space-x-2 text-sm text-gray-700 cursor-pointer";

                const checkbox = document.createElement('input');
                checkbox.type = 'checkbox';
                checkbox.id = checkboxId;
                checkbox.name = 'rest_days';
                checkbox.value = currentDate.getDay(); // Send day of week (0-6) to backend
                checkbox.className = "h-4 w-4 rounded border-gray-300 text-pink-600 focus:ring-pink-500";

                // Default check Sat (6) and Sun (0)
                if (currentDate.getDay() === 0 || currentDate.getDay() === 6) {
                    checkbox.checked = true;
                }

                label.appendChild(checkbox);
                label.appendChild(document.createTextNode(` ${dayName}, ${dateString}`));
                restDaysCheckboxes.appendChild(label);

                currentDate.setDate(currentDate.getDate() + 1);
            }

            timeSlotsContainer.classList.remove('hidden');
            restDaysContainer.classList.remove('hidden');
        } else {
            timeSlotsContainer.classList.add('hidden');
            restDaysContainer.classList.add('hidden');
        }
    }
    startDate.addEventListener('change', checkDates);
    endDate.addEventListener('change', checkDates);

    // Session Mode Toggle
    const sessionModeSelect = document.getElementById('session_mode');
    const morningShiftInputs = document.getElementById('morning-shift-inputs');
    const afternoonShiftInputs = document.getElementById('afternoon-shift-inputs');

    function toggleShiftInputs() {
        const mode = sessionModeSelect.value;
        if (mode === 'morning') {
            morningShiftInputs.classList.remove('hidden');
            afternoonShiftInputs.classList.add('hidden');
        } else if (mode === 'afternoon') {
            morningShiftInputs.classList.add('hidden');
            afternoonShiftInputs.classList.remove('hidden');
        } else {
            morningShiftInputs.classList.remove('hidden');
            afternoonShiftInputs.classList.remove('hidden');
        }
    }
    sessionModeSelect.addEventListener('change', toggleShiftInputs);
    toggleShiftInputs();

    // Rooms
    const numRoomsInput = document.getElementById('num_rooms');
    const roomNamesContainer = document.getElementById('room-names-container');
    const roomNamesInputs = document.getElementById('room-names-inputs');

    numRoomsInput.addEventListener('input', (e) => {
        const num = parseInt(e.target.value, 10);
        roomNamesInputs.innerHTML = '';
        if (num > 0) {
            roomNamesContainer.classList.remove('hidden');
            for (let i = 1; i <= num; i++) {
                const input = document.createElement('input');
                input.type = 'text';
                input.value = `Phòng ${i}`;
                input.className = 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-pink-500 focus:border-pink-500';
                input.name = `room_name_${i}`;
                roomNamesInputs.appendChild(input);
            }
        } else {
            roomNamesContainer.classList.add('hidden');
        }
    });

    // === 3. FILE UPLOAD ===
    const dataFileInput = document.getElementById('data_file');
    const fileStatus = document.getElementById('file-upload-status');
    const downloadTemplateBtn = document.getElementById('download-template-btn');

    downloadTemplateBtn.addEventListener('click', () => {
        // Create a dummy Excel file for download
        const wb = XLSX.utils.book_new();
        const ws_data = [
            ["Mã SV", "Họ Tên", "Toán (90)", "Lý (60)", "Hóa (60)"],
            ["SV001", "Nguyễn Văn A", "x", "x", ""],
            ["SV002", "Trần Thị B", "", "x", "x"]
        ];
        const ws = XLSX.utils.aoa_to_sheet(ws_data);
        XLSX.utils.book_append_sheet(wb, ws, "Mau_Nhap_Lieu");
        XLSX.writeFile(wb, "mau_danh_sach_thi.xlsx");
    });

    dataFileInput.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (file) {
            fileStatus.textContent = `Đang tải lên: ${file.name}...`;
            fileStatus.className = 'text-center mt-2 text-sm text-blue-600';

            const formData = new FormData();
            formData.append('file', file);

            try {
                const res = await fetch('/api/upload', {
                    method: 'POST',
                    body: formData
                });

                if (!res.ok) throw new Error('Upload failed');

                const data = await res.json();
                fileStatus.textContent = `Đã tải lên thành công: ${data.filename} (${data.total_students} học sinh)`;
                fileStatus.className = 'text-center mt-2 text-sm text-green-600';
            } catch (err) {
                fileStatus.textContent = `Lỗi upload: ${err.message}`;
                fileStatus.className = 'text-center mt-2 text-sm text-red-600';
            }
        }
    });

    // === 4. CREATE SCHEDULE ===
    const createBtn = document.getElementById('create-schedule-btn');
    const loadingStatus = document.getElementById('loading-status');
    const resultsSection = document.getElementById('ket-qua');
    const form = document.getElementById('schedule-form');

    createBtn.addEventListener('click', async () => {
        if (!form.checkValidity()) {
            form.reportValidity();
            return;
        }

        // Gather Config
        const formData = new FormData(form);
        const rooms = [];
        const numRoomsVal = formData.get('num_rooms');
        const numRooms = numRoomsVal ? parseInt(numRoomsVal) : 0;

        if (numRooms > 0) {
            for (let i = 1; i <= numRooms; i++) {
                rooms.push({ name: formData.get(`room_name_${i}`) });
            }
        }

        // Collect off_days (days of week)
        // Note: Backend expects list of ints 0-6.
        // The checkboxes currently have values 0-6.
        const offDays = new Set();
        // Default all days are ON, we need to find which are OFF.
        // Actually, backend logic: "if current_date.weekday() not in config.off_days".
        // The UI checkboxes select REST days (OFF days).
        // So we collect checked checkboxes.
        const checkedRestDays = formData.getAll('rest_days').map(v => parseInt(v));

        // Backend expects unique list of weekday integers (0=Mon, 6=Sun)
        // JS getDay(): 0=Sun, 1=Mon... 6=Sat.
        // Python weekday(): 0=Mon... 6=Sun.
        // Mapping: JS 0 -> Py 6. JS 1 -> Py 0. JS 2 -> Py 1...
        // Py = (JS + 6) % 7 ? No.
        // JS: Sun=0, Mon=1, Tue=2, Wed=3, Thu=4, Fri=5, Sat=6
        // Py: Mon=0, Tue=1, Wed=2, Thu=3, Fri=4, Sat=5, Sun=6
        // Formula: Py = (JS + 6) % 7? 
        // Sun(0) -> (0+6)%7 = 6 (Sun). Correct.
        // Mon(1) -> (1+6)%7 = 0 (Mon). Correct.

        const pyOffDays = checkedRestDays.map(d => (d + 6) % 7);

        const config = {
            start_date: formData.get('start_date'),
            end_date: formData.get('end_date'),
            off_days: [...new Set(pyOffDays)],
            shifts: [],
            shift_times: {},
            break_time: parseInt(formData.get('break_minutes')),
            rooms: rooms,
            min_students_per_room: parseInt(formData.get('min_students')) || 0,
            max_students_per_room: parseInt(formData.get('max_students')) || 0
        };

        const mode = formData.get('session_mode');
        if (mode === 'morning' || mode === 'both') {
            config.shifts.push("Morning");
            config.shift_times["Morning"] = {
                start: formData.get('start_time_morning'),
                end: formData.get('end_time_morning')
            };
        }
        if (mode === 'afternoon' || mode === 'both') {
            config.shifts.push("Afternoon");
            config.shift_times["Afternoon"] = {
                start: formData.get('start_time_afternoon'),
                end: formData.get('end_time_afternoon')
            };
        }

        // Call API
        loadingStatus.classList.remove('hidden');
        createBtn.disabled = true;
        resultsSection.classList.add('hidden');

        try {
            const res = await fetch('/api/schedule', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(config)
            });

            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || 'Scheduling failed');
            }

            const responseData = await res.json();
            generatedSchedule = responseData.results;
            const warnings = responseData.warnings;

            if (warnings && warnings.length > 0) {
                alert("CẢNH BÁO:\n" + warnings.join("\n"));
            }

            displaySchedule(generatedSchedule);

            resultsSection.classList.remove('hidden');
            resultsSection.scrollIntoView({ behavior: 'smooth' });

        } catch (err) {
            alert('Lỗi: ' + err.message);
        } finally {
            loadingStatus.classList.add('hidden');
            createBtn.disabled = false;
        }
    });

    // === 5. RENDER TABLE ===
    // Multi-column sort state
    let sortState = []; // Array of {key, direction}

    // Filter State
    let filterState = {
        search: '',
        subject: '',
        room: '',
        date: '',
        shift: ''
    };

    function displaySchedule(data) {
        detailedScheduleData = data; // Original full data
        currentPage = 1;

        // Reset Filter State
        filterState = { search: '', subject: '', room: '', date: '', shift: '' };
        document.getElementById('search-input').value = '';
        document.getElementById('filter-subject').value = '';
        document.getElementById('filter-room').value = '';
        document.getElementById('filter-date').value = '';
        document.getElementById('filter-shift').value = '';

        // Default sort
        sortState = [
            { key: 'date', direction: 'asc' },
            { key: 'startTime', direction: 'asc' },
            { key: 'room', direction: 'asc' },
            { key: 'studentName', direction: 'asc' }
        ];

        // Update UI Components
        const placeholder = document.getElementById('schedule-placeholder');
        const tableContainer = document.getElementById('schedule-table-container');
        const paginationControls = document.getElementById('pagination-controls');
        const dashboard = document.getElementById('stats-dashboard');
        const toolbar = document.getElementById('filter-toolbar');

        if (data.length === 0) {
            placeholder.classList.remove('hidden');
            tableContainer.classList.add('hidden');
            paginationControls.classList.add('hidden');
            dashboard.classList.add('hidden');
            toolbar.classList.add('hidden');
        } else {
            placeholder.classList.add('hidden');
            tableContainer.classList.remove('hidden');
            paginationControls.classList.remove('hidden');
            dashboard.classList.remove('hidden');
            toolbar.classList.remove('hidden');

            // Populate functionalities
            updateStats(data);
            populateFilters(data);
            renderTable(); // Initial Render
        }
    }

    function updateStats(data) {
        const elTotal = document.getElementById('stat-total-exams');
        const elStudents = document.getElementById('stat-total-students');
        const elRooms = document.getElementById('stat-total-rooms');

        if (elTotal) elTotal.textContent = data.length;

        if (elStudents) {
            const uniqueStudents = new Set(data.map(i => i.student_id)).size;
            elStudents.textContent = uniqueStudents;
        }

        if (elRooms) {
            const uniqueRooms = new Set(data.map(i => i.room)).size;
            elRooms.textContent = uniqueRooms;
        }
    }

    function populateFilters(data) {
        const subjects = [...new Set(data.map(i => i.subject))].sort();
        const rooms = [...new Set(data.map(i => i.room))].sort((a, b) => {
            // Sort rooms naturally (Phòng 1, Phòng 2, Phòng 10)
            return a.localeCompare(b, undefined, { numeric: true, sensitivity: 'base' });
        });
        const dates = [...new Set(data.map(i => i.exam_date))].sort();

        const subSelect = document.getElementById('filter-subject');
        if (subSelect) {
            subSelect.innerHTML = '<option value="">Tất cả môn</option>' +
                subjects.map(s => `<option value="${s}">${s}</option>`).join('');
        }

        const roomSelect = document.getElementById('filter-room');
        if (roomSelect) {
            roomSelect.innerHTML = '<option value="">Tất cả phòng</option>' +
                rooms.map(r => `<option value="${r}">${r}</option>`).join('');
        }

        const dateSelect = document.getElementById('filter-date');
        if (dateSelect) {
            dateSelect.innerHTML = '<option value="">Tất cả ngày</option>' +
                dates.map(d => `<option value="${d}">${d}</option>`).join('');
        }
    }

    // Event Listeners for Filters
    document.getElementById('search-input').addEventListener('input', (e) => {
        filterState.search = e.target.value.toLowerCase();
        currentPage = 1;
        renderTable();
    });

    document.getElementById('filter-subject').addEventListener('change', (e) => {
        filterState.subject = e.target.value;
        currentPage = 1;
        renderTable();
    });

    document.getElementById('filter-room').addEventListener('change', (e) => {
        filterState.room = e.target.value;
        currentPage = 1;
        renderTable();
    });

    document.getElementById('filter-date').addEventListener('change', (e) => {
        filterState.date = e.target.value;
        currentPage = 1;
        renderTable();
    });

    document.getElementById('filter-shift').addEventListener('change', (e) => {
        filterState.shift = e.target.value;
        currentPage = 1;
        renderTable();
    });

    function renderTable() {
        const table = document.getElementById('schedule-table');
        const thead = table.querySelector('thead');
        const tbody = table.querySelector('tbody');
        const pageInfo = document.getElementById('page-info');
        const prevPageBtn = document.getElementById('prev-page-btn');
        const nextPageBtn = document.getElementById('next-page-btn');

        // 1. FILTER
        let filteredData = detailedScheduleData.filter(item => {
            // Search
            const s = filterState.search;
            const matchesSearch = !s ||
                item.student_name.toLowerCase().includes(s) ||
                item.student_id.toLowerCase().includes(s);

            // Subject
            const matchesSubject = !filterState.subject || item.subject === filterState.subject;

            // Room
            const matchesRoom = !filterState.room || item.room === filterState.room;

            // Date
            const matchesDate = !filterState.date || item.exam_date === filterState.date;

            // Shift
            const matchesShift = !filterState.shift || item.shift === filterState.shift;

            return matchesSearch && matchesSubject && matchesRoom && matchesDate && matchesShift;
        });

        // 2. SORT
        filteredData.sort((a, b) => {
            const mapKey = (k) => {
                if (k === 'studentName') return 'student_name';
                if (k === 'studentId') return 'student_id';
                if (k === 'date') return 'exam_date';
                if (k === 'startTime') return 'start_time';
                return k;
            };

            for (const sort of sortState) {
                const key = mapKey(sort.key);
                let valA = a[key] || '';
                let valB = b[key] || '';

                if (valA < valB) return sort.direction === 'asc' ? -1 : 1;
                if (valA > valB) return sort.direction === 'asc' ? 1 : -1;
            }
            return 0;
        });

        // Pagination
        const totalPages = Math.ceil(filteredData.length / rowsPerPage);
        const start = (currentPage - 1) * rowsPerPage;
        const pageItems = filteredData.slice(start, start + rowsPerPage);

        // Header
        thead.innerHTML = `
            <tr>
                <th class="px-6 py-3 cursor-pointer hover:bg-pink-200" onclick="setSort('studentName')">Học sinh ${getSortIcon('studentName')}</th>
                <th class="px-6 py-3 cursor-pointer hover:bg-pink-200" onclick="setSort('studentId')">Mã SV ${getSortIcon('studentId')}</th>
                <th class="px-6 py-3 cursor-pointer hover:bg-pink-200" onclick="setSort('subject')">Môn thi ${getSortIcon('subject')}</th>
                <th class="px-6 py-3 cursor-pointer hover:bg-pink-200" onclick="setSort('date')">Ngày thi ${getSortIcon('date')}</th>
                <th class="px-6 py-3">Ca thi</th>
                <th class="px-6 py-3 cursor-pointer hover:bg-pink-200" onclick="setSort('startTime')">Giờ ${getSortIcon('startTime')}</th>
                <th class="px-6 py-3 cursor-pointer hover:bg-pink-200" onclick="setSort('room')">Phòng ${getSortIcon('room')}</th>
            </tr>
        `;

        // Body
        tbody.innerHTML = pageItems.map(item => {
            const shiftVi = item.shift === 'Morning' ? 'Sáng' : (item.shift === 'Afternoon' ? 'Chiều' : item.shift);
            return `
            <tr class="bg-white border-b hover:bg-pink-50">
                <td class="px-6 py-4 font-medium text-gray-900 whitespace-nowrap">${item.student_name}</td>
                <td class="px-6 py-4">${item.student_id}</td>
                <td class="px-6 py-4 font-semibold text-pink-700">${item.subject}</td>
                <td class="px-6 py-4">${item.exam_date}</td>
                <td class="px-6 py-4">
                     <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${item.shift === 'Morning' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'}">
                        ${shiftVi}
                    </span>
                </td>
                <td class="px-6 py-4">${item.start_time} - ${item.end_time}</td>
                <td class="px-6 py-4">${item.room}</td>
            </tr>
        `}).join('');

        // Controls
        pageInfo.textContent = `Trang ${currentPage} / ${totalPages || 1}`;
        prevPageBtn.disabled = currentPage === 1;
        nextPageBtn.disabled = currentPage === totalPages || totalPages === 0;

        prevPageBtn.onclick = () => { if (currentPage > 1) { currentPage--; renderTable(); } };
        nextPageBtn.onclick = () => { if (currentPage < totalPages) { currentPage++; renderTable(); } };
    }

    window.setSort = (key) => {
        // Multi-sort logic:
        // If key exists, toggle direction and move to front
        // If key doesn't exist, add to front

        const existingIndex = sortState.findIndex(s => s.key === key);
        if (existingIndex > -1) {
            // Toggle
            sortState[existingIndex].direction = sortState[existingIndex].direction === 'asc' ? 'desc' : 'asc';
            // Move to front (primary sort)
            const item = sortState.splice(existingIndex, 1)[0];
            sortState.unshift(item);
        } else {
            // Add new primary
            sortState.unshift({ key: key, direction: 'asc' });
        }

        // Limit sort depth to avoid performance issues? Not really needed for small data.
        renderTable();
    };

    function getSortIcon(key) {
        const index = sortState.findIndex(s => s.key === key);
        if (index === -1) return '';
        const icon = sortState[index].direction === 'asc' ? '↑' : '↓';
        // Show priority number if multiple sorts?
        if (sortState.length > 1) {
            return `${icon} (${index + 1})`;
        }
        return icon;
    }

    // === 6. EXPORT ===
    document.getElementById('export-excel-btn').addEventListener('click', () => {
        if (detailedScheduleData.length === 0) return alert('Chưa có dữ liệu');

        const ws = XLSX.utils.json_to_sheet(detailedScheduleData);
        const wb = XLSX.utils.book_new();
        XLSX.utils.book_append_sheet(wb, ws, "LichThi");
        XLSX.writeFile(wb, "LichThi.xlsx");
    });

    document.getElementById('export-pdf-btn').addEventListener('click', () => {
        if (detailedScheduleData.length === 0) return alert('Chưa có dữ liệu');

        const { jsPDF } = window.jspdf;
        const doc = new jsPDF({ orientation: 'landscape' });

        const head = [['Hoc sinh', 'Ma SV', 'Mon', 'Ngay', 'Ca', 'Gio', 'Phong']];
        const body = detailedScheduleData.map(r => [
            r.student_name, r.student_id, r.subject, r.exam_date, r.shift, `${r.start_time}-${r.end_time}`, r.room
        ]);

        doc.autoTable({
            head: head,
            body: body,
            startY: 20,
            styles: { fontSize: 8 }
        });

        doc.save('LichThi.pdf');
    });

    document.getElementById('regenerate-schedule-btn').addEventListener('click', () => {
        createBtn.click();
    });

});
