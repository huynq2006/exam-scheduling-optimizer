import os
import pymysql
from urllib.parse import urlparse
from dotenv import load_dotenv

# Load environment variables from .env (once)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'))


class BusinessRuleError(Exception):
    """Raised when an operation violates an exam-scheduling rule (not a database failure)."""
    pass


def _get_connection(url_env):
    """Open and return a PyMySQL connection described by an environment variable."""
    db_url = os.getenv(url_env)

    if not db_url:
        raise ValueError(f"Error: {url_env} environment variable is missing!")

    # Parse the connection URL to extract individual credentials
    parsed = urlparse(db_url)

    # Establish and return the PyMySQL connection using extracted parameters
    try:
        return pymysql.connect(
            host=parsed.hostname,              # e.g., 'mysql-master'
            user=parsed.username,              # e.g., 'app_user'
            password=parsed.password,          # e.g., 'App_Pass@123'
            database=parsed.path.lstrip('/'),  # e.g., 'quan_ly_thi'
            port=parsed.port or 3306,          # Fallback to default MySQL port if missing
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
    except pymysql.Error as e:
        # Catch network/authentication errors early for clear logging
        print(f"[CONNECTION ERROR] Cannot connect to DB via {url_env}: {e}")
        raise e


def get_slave_connection():
    """Returns a connection to the Read-Only Replica (Slave)."""
    return _get_connection('DB_SLAVE_URL')


def get_master_connection():
    """Returns a connection to the Primary Database (Master)."""
    return _get_connection('DB_MASTER_URL')


def fetch_data(query, params=None):
    """
    READ data function (Routes to SLAVE).
    Used exclusively for read-only workloads such as SELECT statements.
    """
    conn = get_slave_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            result = cursor.fetchall()
            return result
    except pymysql.MySQLError as e:
        print(f"[SLAVE READ ERROR]: {e}")
        raise Exception(f"Database Read Error: {e}")
    except Exception as e:
        print(f"[SYSTEM ERROR] Unexpected error during read operation: {e}")
        raise Exception(f"SYSTEM Error: {e}")
    finally:
        # Ensure the connection exists before attempting to close it
        if conn:
            conn.close()


def execute_write(query, params=None):
    """
    WRITE data function (Routes to MASTER).
    Used for single-statement changes: INSERT, UPDATE, DELETE, CALL PROCEDURE.
    Includes built-in ACID transaction management (commit/rollback).
    """
    conn = get_master_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, params)
        conn.commit()  # Commit transaction if successful
        return cursor.lastrowid  # Return the ID of the newly inserted row (if applicable)
    except pymysql.MySQLError as e:
        if conn:
            conn.rollback()  # Rollback immediately if an error occurs to maintain data integrity
        print(f"[MASTER WRITE ERROR]: {e}")
        raise Exception(f"Database Write Error: {e}")
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"[SYSTEM ERROR] Unexpected error during write operation: {e}")
        raise Exception(f"SYSTEM Error: {e}")

    finally:
        if conn:
            conn.close()


def execute_transaction(work):
    """
    WRITE data function for multi-step operations (Routes to MASTER).
    `work(cursor)` runs several statements inside ONE transaction and returns a result.
    Commits on success, rolls back on any error. BusinessRuleError is re-raised unchanged
    so callers can show the message to the user.
    """
    conn = get_master_connection()
    try:
        conn.begin()
        with conn.cursor() as cursor:
            result = work(cursor)
        conn.commit()
        return result
    except BusinessRuleError:
        if conn:
            conn.rollback()
        raise
    except pymysql.MySQLError as e:
        if conn:
            conn.rollback()
        print(f"[MASTER TRANSACTION ERROR]: {e}")
        raise Exception(f"Database Write Error: {e}")
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"[SYSTEM ERROR] Unexpected error during transaction: {e}")
        raise Exception(f"SYSTEM Error: {e}")
    finally:
        if conn:
            conn.close()


# ======================================================================
# READ functions (SLAVE)
# ======================================================================
def fetch_rooms():
    """
    Query room list with hardware configuration (for dashboard/frontend).
    """
    return fetch_data("SELECT * FROM phong_may ORDER BY ma_phong")


