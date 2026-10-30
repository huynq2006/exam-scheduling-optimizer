import sys
import os
# Add parent directory to path to allow importing from 'backend'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from faker import Faker
from faker.providers import BaseProvider
import random
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


def generated_exam_schedule(students, subjects, rooms, room_software, subject_software, slots,
                            min_subjects=3, max_subjects=5):
    """
    lich_thi + dang_ky_thi.
    Greedy scheduler that respects:
      - room must contain all software required by the subject
      - room must be 'Working' and the group size must not exceed suc_chua
      - one session per (room, slot)            -> UNIQUE uq_phong_khung
      - one student per machine in a session    -> UNIQUE uq_lich_may
      - a student never sits two exams in the same slot (rule the schema cannot enforce)
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

    # Each student picks 3-5 subjects
    enrolled = {code: [] for code in subject_codes}
    for stu in students:
        k = min(random.randint(min_subjects, max_subjects), len(subject_codes))
        for code in random.sample(subject_codes, k):
            enrolled[code].append(stu["ma_sv"])

    sessions, registrations = [], []
    busy_rooms = set()       # {(ma_phong, ma_khung)}
    busy_students = {}       # {ma_sv: {ma_khung}}
    unscheduled = []

    for code in subject_codes:
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
                ma_lich = len(sessions) + 1
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
                 publish=True):
    """
    Replace the whole dataset inside ONE transaction: if anything fails, the previous data
    is restored (rollback). Returns a summary dict (used by the Streamlit page).
    """
    if min(n_students, n_subjects, n_rooms, n_days) < 1:
        raise ValueError("All quantities must be >= 1")
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

        # Plans that are not in 'NHAP' are locked by triggers (02_views_triggers.sql):
        # unlock them first so the wipe below is allowed. Same transaction => rolled back on error.
        cursor.execute("UPDATE phuong_an SET trang_thai = 'NHAP'")
        for table in CLEAR_ORDER:
            cursor.execute(f"DELETE FROM {table}")

        # Phase 1: master data (no foreign keys)
        raw_software = generated_software()
        insert_software(connection, raw_software)
        raw_students = generated_students(n_students)
        insert_students(connection, raw_students)
        raw_rooms = generated_rooms(n_rooms)
        insert_rooms(connection, raw_rooms)
        raw_subjects = generated_subjects(n_subjects)
        insert_subjects(connection, raw_subjects)
        raw_slots = generated_time_slots(n_days)
        insert_time_slots(connection, raw_slots)
        log("Phase 1 done: master data")

        # Phase 2: software relations
        raw_room_sw = generated_room_software(raw_rooms)
        insert_room_software(connection, raw_room_sw)
        raw_subject_sw = generated_subject_software(raw_subjects)
        insert_subject_software(connection, raw_subject_sw)
        log("Phase 2 done: software relations")

        # Phase 3: exam sessions and seating
        raw_sessions, raw_registrations, unscheduled = generated_exam_schedule(
            raw_students, raw_subjects, raw_rooms, raw_room_sw, raw_subject_sw, raw_slots)
        ma_pa = insert_plan(connection, "Phương án mẫu (thuật toán tham lam)",
                            "Sinh tự động bởi generate_data.py")
        insert_sessions(connection, raw_sessions, ma_pa)
        insert_registrations(connection, raw_registrations)
        if publish:   # the sample plan becomes the official schedule students/proctors can see
            cursor.execute("UPDATE phuong_an SET trang_thai = 'DA_CONG_BO' WHERE ma_pa = %s", (ma_pa,))
        log("Phase 3 done: plan, sessions & registrations")

        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()

    return {
        "ma_pa": ma_pa, "published": bool(publish),
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

    connection = get_master_connection()
    try:
        summary = generate_all(connection, amt_of_students, amt_of_subjects,
                               amt_of_rooms, cnt_exam_days)
        print(f"Exam sessions: {summary['sessions']}, registrations: {summary['registrations']}")
        if summary["unscheduled"]:
            print(f"Unscheduled registrations (add rooms or exam days): {summary['unscheduled']}")
            print(f"First 5 unscheduled (student, subject): {summary['unscheduled_sample']}")
        print("Data generation completed successfully.")
    finally:
        connection.close()


if __name__ == "__main__":
    main()