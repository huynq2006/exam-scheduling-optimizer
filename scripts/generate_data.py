import sys
import os
# Add parent directory to path to allow importing from 'backend'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from faker import Faker
from faker.providers import BaseProvider
import random
from collections import defaultdict
from datetime import date, time, timedelta
from unidecode import unidecode
import unicodedata 

# ======================================================================
# Reference data (maps 1-to-1 with the tables in schema.sql)
# ======================================================================
# phan_mem: (ten_pm, phien_ban) -> ma_pm = index + 1
SOFTWARE_CATALOG = [
    ("Visual Studio", "2022"), ("Python", "3.12"), ("MySQL Workbench", "8.0"),
    ("PyCharm", "2024"), ("MATLAB", "R2024a"), ("Cisco Packet Tracer", "8.2"),
    ("AutoCAD", "2024"), ("Microsoft Office", "2021"), ("Eclipse", "2024-03"),
    ("Android Studio", "2023.3"), ("Oracle VirtualBox", "7.0"), ("Wireshark", "4.2"),
]
SOFTWARE_ID = {name: idx + 1 for idx, (name, _) in enumerate(SOFTWARE_CATALOG)}

# mon_thi: (ma_mon, ten_mon, so_tin_chi, thoi_luong_phut, hinh_thuc, required software)
SUBJECT_CATALOG = [
    ("INT1306", "Cấu trúc dữ liệu và giải thuật", 3, 90, "Practical", ["Visual Studio"]),
    ("INT1313", "Lập trình Python", 3, 90, "Practical", ["Python", "PyCharm"]),
    ("INT1314", "Lập trình hướng đối tượng", 3, 90, "Practical", ["Eclipse"]),
    ("INT1319", "Cơ sở dữ liệu", 3, 75, "Practical", ["MySQL Workbench"]),
    ("INT1332", "Hệ quản trị cơ sở dữ liệu", 3, 90, "Practical", ["MySQL Workbench"]),
    ("INT1336", "Mạng máy tính", 3, 60, "Computer-based test", ["Cisco Packet Tracer"]),
    ("INT1340", "An toàn mạng", 3, 75, "Practical", ["Wireshark", "Oracle VirtualBox"]),
    ("INT1359", "Lập trình Web", 3, 90, "Practical", ["Visual Studio"]),
    ("INT1449", "Lập trình di động", 3, 90, "Practical", ["Android Studio"]),
    ("INT1405", "Hệ điều hành", 3, 60, "Computer-based test", ["Oracle VirtualBox"]),
    ("MAT1101", "Giải tích số", 2, 60, "Practical", ["MATLAB"]),
    ("MAT1102", "Xác suất thống kê", 3, 60, "Practical", ["MATLAB", "Python"]),
    ("ENG1201", "Tiếng Anh chuyên ngành", 2, 45, "Computer-based test", ["Microsoft Office"]),
    ("INF1101", "Tin học văn phòng", 2, 60, "Practical", ["Microsoft Office"]),
    ("DES1301", "Đồ họa kỹ thuật", 2, 90, "Practical", ["AutoCAD"]),
    ("INT1415", "Kiểm thử phần mềm", 3, 75, "Practical", ["Eclipse", "Python"]),
    ("INT1416", "Phân tích dữ liệu", 3, 90, "Practical", ["Python", "Microsoft Office"]),
    ("INT1417", "Học máy cơ bản", 3, 90, "Practical", ["Python", "PyCharm"]),
    ("INT1418", "Kiến trúc máy tính", 3, 60, "Computer-based test", ["Oracle VirtualBox"]),
    ("INT1419", "Phát triển ứng dụng Java", 3, 90, "Practical", ["Eclipse"]),
    ("INT1420", "Điện toán đám mây", 3, 75, "Computer-based test", ["Oracle VirtualBox", "Wireshark"]),
    ("INT1421", "Trí tuệ nhân tạo", 3, 90, "Practical", ["Python", "PyCharm"]),
]

# Must match ENUM('Working','Maintenance') in phong_may.tinh_trang (01_schema.sql)
STATUS_MAINTENANCE = "Maintenance"

# phong_may hardware profile 
ROOM_CAPACITIES = [30, 36, 40, 45, 50, 60]