def fetch_room_software(ma_phong):
    """
    Fetch the software installed in one room.
    """
    query = """
        SELECT pm.ma_pm, pm.ten_pm, pm.phien_ban
        FROM phong_may_phan_mem x
        JOIN phan_mem pm ON pm.ma_pm = x.ma_pm
        WHERE x.ma_phong = %s
        ORDER BY pm.ten_pm
    """
    return fetch_data(query, (ma_phong,))


def fetch_subjects():
    """
    Fetch all exam subjects with the software each one requires.
    """
    query = """
        SELECT m.ma_mon, m.ten_mon, m.so_tin_chi, m.thoi_luong_phut, m.hinh_thuc,
               GROUP_CONCAT(pm.ten_pm ORDER BY pm.ten_pm SEPARATOR ', ') AS phan_mem_yeu_cau
        FROM mon_thi m
        LEFT JOIN mon_thi_phan_mem r ON r.ma_mon = m.ma_mon
        LEFT JOIN phan_mem pm ON pm.ma_pm = r.ma_pm
        GROUP BY m.ma_mon, m.ten_mon, m.so_tin_chi, m.thoi_luong_phut, m.hinh_thuc
        ORDER BY m.ma_mon
    """
    return fetch_data(query)


def fetch_time_slots():
    """
    Fetch all exam time slots (khung_gio).
    """
    return fetch_data("SELECT * FROM khung_gio ORDER BY ngay_thi, ca_thi")


def fetch_exam_schedule(ngay_thi=None, ma_mon=None):
    """
    Fetch exam sessions with subject, room, time slot and number of seated students.
    Optional filters: exam date (YYYY-MM-DD) and subject code.
    """
    query = """
        SELECT l.ma_lich, l.ma_mon, m.ten_mon,
               l.ma_phong, p.suc_chua,
               k.ngay_thi, k.ca_thi, k.gio_bat_dau, k.gio_ket_thuc,
               (SELECT COUNT(*) FROM dang_ky_thi d WHERE d.ma_lich = l.ma_lich) AS so_thi_sinh
        FROM lich_thi l
        JOIN mon_thi m   ON m.ma_mon = l.ma_mon
        JOIN phong_may p ON p.ma_phong = l.ma_phong
        JOIN khung_gio k ON k.ma_khung = l.ma_khung
        WHERE 1 = 1
    """
    params = []
    if ngay_thi:
        query += " AND k.ngay_thi = %s"
        params.append(ngay_thi)
    if ma_mon:
        query += " AND l.ma_mon = %s"
        params.append(ma_mon)
    query += " ORDER BY k.ngay_thi, k.ca_thi, l.ma_phong"
    return fetch_data(query, tuple(params))


def fetch_student_info(ma_sv):
    """
    Fetch student personal information by student code.
    """
    query = """
        SELECT ma_sv, ho_ten, ngay_sinh, gioi_tinh, email, so_dien_thoai, lop, khoa, khoa_hoc
        FROM sinh_vien
        WHERE ma_sv = %s
    """
    return fetch_data(query, (ma_sv,))


def fetch_student_schedule(ma_sv):
    """
    Fetch every exam a student has to sit: subject, date, shift, room, machine number and score.
    """
    query = """
        SELECT d.ma_lich, l.ma_mon, m.ten_mon,
               k.ngay_thi, k.ca_thi, k.gio_bat_dau, k.gio_ket_thuc,
               l.ma_phong, d.so_may, d.diem
        FROM dang_ky_thi d
        JOIN lich_thi l  ON l.ma_lich = d.ma_lich
        JOIN mon_thi m   ON m.ma_mon = l.ma_mon
        JOIN khung_gio k ON k.ma_khung = l.ma_khung
        WHERE d.ma_sv = %s
        ORDER BY k.ngay_thi, k.ca_thi
    """
    return fetch_data(query, (ma_sv,))


def fetch_session_roster(ma_lich):
    """
    Fetch the seating list (danh sách phòng thi) of one exam session.
    """
    query = """
        SELECT d.so_may, s.ma_sv, s.ho_ten, s.lop, d.diem
        FROM dang_ky_thi d
        JOIN sinh_vien s ON s.ma_sv = d.ma_sv
        WHERE d.ma_lich = %s
        ORDER BY d.so_may
    """
    return fetch_data(query, (ma_lich,))


def fetch_available_rooms(ma_mon, ma_khung):
    """
    Fetch rooms that can host a subject in a time slot: active, free in that slot,
    and with ALL the software the subject requires.
    """
    query = """
        SELECT p.ma_phong, p.ten_phong, p.suc_chua, p.cpu, p.ram_gb, p.he_dieu_hanh
        FROM phong_may p
        WHERE p.tinh_trang = 'Hoạt động'
          AND NOT EXISTS (
                SELECT 1 FROM lich_thi l
                WHERE l.ma_phong = p.ma_phong AND l.ma_khung = %s)
          AND NOT EXISTS (
                SELECT 1 FROM mon_thi_phan_mem r
                WHERE r.ma_mon = %s
                  AND r.ma_pm NOT IN (SELECT x.ma_pm FROM phong_may_phan_mem x
                                      WHERE x.ma_phong = p.ma_phong))
        ORDER BY p.suc_chua DESC, p.ma_phong
    """
    return fetch_data(query, (ma_khung, ma_mon))


def fetch_room_utilization():
    """
    Fetch how many time slots each room is used in, as a percentage of all slots.
    """
    query = """
        SELECT p.ma_phong, p.ten_phong, p.suc_chua, p.tinh_trang,
               COUNT(l.ma_lich) AS so_ca_thi,
               (SELECT COUNT(*) FROM khung_gio) AS tong_so_ca,
               ROUND(COUNT(l.ma_lich) * 100 / (SELECT COUNT(*) FROM khung_gio), 1) AS ty_le_su_dung
        FROM phong_may p
        LEFT JOIN lich_thi l ON l.ma_phong = p.ma_phong
        GROUP BY p.ma_phong, p.ten_phong, p.suc_chua, p.tinh_trang
        ORDER BY ty_le_su_dung DESC, p.ma_phong
    """
    return fetch_data(query)


def fetch_score_statistics():
    """
    Fetch score statistics per subject (only graded registrations are counted).
    """
    query = """
        SELECT m.ma_mon, m.ten_mon,
               COUNT(d.diem) AS so_bai_da_cham,
               ROUND(AVG(d.diem), 2) AS diem_trung_binh,
               MIN(d.diem) AS diem_thap_nhat,
               MAX(d.diem) AS diem_cao_nhat
        FROM mon_thi m
        LEFT JOIN lich_thi l     ON l.ma_mon = m.ma_mon
        LEFT JOIN dang_ky_thi d  ON d.ma_lich = l.ma_lich
        GROUP BY m.ma_mon, m.ten_mon
        ORDER BY m.ma_mon
    """
    return fetch_data(query)


def fetch_student_clashes():
    """
    Data-quality audit: students seated in more than one session of the same time slot.
    Should always return an empty list.
    """
    query = """
        SELECT d.ma_sv, l.ma_khung, COUNT(*) AS so_mon
        FROM dang_ky_thi d
        JOIN lich_thi l ON l.ma_lich = d.ma_lich
        GROUP BY d.ma_sv, l.ma_khung
        HAVING COUNT(*) > 1
    """
    return fetch_data(query)


# ======================================================================
# WRITE functions (MASTER)
# ======================================================================
def create_exam_session(ma_mon, ma_phong, ma_khung):
    """
    Create a new exam session (lich_thi). Validates inside one transaction that:
      - the room is active
      - the room has every software the subject requires
      - the room is not already booked in that slot (also guarded by UNIQUE uq_phong_khung)
    Returns the new ma_lich.
    """
    def work(cursor):
        cursor.execute("SELECT tinh_trang FROM phong_may WHERE ma_phong = %s", (ma_phong,))
        room = cursor.fetchone()
        if not room:
            raise BusinessRuleError(f"Room {ma_phong} does not exist")
        if room["tinh_trang"] != "Hoạt động":
            raise BusinessRuleError(f"Room {ma_phong} is under maintenance")

        cursor.execute("""
            SELECT COUNT(*) AS missing
            FROM mon_thi_phan_mem r
            WHERE r.ma_mon = %s
              AND r.ma_pm NOT IN (SELECT ma_pm FROM phong_may_phan_mem WHERE ma_phong = %s)
        """, (ma_mon, ma_phong))
        if cursor.fetchone()["missing"] > 0:
            raise BusinessRuleError(f"Room {ma_phong} lacks software required by {ma_mon}")

        try:
            cursor.execute(
                "INSERT INTO lich_thi (ma_mon, ma_phong, ma_khung) VALUES (%s, %s, %s)",
                (ma_mon, ma_phong, ma_khung))
        except pymysql.err.IntegrityError as e:
            if e.args[0] == 1062:
                raise BusinessRuleError(f"Room {ma_phong} is already booked in this time slot")
            if e.args[0] == 1452:
                raise BusinessRuleError("Subject or time slot does not exist")
            raise
        return cursor.lastrowid

    return execute_transaction(work)