# sinh_vien.khoa -> class prefix
DEPARTMENTS = {
    "Công nghệ thông tin": "CNTT", "Khoa học máy tính": "KHMT",
    "Hệ thống thông tin": "HTTT", "An toàn thông tin": "ATTT",
    "Kỹ thuật phần mềm": "KTPM", "Mạng máy tính": "MMT",
}
ADMISSION_YEARS = [2021, 2022, 2023, 2024]
PHONE_PREFIXES = ["032", "033", "034", "035", "036", "037", "038", "039", "070", "076", "077",
                  "078", "079", "081", "082", "083", "085", "086", "088", "089", "090", "091",
                  "093", "094", "096", "097", "098"]

# khung_gio: 4 exam shifts per day -> (gio_bat_dau, gio_ket_thuc)
TIME_SLOTS = [(time(7, 0), time(9, 0)), (time(9, 30), time(11, 30)),
              (time(13, 0), time(15, 0)), (time(15, 30), time(17, 30))]


class VietnameseNameProvider(BaseProvider):
    """
    Custom Faker provider to generate realistic Vietnamese names (Family - Middle - Given),
    consistent with the gender stored in sinh_vien.gioi_tinh ('Nam' / 'Nu').
    """
    def vn_last_name(self):
        last_names = [
            "Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Phan", "Vũ", "Đặng", "Bùi", "Đỗ",
            "Hồ", "Ngô", "Dương", "Lý", "Vương", "Trịnh", "Đoàn", "Lâm", "Phùng", "Mai",
            "Tô", "Trương", "Hà", "Tạ", "Cao", "Khổng", "Quách"
        ]
        # Weighted so "Nguyễn" dominates, as in real populations
        weights = [30, 11, 10, 7, 5, 4, 4, 3, 3, 3, 2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
        return random.choices(last_names, weights)[0]

    def vn_middle_name(self, gender):
        if gender == "Nam":
            return random.choice(["Văn", "Đức", "Minh", "Quốc", "Hữu", "Gia", "Thành", "Công"])
        return random.choice(["Thị", "Ngọc", "Thu", "Phương", "Hồng", "Khánh", "Thùy", "Mai"])

    def vn_first_name(self, gender):
        if gender == "Nam":
            names = ["An", "Anh", "Bình", "Bảo", "Cường", "Chương", "Dũng", "Duy", "Đạt", "Đông",
                     "Hải", "Hiếu", "Hùng", "Huy", "Khang", "Khoa", "Kiên", "Long", "Lâm", "Lộc",
                     "Minh", "Nam", "Nghĩa", "Phong", "Phúc", "Quân", "Quang", "Sơn", "Thắng",
                     "Thịnh", "Thành", "Tiến", "Trung", "Tuấn", "Tùng", "Vinh", "Việt"]
        else:
            names = ["Anh", "Chi", "Giang", "Hà", "Hạnh", "Hiền", "Hoa", "Hương", "Huyền", "Lan",
                     "Linh", "Mai", "My", "Ngân", "Ngọc", "Nhi", "Nhung", "Oanh", "Phương",
                     "Quỳnh", "Thảo", "Thu", "Thủy", "Trâm", "Trang", "Tuyết", "Vy", "Yến"]
        return random.choice(names)


# Initialize Faker with Vietnamese locale and register custom name provider
fake = Faker('vi_VN')
fake.add_provider(VietnameseNameProvider)
def normalize_name(name):
    """
    Removes accents (diacritics), converts to lowercase, and removes spaces
    to create standardized strings for emails/usernames.
    """
    name = unidecode(name)
    name = name.lower()
    name = name.replace(" ", "")
    return name


# ======================================================================
# Generators (one per table; each returns a list of dicts keyed by column name)
# ======================================================================
def generated_software():
    """phan_mem: software catalogue."""
    return [{"ma_pm": SOFTWARE_ID[name], "ten_pm": name, "phien_ban": ver}
            for name, ver in SOFTWARE_CATALOG]


def generated_students(n):
    """
    sinh_vien: student records with realistic student codes, classes and university emails.
    """
    students = []

    for i in range(n):
        gender = fake.random_element(elements=('Nam', 'Nu'))
        last_name = fake.vn_last_name()
        middle_name = fake.vn_middle_name(gender)
        first_name = fake.vn_first_name(gender)
        full_name = f"{last_name} {middle_name} {first_name}"  # Vietnamese order

        year = random.choice(ADMISSION_YEARS)
        department, prefix = random.choice(list(DEPARTMENTS.items()))
        # Sequential suffix guarantees a unique ma_sv (and therefore a unique email)
        ma_sv = f"SV{year}{i + 1:04d}"
        class_name = f"D{str(year)[2:]}{prefix}{random.randint(1, 4):02d}"
        dob = fake.date_between(start_date=date(year - 19, 1, 1), end_date=date(year - 18, 12, 31))
        email = (normalize_name(first_name) + normalize_name(last_name)[0]
                 + normalize_name(middle_name)[0] + ma_sv[2:] + "@student.edu.vn")

        data = {
            "ma_sv": ma_sv,
            "ho_ten": full_name,
            "ngay_sinh": dob,
            "gioi_tinh": gender,
            "email": email,
            "so_dien_thoai": random.choice(PHONE_PREFIXES) + fake.numerify("#######"),
            "lop": class_name,
            "khoa": department,
            "khoa_hoc": year
        }
        students.append(data)

    return students


def generated_rooms(n):
    """
    phong_may: computer-lab rooms with hardware configuration. ~5% are under maintenance.
    """
    rooms = []

    if n > 500:
        print("Warning: Room count cannot exceed 500")
        n = 500

    for i in range(n):
        building = "A" if i < (n + 1) // 2 else "B"
        floor = random.randint(2, 5)
        code = f"P{building}{floor}{i + 1:03d}"  # e.g. PA2001 (unique through i + 1)
        operating_sys = "Windows 11"
        
        data = {
            "ma_phong": code,
            "ten_phong": f"Phòng máy {code}",
            "toa_nha": building,
            "tang": floor,
            "suc_chua": random.choice(ROOM_CAPACITIES),
            "he_dieu_hanh": operating_sys,
            "tinh_trang": STATUS_MAINTENANCE if random.random() < 0.05 else "Working"
        }
        rooms.append(data)

    return rooms


def generated_room_software(rooms):
    """
    phong_may_phan_mem: software installed per room (many-to-many).
    Every room has a base set; each piece of software is guaranteed to exist in >= 3 rooms
    so that every exam can be scheduled somewhere.
    """
    base = {"Microsoft Office", "Python", "Oracle VirtualBox"}
    all_names = list(SOFTWARE_ID.keys())
    installed = {r["ma_phong"]: set() for r in rooms}

    for r in rooms:
        extra = set(random.sample(all_names, random.randint(4, 8)))
        installed[r["ma_phong"]] = base | extra

    active_codes = [r["ma_phong"] for r in rooms if r["tinh_trang"] == "Working"]
    for name in all_names:
        holders = [c for c in active_codes if name in installed[c]]
        missing = [c for c in active_codes if name not in installed[c]]
        random.shuffle(missing)
        while len(holders) < min(3, len(active_codes)) and missing:
            code = missing.pop()
            installed[code].add(name)
            holders.append(code)

    return [{"ma_phong": code, "ma_pm": SOFTWARE_ID[name]}
            for code, names in installed.items() for name in sorted(names)]


def generated_subjects(n):
    """
    mon_thi: exam subjects (taken from a realistic catalogue).
    """
    if n > len(SUBJECT_CATALOG):
        print(f"Warning: Subject count cannot exceed {len(SUBJECT_CATALOG)}")
        n = len(SUBJECT_CATALOG)

    return [{"ma_mon": s[0], "ten_mon": s[1], "so_tin_chi": s[2],
             "thoi_luong_phut": s[3], "hinh_thuc": s[4]} for s in SUBJECT_CATALOG[:n]]


def generated_subject_software(subjects):
    """
    mon_thi_phan_mem: software each subject requires.
    """
    required = {s[0]: s[5] for s in SUBJECT_CATALOG}
    return [{"ma_mon": sub["ma_mon"], "ma_pm": SOFTWARE_ID[name]}
            for sub in subjects for name in required[sub["ma_mon"]]]


def generated_time_slots(days, start_date=None):
    """
    khung_gio: 4 shifts per exam day (Mon-Sat), starting from next Monday by default.
    """
    slots = []
    current = start_date or (date.today() + timedelta(days=7 - date.today().weekday()))
    ma_khung = 1

    while len(slots) < days * len(TIME_SLOTS):
        if current.weekday() < 6:  # skip Sunday
            for shift, (begin, end) in enumerate(TIME_SLOTS, start=1):
                slots.append({"ma_khung": ma_khung, "ngay_thi": current, "ca_thi": shift,
                              "gio_bat_dau": begin, "gio_ket_thuc": end})
                ma_khung += 1
        current += timedelta(days=1)

    return slots


def build_enrollment(students, subject_codes, min_subjects=3, max_subjects=5):
    """Each student picks 3-5 subjects at random -> {ma_mon: [ma_sv, ...]}."""
    enrolled = {code: [] for code in subject_codes}
    for stu in students:
        k = min(random.randint(min_subjects, max_subjects), len(subject_codes))
        for code in random.sample(subject_codes, k):
            enrolled[code].append(stu["ma_sv"])
    return enrolled


def generated_exam_schedule(students, subjects, rooms, room_software, subject_software, slots,
                            min_subjects=3, max_subjects=5, enrolled=None, existing=None, only_codes=None):
    """
    lich_thi + dang_ky_thi.
    Greedy scheduler that respects:
      - room must contain all software required by the subject
      - room must be 'Working' and the group size must not exceed suc_chua
      - one session per (room, slot)            -> UNIQUE uq_pa_phong_khung
      - one student per machine in a session    -> UNIQUE uq_lich_may
      - a student never sits two exams in the same slot (rule the schema cannot enforce)
    A subject may be split over several slots (students are grouped per session).

    Optional arguments (used to "repair" a CP-SAT result):
      enrolled   : reuse an existing enrolment {ma_mon: [ma_sv]} instead of drawing a new one
      existing   : (sessions, registrations) already placed; their rooms/slots/students stay busy
      only_codes : schedule only these subjects (the ones the solver left unscheduled)
    Returns (sessions, registrations, unscheduled) - 'unscheduled' plays the role of the
    waiting list in the dormitory sample.
    """
    sw_by_room = {}
    for link in room_software:
        sw_by_room.setdefault(link["ma_phong"], set()).add(link["ma_pm"])
    req_by_subject = {}
    for link in subject_software:
        req_by_subject.setdefault(link["ma_mon"], set()).add(link["ma_pm"])
    active_rooms = [r for r in rooms if r["tinh_trang"] == "Working"]
    subject_codes = [s["ma_mon"] for s in subjects]

    if enrolled is None:
        enrolled = build_enrollment(students, subject_codes, min_subjects, max_subjects)

    sessions = [dict(x) for x in existing[0]] if existing else []
    registrations = [dict(x) for x in existing[1]] if existing else []
    busy_rooms = {(x["ma_phong"], x["ma_khung"]) for x in sessions}      # {(ma_phong, ma_khung)}
    slot_of = {x["ma_lich"]: x["ma_khung"] for x in sessions}
    busy_students = {}                                                  # {ma_sv: {ma_khung}}
    for x in registrations:
        busy_students.setdefault(x["ma_sv"], set()).add(slot_of[x["ma_lich"]])
    unscheduled = []

    for code in subject_codes:
        if only_codes is not None and code not in only_codes:
            continue
        pending = enrolled[code][:]
        random.shuffle(pending)

        while pending:
            candidates = [(r, sl) for r in active_rooms
                          if req_by_subject.get(code, set()) <= sw_by_room.get(r["ma_phong"], set())
                          for sl in slots if (r["ma_phong"], sl["ma_khung"]) not in busy_rooms]
            random.shuffle(candidates)

            placed = False
            for room, slot in candidates:
                free = [s for s in pending if slot["ma_khung"] not in busy_students.get(s, set())]
                if len(free) < min(10, len(pending)):  # avoid near-empty sessions
                    continue

                group = free[:room["suc_chua"]]
                ma_lich = max((x["ma_lich"] for x in sessions), default=0) + 1
                sessions.append({"ma_lich": ma_lich, "ma_mon": code,
                                 "ma_phong": room["ma_phong"], "ma_khung": slot["ma_khung"]})
                busy_rooms.add((room["ma_phong"], slot["ma_khung"]))

                for seat, ma_sv in enumerate(group, start=1):
                    # Scores roughly normal around 6.8, clamped to [0, 10]
                    score = round(min(10, max(0, random.gauss(6.8, 1.6))), 2)
                    registrations.append({"ma_sv": ma_sv, "ma_lich": ma_lich,
                                          "so_may": seat, "diem": score})
                    busy_students.setdefault(ma_sv, set()).add(slot["ma_khung"])

                grouped = set(group)
                pending = [s for s in pending if s not in grouped]
                placed = True
                break

            if not placed:
                unscheduled.extend((ma_sv, code) for ma_sv in pending)
                break

    return sessions, registrations, unscheduled


# ======================================================================
# Scheduling front-end: CP-SAT (src/algo/exam_scheduler.py) with the greedy scheduler as fallback
# ======================================================================
ALGORITHMS = ("auto", "cpsat", "greedy")


def _load_cp_sat():
    """Import schedule_cp_sat lazily so the greedy path works without ortools installed."""
    try:
        from src.algo.exam_scheduler import schedule_cp_sat
        return schedule_cp_sat
    except ImportError as first:
        try:
            from src.algo.exam_scheduler import schedule_cp_sat      # same folder as this script
            return schedule_cp_sat
        except ImportError:
            raise ImportError(f"Không nạp được bộ giải CP-SAT ({first}). Cần đặt exam_scheduler.py tại "
                              f"src/algo/ và chạy `python -m pip install ortools`.") from first


def rebalance_sessions(sessions, registrations, rooms):
    """
    CP-SAT decides WHICH rooms host a subject in a slot; students were then poured into the biggest room
    first, which can leave a 1-3 student remainder room. Re-split the students of each (subject, slot)
    over its rooms proportionally to capacity. Returns renumbered (sessions, registrations).
    """
    cap = {r["ma_phong"]: r["suc_chua"] for r in rooms}
    regs_of = defaultdict(list)
    for r in registrations:
        regs_of[r["ma_lich"]].append(r)
    groups = defaultdict(list)
    for s in sessions:
        groups[(s["ma_mon"], s["ma_khung"])].append(s)

    new_sessions, new_regs = [], []
    for key in sorted(groups, key=lambda k: min(x["ma_lich"] for x in groups[k])):
        group = sorted(groups[key], key=lambda x: (-cap[x["ma_phong"]], x["ma_lich"]))
        students = [r for s in group for r in regs_of[s["ma_lich"]]]
        caps = [cap[s["ma_phong"]] for s in group]
        n, total = len(students), sum(caps)
        quotas = [n * c // total for c in caps]
        for i in sorted(range(len(caps)), key=lambda i: -(caps[i] - quotas[i]))[:n - sum(quotas)]:
            quotas[i] += 1                      # every room still has >= 1 free seat here, so quota <= capacity
        pos = 0
        for s, q in zip(group, quotas):
            if q == 0:
                continue                        # this room is not needed
            ma_lich = len(new_sessions) + 1
            new_sessions.append({**s, "ma_lich": ma_lich})
            for seat, r in enumerate(students[pos:pos + q], start=1):
                new_regs.append({**r, "ma_lich": ma_lich, "so_may": seat})
            pos += q
    return new_sessions, new_regs


def schedule_exams(students, subjects, rooms, room_software, subject_software, slots,
                   algorithm="auto", time_limit=30, workers=None, seed=None):
    """
    Returns (sessions, registrations, unscheduled, info).
      greedy : the original greedy scheduler.
      cpsat  : exam_scheduler.schedule_cp_sat (always returns a valid schedule, but may skip whole
               subjects that do not fit in one slot or that it could not place within time_limit).
      auto   : cpsat, then the greedy scheduler places the skipped subjects around the CP-SAT result
               (a subject may then be split over several slots). Falls back to greedy if ortools is missing.
    """
    if algorithm not in ALGORITHMS:
        raise ValueError(f"algorithm must be one of {ALGORITHMS}")
    enrolled = build_enrollment(students, [s["ma_mon"] for s in subjects])
    args = (students, subjects, rooms, room_software, subject_software, slots)
    info = {"algorithm": "greedy"}

    cp_sat = None
    if algorithm != "greedy":
        try:
            cp_sat = _load_cp_sat()
        except ImportError as exc:
            if algorithm == "cpsat":
                raise
            info["warning"] = f"Không dùng được CP-SAT, đã chuyển sang thuật toán tham lam. {exc}"

    if cp_sat is None:
        sessions, registrations, unscheduled = generated_exam_schedule(*args, enrolled=enrolled)
        return sessions, registrations, unscheduled, info

    workers = workers or min(8, os.cpu_count() or 1)
    sessions, registrations, unscheduled, stats = cp_sat(
        *args, enrolled=enrolled, time_limit=time_limit, workers=workers,
        seed=42 if seed is None else seed)
    sessions, registrations = rebalance_sessions(sessions, registrations, rooms)
    info.update(algorithm="cpsat", solver_status=stats["status"], solve_time=round(stats["solve_time"], 1),
                rooms_opened=stats.get("rooms_opened"), skipped_subjects=stats.get("unscheduled_subjects", 0),
                workers=workers)
    if unscheduled and algorithm == "auto":
        skipped = len(unscheduled)
        sessions, registrations, unscheduled = generated_exam_schedule(
            *args, enrolled=enrolled, existing=(sessions, registrations),
            only_codes={code for _, code in unscheduled})
        info.update(algorithm="cpsat+greedy", repaired=skipped - len(unscheduled))
        if unscheduled:
            # The solver already took rooms/slots, which can leave the greedy repair less room to
            # manoeuvre than a pure greedy run. Keep whichever result schedules more registrations.
            g_sessions, g_regs, g_unscheduled = generated_exam_schedule(*args, enrolled=enrolled)
            if len(g_unscheduled) < len(unscheduled):
                info.update(algorithm="greedy", note=f"CP-SAT + bù còn {len(unscheduled)} đăng ký chưa xếp, "
                                                     f"thuật toán tham lam thuần còn {len(g_unscheduled)} nên được dùng.")
                return g_sessions, g_regs, g_unscheduled, info
    return sessions, registrations, unscheduled, info


# ======================================================================
# Database Insertion Helper Functions
# ======================================================================
def insert_software(connection, data_list):
    cursor = connection.cursor()
    sql = """INSERT INTO phan_mem (ma_pm, ten_pm, phien_ban)
             VALUES (%s, %s, %s)"""
    values = [(d['ma_pm'], d['ten_pm'], d['phien_ban']) for d in data_list]
    cursor.executemany(sql, values)


def insert_students(connection, data_list):
    cursor = connection.cursor()
    sql = """INSERT INTO sinh_vien (ma_sv, ho_ten, ngay_sinh, gioi_tinh, email, so_dien_thoai, lop, khoa, khoa_hoc)
             VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"""
    values = [(d['ma_sv'], d['ho_ten'], d['ngay_sinh'], unicodedata.normalize('NFC', d['gioi_tinh']), d['email'],
               d['so_dien_thoai'], d['lop'], d['khoa'], d['khoa_hoc']) for d in data_list]
    cursor.executemany(sql, values)


def insert_rooms(connection, data_list):
    cursor = connection.cursor()
    sql = """INSERT INTO phong_may (ma_phong, ten_phong, toa_nha, tang, suc_chua, he_dieu_hanh, tinh_trang)
             VALUES (%s, %s, %s, %s, %s, %s, %s)"""
    values = [(d['ma_phong'], d['ten_phong'], d['toa_nha'], d['tang'], d['suc_chua'], d['he_dieu_hanh'], d['tinh_trang']) for d in data_list]
    cursor.executemany(sql, values)


def insert_room_software(connection, data_list):
    cursor = connection.cursor()
    sql = """INSERT INTO phong_may_phan_mem (ma_phong, ma_pm)
             VALUES (%s, %s)"""
    values = [(d['ma_phong'], d['ma_pm']) for d in data_list]
    cursor.executemany(sql, values)


def insert_subjects(connection, data_list):
    cursor = connection.cursor()
    sql = """INSERT INTO mon_thi (ma_mon, ten_mon, so_tin_chi, thoi_luong_phut, hinh_thuc)
             VALUES (%s, %s, %s, %s, %s)"""
    values = [(d['ma_mon'], d['ten_mon'], d['so_tin_chi'], d['thoi_luong_phut'], d['hinh_thuc'])
              for d in data_list]
    cursor.executemany(sql, values)


def insert_subject_software(connection, data_list):
    cursor = connection.cursor()
    sql = """INSERT INTO mon_thi_phan_mem (ma_mon, ma_pm)
             VALUES (%s, %s)"""
    values = [(d['ma_mon'], d['ma_pm']) for d in data_list]
    cursor.executemany(sql, values)


def insert_time_slots(connection, data_list):
    cursor = connection.cursor()
    sql = """INSERT INTO khung_gio (ma_khung, ngay_thi, ca_thi, gio_bat_dau, gio_ket_thuc)
             VALUES (%s, %s, %s, %s, %s)"""
    values = [(d['ma_khung'], d['ngay_thi'], d['ca_thi'], d['gio_bat_dau'], d['gio_ket_thuc'])
              for d in data_list]
    cursor.executemany(sql, values)


def insert_plan(connection, name, note=None):
    """Create a draft plan (phuong_an) and return its id."""
    cursor = connection.cursor()
    cursor.execute("INSERT INTO phuong_an (ten_pa, trang_thai, ghi_chu) VALUES (%s, 'NHAP', %s)",
                   (name, note))
    return cursor.lastrowid


def insert_sessions(connection, data_list, ma_pa):
    cursor = connection.cursor()
    sql = """INSERT INTO lich_thi (ma_lich, ma_pa, ma_mon, ma_phong, ma_khung)
             VALUES (%s, %s, %s, %s, %s)"""
    values = [(d['ma_lich'], ma_pa, d['ma_mon'], d['ma_phong'], d['ma_khung']) for d in data_list]
    cursor.executemany(sql, values)


def insert_registrations(connection, data_list):
    cursor = connection.cursor()
    sql = """INSERT INTO dang_ky_thi (ma_sv, ma_lich, so_may, diem)
             VALUES (%s, %s, %s, %s)"""
    values = [(d['ma_sv'], d['ma_lich'], d['so_may'], d['diem']) for d in data_list]
    cursor.executemany(sql, values)


# Child tables first, so DELETE never violates a foreign key.
CLEAR_ORDER = ["dang_ky_thi", "lich_thi", "phuong_an", "mon_thi_phan_mem", "phong_may_phan_mem",
               "khung_gio", "mon_thi", "phong_may", "phan_mem", "sinh_vien"]


def generate_all(connection, n_students, n_subjects, n_rooms, n_days, seed=None, log=print,
                 publish=True, algorithm="auto", time_limit=30, workers=None):
    """
    Replace the whole dataset inside ONE transaction: if anything fails, the previous data
    is restored (rollback). Returns a summary dict (used by the Streamlit page).

    The data is generated and the exam schedule is solved IN MEMORY first; the transaction that
    wipes and rewrites the tables only starts afterwards, so a long CP-SAT run never holds row locks.
    algorithm: 'auto' (CP-SAT + greedy repair), 'cpsat', or 'greedy'; time_limit: solver seconds.
    workers: CP-SAT threads (None = up to 8). With a seed, workers=1 gives reproducible results.
    """
    if min(n_students, n_subjects, n_rooms, n_days) < 1:
        raise ValueError("All quantities must be >= 1")
    if algorithm not in ALGORITHMS:
        raise ValueError(f"algorithm must be one of {ALGORITHMS}")
    if seed is not None:
        random.seed(seed)
        Faker.seed(seed)

    cursor = connection.cursor()
    try:
        # Master/replica guard: never write to a read-only node (a replica).
        cursor.execute("SELECT @@read_only AS ro")
        row = cursor.fetchone()
        if (row["ro"] if isinstance(row, dict) else row[0]):
            raise RuntimeError("Node hiện tại ở chế độ chỉ đọc (read_only=1, có thể là replica). "
                               "Hãy kết nối vào MASTER để sinh dữ liệu.")

        # Phase 0: generate + schedule in memory (no locks held while the solver runs)
        raw_software = generated_software()
        raw_students = generated_students(n_students)
        raw_rooms = generated_rooms(n_rooms)
        raw_subjects = generated_subjects(n_subjects)
        raw_slots = generated_time_slots(n_days)
        raw_room_sw = generated_room_software(raw_rooms)
        raw_subject_sw = generated_subject_software(raw_subjects)
        raw_sessions, raw_registrations, unscheduled, info = schedule_exams(
            raw_students, raw_subjects, raw_rooms, raw_room_sw, raw_subject_sw, raw_slots,
            algorithm=algorithm, time_limit=time_limit, workers=workers, seed=seed)
        log(f"Phase 0 done: data generated and scheduled ({info['algorithm']})")

        # Phase 1: wipe + write. Plans that are not in 'NHAP' are locked by triggers
        # (02_views_triggers.sql): unlock them first so the wipe is allowed.
        cursor.execute("UPDATE phuong_an SET trang_thai = 'NHAP'")
        for table in CLEAR_ORDER:
            cursor.execute(f"DELETE FROM {table}")
        insert_software(connection, raw_software)
        insert_students(connection, raw_students)
        insert_rooms(connection, raw_rooms)
        insert_subjects(connection, raw_subjects)
        insert_time_slots(connection, raw_slots)
        insert_room_software(connection, raw_room_sw)
        insert_subject_software(connection, raw_subject_sw)
        log("Phase 1 done: master data")

        label = {"greedy": "thuật toán tham lam", "cpsat": "CP-SAT",
                 "cpsat+greedy": "CP-SAT + tham lam bù"}[info["algorithm"]]
        note = f"Sinh bởi generate_data.py; {info['algorithm']}"
        if "solver_status" in info:
            note += f"; solver={info['solver_status']} {info['solve_time']}s"
        ma_pa = insert_plan(connection, f"Phương án mẫu ({label})", note)
        insert_sessions(connection, raw_sessions, ma_pa)
        insert_registrations(connection, raw_registrations)
        if publish:   # the sample plan becomes the official schedule students/proctors can see
            cursor.execute("UPDATE phuong_an SET trang_thai = 'DA_CONG_BO' WHERE ma_pa = %s", (ma_pa,))
        log("Phase 2 done: plan, sessions & registrations")

        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()

    return {
        "ma_pa": ma_pa, "published": bool(publish), "solver": info,
        "students": len(raw_students), "subjects": len(raw_subjects),
        "rooms": len(raw_rooms),
        "rooms_maintenance": sum(r["tinh_trang"] != "Working" for r in raw_rooms),
        "slots": len(raw_slots), "sessions": len(raw_sessions),
        "registrations": len(raw_registrations),
        "unscheduled": len(unscheduled), "unscheduled_sample": unscheduled[:5],
    }


def main():
    """CLI entry point: ask for the data volume, then call generate_all()."""
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from src.backend.db_helper import get_master_connection

    amt_of_students = int(input("Number of students: "))
    amt_of_subjects = int(input("Number of exam subjects: "))
    amt_of_rooms = int(input("Number of computer rooms: "))
    cnt_exam_days = int(input("Number of exam days: "))

    algo = input(f"Scheduling algorithm {list(ALGORITHMS)} (default auto): ").strip() or "auto"
    tl = input("Solver time limit in seconds (default 30): ").strip()

    connection = get_master_connection()
    try:
        summary = generate_all(connection, amt_of_students, amt_of_subjects,
                               amt_of_rooms, cnt_exam_days, algorithm=algo,
                               time_limit=int(tl) if tl else 30)
        print(f"Algorithm used: {summary['solver']}")
        print(f"Exam sessions: {summary['sessions']}, registrations: {summary['registrations']}")
        if summary["unscheduled"]:
            print(f"Unscheduled registrations (add rooms or exam days): {summary['unscheduled']}")
            print(f"First 5 unscheduled (student, subject): {summary['unscheduled_sample']}")
        print("Data generation completed successfully.")
    finally:
        connection.close()

if __name__ == "__main__":
    main()