def register_student_exam(ma_sv, ma_lich):
    """
    Seat a student in an exam session. Validates inside one transaction that:
      - the student and the session exist
      - the student has no other exam in the same time slot
      - the room still has a free machine
    Picks the lowest free machine number and returns it.
    The session row is locked (FOR UPDATE) so two concurrent registrations cannot take the same seat.
    """
    def work(cursor):
        cursor.execute("SELECT 1 FROM sinh_vien WHERE ma_sv = %s", (ma_sv,))
        if not cursor.fetchone():
            raise BusinessRuleError(f"Student {ma_sv} does not exist")

        cursor.execute("""
            SELECT l.ma_khung, p.suc_chua
            FROM lich_thi l
            JOIN phong_may p ON p.ma_phong = l.ma_phong
            WHERE l.ma_lich = %s
            FOR UPDATE
        """, (ma_lich,))
        session = cursor.fetchone()
        if not session:
            raise BusinessRuleError(f"Exam session {ma_lich} does not exist")

        cursor.execute("""
            SELECT 1
            FROM dang_ky_thi d
            JOIN lich_thi l ON l.ma_lich = d.ma_lich
            WHERE d.ma_sv = %s AND l.ma_khung = %s
            LIMIT 1
        """, (ma_sv, session["ma_khung"]))
        if cursor.fetchone():
            raise BusinessRuleError(f"Student {ma_sv} already has an exam in this time slot")

        cursor.execute("SELECT so_may FROM dang_ky_thi WHERE ma_lich = %s", (ma_lich,))
        used = {row["so_may"] for row in cursor.fetchall()}
        seat = next((n for n in range(1, session["suc_chua"] + 1) if n not in used), None)
        if seat is None:
            raise BusinessRuleError(f"Exam session {ma_lich} is full")

        cursor.execute(
            "INSERT INTO dang_ky_thi (ma_sv, ma_lich, so_may) VALUES (%s, %s, %s)",
            (ma_sv, ma_lich, seat))
        return seat

    return execute_transaction(work)


def cancel_registration(ma_sv, ma_lich):
    """
    Remove a student from an exam session. Returns the number of deleted rows (0 or 1).
    """
    def work(cursor):
        cursor.execute("DELETE FROM dang_ky_thi WHERE ma_sv = %s AND ma_lich = %s", (ma_sv, ma_lich))
        if cursor.rowcount == 0:
            raise BusinessRuleError("Registration not found")
        return cursor.rowcount

    return execute_transaction(work)


def record_score(ma_sv, ma_lich, diem):
    """
    Save the score (0-10) of a student for an exam session.
    """
    if diem is None or not (0 <= diem <= 10):
        raise BusinessRuleError("Score must be between 0 and 10")

    def work(cursor):
        cursor.execute(
            "UPDATE dang_ky_thi SET diem = %s WHERE ma_sv = %s AND ma_lich = %s",
            (diem, ma_sv, ma_lich))
        if cursor.rowcount == 0:
            raise BusinessRuleError("Registration not found (or score unchanged)")
        return cursor.rowcount

    return execute_transaction(work)


def set_room_status(ma_phong, tinh_trang):
    """
    Change a room status ('Hoạt động' or 'Bảo trì').
    """
    if tinh_trang not in ("Hoạt động", "Bảo trì"):
        raise BusinessRuleError("Invalid status")
    query = "UPDATE phong_may SET tinh_trang = %s WHERE ma_phong = %s"
    return execute_write(query, (tinh_trang, ma_phong))