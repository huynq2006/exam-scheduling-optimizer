import streamlit as st
import pandas as pd
from datetime import date

# ==============================================================================
# CẤU HÌNH TRANG & GIAO DIỆN
# ==============================================================================
st.set_page_config(
    page_title="ExamScheduler - Hệ thống xếp lịch thi & phòng máy",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS cho phong cách Clean & Professional
st.markdown("""
<style>
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2.5rem;
    }
    
    [data-testid="stSidebar"] {
        background-color: #F8FAFC;
        border-right: 1px solid #E2E8F0;
    }
    
    div[data-testid="stMetric"] {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        padding: 14px 18px;
        border-radius: 10px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.03);
    }
    
    .role-badge {
        display: inline-block;
        padding: 4px 12px;
        font-size: 12px;
        font-weight: 600;
        border-radius: 20px;
        background-color: #EFF6FF;
        color: #1D4ED8;
        border: 1px solid #BFDBFE;
    }
    
    .user-profile-box {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 12px;
        margin-bottom: 12px;
    }
</style>
""", unsafe_allow_html=True)


# ==============================================================================
# KẾT NỐI CSDL & TIỆN ÍCH TRUY VẤN (đọc dữ liệu thật từ schema quan_ly_thi)
# ==============================================================================
import sys
import importlib.util
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
# Tìm thư mục gốc dự án (nơi có src/backend/db_helper.py) để import được get_master_connection
ROOT = next((p for p in [HERE, *HERE.parents] if (p / "src" / "backend").exists()), None)
for _p in (ROOT, HERE):
    if _p and str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

try:
    from src.backend.db_helper import get_master_connection
    DB_IMPORT_ERROR = None
except Exception as exc:  # noqa: BLE001 - hiển thị lỗi cho người dùng thay vì crash
    get_master_connection = None
    DB_IMPORT_ERROR = exc


def _rows(cur):
    """Chuẩn hoá kết quả cursor (tuple hoặc dict) thành list[dict]."""
    cols = [d[0] for d in cur.description]
    return [r if isinstance(r, dict) else dict(zip(cols, r)) for r in cur.fetchall()], cols


def _run_query(sql: str, params: tuple = ()) -> pd.DataFrame:
    """Chạy SELECT và trả về DataFrame (không cache)."""
    conn = get_master_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql, params or None)
        rows, cols = _rows(cur)
    finally:
        conn.close()
    df = pd.DataFrame(rows, columns=cols)
    for c in df.columns:  # Decimal (vd. dang_ky_thi.diem) -> float để hiển thị/tính toán
        if df[c].map(lambda v: isinstance(v, Decimal)).any():
            df[c] = df[c].astype(float)
    return df


@st.cache_data(ttl=60, show_spinner=False)
def query_df(sql: str, params: tuple = ()) -> pd.DataFrame:
    """Bản có cache 60s; nút 'Làm mới dữ liệu' hoặc việc sinh dữ liệu mới sẽ xoá cache."""
    return _run_query(sql, params)


def db_ping():
    """Kiểm tra kết nối + schema (bảng phuong_an và 2 view từ 02_views_triggers.sql)."""
    if get_master_connection is None:
        return False, f"Không import được src.backend.db_helper: {DB_IMPORT_ERROR}"
    try:
        conn = get_master_connection()
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) AS n FROM sinh_vien")
        cur.fetchall()
        try:
            for sql in ("SELECT COUNT(*) AS n FROM phuong_an",
                        "SELECT * FROM v_vi_pham LIMIT 0",
                        "SELECT * FROM v_lich_thi_cong_bo LIMIT 0"):
                cur.execute(sql)
                cur.fetchall()
        except Exception as exc:  # noqa: BLE001
            return False, ("Thiếu bảng `phuong_an` hoặc view kiểm tra: chạy lại 01_schema.sql rồi "
                           "02_views_triggers.sql.\n" + str(exc))
        return True, ""
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)
    finally:
        conn.close()


def load_generator():
    """Nạp generate_data.py (tìm ở thư mục app, thư mục gốc dự án và các thư mục con trực tiếp)."""
    dirs = [HERE]
    if ROOT:
        dirs += [ROOT, *sorted(p for p in ROOT.iterdir() if p.is_dir())]
    for d in dirs:
        f = d / "generate_data.py"
        if f.exists():
            spec = importlib.util.spec_from_file_location("generate_data", f)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    return None


def fmt_dates(series):
    return pd.to_datetime(series).dt.strftime("%d/%m/%Y")


def slot_labels(df):
    return [f"Ca {c} ({b} - {e})" for c, b, e in zip(df["ca_thi"], df["gio_bd"], df["gio_kt"])]


SLOT_SQL = ("CAST(kg.ngay_thi AS CHAR) AS ngay_iso, kg.ca_thi, "
            "LEFT(CAST(kg.gio_bat_dau AS CHAR), 5) AS gio_bd, "
            "LEFT(CAST(kg.gio_ket_thuc AS CHAR), 5) AS gio_kt")
SW_LIST = "GROUP_CONCAT(CONCAT(p.ten_pm, ' ', COALESCE(p.phien_ban, '')) ORDER BY p.ten_pm SEPARATOR ', ')"


PLAN_LABEL = {"NHAP": "Nháp", "CHO_DUYET": "Chờ duyệt", "DA_DUYET": "Đã duyệt",
              "DA_CONG_BO": "Đã công bố", "LUU_TRU": "Lưu trữ"}
ALGO_OPTIONS = {"Tự động (CP-SAT, tham lam xếp bù phần còn lại)": "auto",
                "CP-SAT (có thể bỏ môn không vừa)": "cpsat",
                "Tham lam (nhanh, dùng nhiều phòng)": "greedy"}
LOAI_LABEL = {"VUOT_SUC_CHUA": "Vượt sức chứa phòng", "THIEU_PHAN_MEM": "Phòng thiếu phần mềm",
              "PHONG_BAO_TRI": "Phòng đang bảo trì", "SV_TRUNG_KHUNG_GIO": "SV trùng khung giờ",
              "SO_MAY_NGOAI_PHONG": "Số máy vượt sức chứa"}


def load_overview(ma_pa):
    return query_df("""
        SELECT (SELECT COUNT(*) FROM mon_thi) AS mon,
               (SELECT COUNT(*) FROM phong_may) AS phong,
               (SELECT COUNT(*) FROM phong_may WHERE tinh_trang = 'Working') AS phong_ok,
               (SELECT COUNT(*) FROM sinh_vien) AS sv,
               (SELECT COUNT(*) FROM lich_thi WHERE ma_pa = %s) AS lich,
               (SELECT COUNT(*) FROM dang_ky_thi dk JOIN lich_thi lt ON lt.ma_lich = dk.ma_lich
                 WHERE lt.ma_pa = %s) AS dk,
               (SELECT COUNT(*) FROM khung_gio) AS khung""", (ma_pa, ma_pa)).iloc[0]


def load_plans():
    return query_df("""
        SELECT p.ma_pa, p.ten_pa, p.trang_thai, CAST(p.tao_luc AS CHAR) AS tao_luc, p.ghi_chu,
               (SELECT COUNT(*) FROM lich_thi lt WHERE lt.ma_pa = p.ma_pa) AS so_ca
        FROM phuong_an p ORDER BY p.ma_pa DESC""")


def load_violations(ma_pa):
    """Các vi phạm ràng buộc cứng của một phương án (rỗng = hợp lệ)."""
    return query_df("SELECT ma_lich, loai, chi_tiet FROM v_vi_pham WHERE ma_pa = %s ORDER BY loai, ma_lich",
                    (ma_pa,))


def load_sessions(ma_pa=None, published=False):
    """Ca thi của một phương án; published=True đọc từ view lịch đã công bố (cho SV/giám thị)."""
    src = "v_lich_thi_cong_bo" if published else "lich_thi"
    where = "" if published else "WHERE lt.ma_pa = %s"
    return query_df(f"""
        SELECT lt.ma_lich, lt.ma_pa, {SLOT_SQL}, lt.ma_mon, mt.ten_mon, lt.ma_phong,
               pm.suc_chua, pm.toa_nha, pm.tang,
               (SELECT COUNT(*) FROM dang_ky_thi dk WHERE dk.ma_lich = lt.ma_lich) AS so_sv
        FROM {src} lt
        JOIN khung_gio kg ON kg.ma_khung = lt.ma_khung
        JOIN mon_thi mt ON mt.ma_mon = lt.ma_mon
        JOIN phong_may pm ON pm.ma_phong = lt.ma_phong
        {where}
        ORDER BY kg.ngay_thi, kg.ca_thi, lt.ma_phong""", () if published else (ma_pa,))


# ------------------------------------------------------------------------------
# GHI DỮ LIỆU: mọi thao tác ghi chạy trên MASTER, trong 1 giao dịch
# ------------------------------------------------------------------------------
def friendly_db_error(exc) -> str:
    msg = str(exc)
    code = exc.args[0] if getattr(exc, "args", None) and isinstance(exc.args[0], int) else None
    if code == 1062 or "Duplicate entry" in msg:
        return ("Xung đột dữ liệu: phòng/khung giờ hoặc số máy vừa bị người khác chiếm. "
                "Hãy làm mới dữ liệu rồi thử lại.")
    if "Phuong an da khoa" in msg:
        return ("Phương án đang bị khóa (không ở trạng thái Nháp). "
                "Hãy tạo bản nháp từ phương án này để chỉnh sửa.")
    return msg


def _fetch(cur, sql, args=None):
    cur.execute(sql, args)
    return _rows(cur)[0]


def _tx(work):
    """Chạy work(cur) -> (ok, [thông báo], extra) trong một giao dịch; commit nếu ok, ngược lại rollback."""
    conn = get_master_connection()
    try:
        cur = conn.cursor()
        if _fetch(cur, "SELECT @@read_only AS ro")[0]["ro"]:
            return False, ["Node CSDL đang ở chế độ chỉ đọc (replica?). Cần kết nối vào MASTER để ghi."], None
        ok, msgs, extra = work(cur)
        conn.commit() if ok else conn.rollback()
        return ok, msgs, extra
    except Exception as exc:  # noqa: BLE001
        try:
            conn.rollback()
        except Exception:  # noqa: BLE001
            pass
        return False, [friendly_db_error(exc)], None
    finally:
        conn.close()


def _room_errors(cur, ses, room_code, need):
    """Kiểm tra phòng `room_code` có nhận được `need` sinh viên của ca `ses` không."""
    rows = _fetch(cur, "SELECT tinh_trang, suc_chua FROM phong_may WHERE ma_phong = %s", (room_code,))
    if not rows:
        return ["Phòng không tồn tại."]
    room, errors = rows[0], []
    if room["tinh_trang"] != "Working":
        errors.append("Phòng đang bảo trì.")
    if need > room["suc_chua"]:
        errors.append(f"Phòng chỉ có {room['suc_chua']} máy nhưng cần {need} chỗ.")
    missing = [r["ten_pm"] for r in _fetch(
        cur, """SELECT p.ten_pm FROM mon_thi_phan_mem r JOIN phan_mem p ON p.ma_pm = r.ma_pm
                WHERE r.ma_mon = %s AND r.ma_pm NOT IN
                      (SELECT ma_pm FROM phong_may_phan_mem WHERE ma_phong = %s)""",
        (ses["ma_mon"], room_code))]
    if missing:
        errors.append("Phòng thiếu phần mềm: " + ", ".join(missing))
    if _fetch(cur, """SELECT 1 AS x FROM lich_thi WHERE ma_pa = %s AND ma_phong = %s AND ma_khung = %s
                      AND ma_lich <> %s""", (ses["ma_pa"], room_code, ses["ma_khung"], ses["ma_lich"])):
        errors.append("Phòng đã có ca thi khác trong cùng khung giờ.")
    return errors


def _renumber(cur, ma_lich):
    """Đánh số máy lại 1..n (giữ nguyên thứ tự cũ) để không bị 'lủng' số."""
    regs = _fetch(cur, "SELECT ma_sv FROM dang_ky_thi WHERE ma_lich = %s ORDER BY so_may", (ma_lich,))
    cur.execute("UPDATE dang_ky_thi SET so_may = so_may + 10000 WHERE ma_lich = %s", (ma_lich,))  # tránh trùng UNIQUE
    cur.executemany("UPDATE dang_ky_thi SET so_may = %s WHERE ma_lich = %s AND ma_sv = %s",
                    [(i, ma_lich, r["ma_sv"]) for i, r in enumerate(regs, start=1)])


def _lock_session(cur, ma_lich):
    rows = _fetch(cur, "SELECT ma_lich, ma_pa, ma_mon, ma_khung FROM lich_thi WHERE ma_lich = %s FOR UPDATE",
                  (ma_lich,))
    return rows[0] if rows else None


def move_session(ma_lich: int, new_room: str):
    """Đổi phòng cho 1 ca thi. Số SV của ca không đổi (được tính từ dang_ky_thi), nhưng phải kiểm tra
    phòng mới và đánh số máy lại nếu số máy đang bị 'lủng'."""
    def work(cur):
        ses = _lock_session(cur, ma_lich)
        if not ses:
            return False, ["Ca thi không còn tồn tại."], None
        st = _fetch(cur, "SELECT COUNT(*) AS n, COALESCE(MAX(so_may), 0) AS mx FROM dang_ky_thi "
                         "WHERE ma_lich = %s FOR UPDATE", (ma_lich,))[0]
        errors = _room_errors(cur, ses, new_room, st["n"])
        if errors:
            return False, errors, None
        if st["mx"] != st["n"]:          # số máy không liên tục -> đánh số lại để vừa phòng mới
            _renumber(cur, ma_lich)
        cur.execute("UPDATE lich_thi SET ma_phong = %s WHERE ma_lich = %s", (new_room, ma_lich))
        return True, [f"Đã chuyển ca thi #{ma_lich} sang phòng {new_room}."], None
    return _tx(work)


def candidate_rooms(ma_lich: int, need: int) -> pd.DataFrame:
    """Phòng có thể nhận `need` sinh viên của ca: hoạt động, đủ máy, đủ phần mềm, rảnh trong khung giờ."""
    return _run_query("""
        SELECT r.ma_phong, r.suc_chua FROM phong_may r
        JOIN lich_thi s ON s.ma_lich = %s
        WHERE r.tinh_trang = 'Working' AND r.suc_chua >= %s
          AND NOT EXISTS (SELECT 1 FROM mon_thi_phan_mem q WHERE q.ma_mon = s.ma_mon AND NOT EXISTS
                (SELECT 1 FROM phong_may_phan_mem i WHERE i.ma_phong = r.ma_phong AND i.ma_pm = q.ma_pm))
          AND NOT EXISTS (SELECT 1 FROM lich_thi o WHERE o.ma_pa = s.ma_pa AND o.ma_khung = s.ma_khung
                          AND o.ma_phong = r.ma_phong)
        ORDER BY r.suc_chua, r.ma_phong""", (int(ma_lich), int(need)))


def split_session(ma_lich: int, k: int, new_room: str):
    """Tách ca: chuyển k sinh viên (những người có số máy cuối) sang một ca mới cùng môn, cùng khung giờ,
    ở phòng khác. Cả hai ca được đánh số máy lại; mọi bước nằm trong một giao dịch."""
    def work(cur):
        ses = _lock_session(cur, ma_lich)
        if not ses:
            return False, ["Ca thi không còn tồn tại."], None
        regs = _fetch(cur, "SELECT ma_sv FROM dang_ky_thi WHERE ma_lich = %s ORDER BY so_may FOR UPDATE", (ma_lich,))
        n = len(regs)
        if not 1 <= k <= n - 1:
            return False, [f"Số sinh viên chuyển phải từ 1 đến {n - 1}."], None
        errors = _room_errors(cur, ses, new_room, k)
        if errors:
            return False, errors, None
        cur.execute("INSERT INTO lich_thi (ma_pa, ma_mon, ma_phong, ma_khung) VALUES (%s, %s, %s, %s)",
                    (ses["ma_pa"], ses["ma_mon"], new_room, ses["ma_khung"]))
        new_id = cur.lastrowid
        cur.executemany("UPDATE dang_ky_thi SET ma_lich = %s, so_may = %s WHERE ma_lich = %s AND ma_sv = %s",
                        [(new_id, i, ma_lich, r["ma_sv"]) for i, r in enumerate(regs[n - k:], start=1)])
        left = _fetch(cur, "SELECT COALESCE(MAX(so_may), 0) AS mx FROM dang_ky_thi WHERE ma_lich = %s",
                      (ma_lich,))[0]["mx"]
        if left != n - k:
            _renumber(cur, ma_lich)
        return True, [f"Đã tách ca #{ma_lich}: {k} SV sang ca mới #{new_id} (phòng {new_room}), "
                      f"{n - k} SV ở lại."], new_id
    return _tx(work)


def clone_plan(src_pa: int):
    """Tạo bản nháp từ một phương án (sao chép ca thi + chỗ ngồi) để chỉnh sửa / lập lại lịch."""
    from datetime import datetime

    def work(cur):
        src = _fetch(cur, "SELECT ten_pa FROM phuong_an WHERE ma_pa = %s", (src_pa,))
        if not src:
            return False, ["Phương án nguồn không tồn tại."], None
        cur.execute("INSERT INTO phuong_an (ten_pa, trang_thai, ghi_chu) VALUES (%s, 'NHAP', %s)",
                    (f"Bản nháp từ #{src_pa} ({datetime.now():%d/%m %H:%M})", f"Sao chép từ phương án #{src_pa}"))
        new_pa = cur.lastrowid
        cur.execute("INSERT INTO lich_thi (ma_pa, ma_mon, ma_phong, ma_khung) "
                    "SELECT %s, ma_mon, ma_phong, ma_khung FROM lich_thi WHERE ma_pa = %s", (new_pa, src_pa))
        cur.execute("""INSERT INTO dang_ky_thi (ma_sv, ma_lich, so_may, diem)
                       SELECT dk.ma_sv, nl.ma_lich, dk.so_may, dk.diem
                       FROM dang_ky_thi dk
                       JOIN lich_thi ol ON ol.ma_lich = dk.ma_lich AND ol.ma_pa = %s
                       JOIN lich_thi nl ON nl.ma_pa = %s AND nl.ma_phong = ol.ma_phong AND nl.ma_khung = ol.ma_khung""",
                    (src_pa, new_pa))
        return True, [f"Đã tạo bản nháp #{new_pa} từ phương án #{src_pa}."], new_pa
    return _tx(work)


def set_plan_status(ma_pa: int, new_status: str, allowed_from, need_clean: bool = False):
    """Chuyển trạng thái phương án (có kiểm tra trạng thái hiện tại và, nếu cần, không còn vi phạm)."""
    def work(cur):
        row = _fetch(cur, "SELECT trang_thai FROM phuong_an WHERE ma_pa = %s FOR UPDATE", (ma_pa,))
        if not row:
            return False, ["Phương án không tồn tại."], None
        cur_status = row[0]["trang_thai"]
        if cur_status not in allowed_from:
            return False, [f"Phương án đang ở trạng thái '{PLAN_LABEL[cur_status]}', "
                           f"không thể chuyển sang '{PLAN_LABEL[new_status]}'."], None
        if need_clean:
            n = _fetch(cur, "SELECT COUNT(*) AS n FROM v_vi_pham WHERE ma_pa = %s", (ma_pa,))[0]["n"]
            if n:
                return False, [f"Còn {n} vi phạm ràng buộc. Hãy xử lý trước khi chuyển trạng thái."], None
        if new_status == "DA_CONG_BO":      # chỉ một phương án được công bố: lưu trữ bản cũ
            cur.execute("UPDATE phuong_an SET trang_thai = 'LUU_TRU' WHERE trang_thai = 'DA_CONG_BO' AND ma_pa <> %s",
                        (ma_pa,))
        cur.execute("UPDATE phuong_an SET trang_thai = %s WHERE ma_pa = %s", (new_status, ma_pa))
        return True, [f"Phương án #{ma_pa}: '{PLAN_LABEL[cur_status]}' → '{PLAN_LABEL[new_status]}'."], None
    return _tx(work)



# ==============================================================================
# QUẢN LÝ TÀI KHOẢN MẪU (MOCK USERS DATABASE)
# ==============================================================================
ACCOUNTS = {
    "giaovu": {
        "password": "123",
        "name": "Nguyễn Thị Mai",
        "role": "Giáo vụ (Quản lý đào tạo)",
        "dept": "Phòng Đào tạo",
        "email": "ntmai@university.edu.vn"
    },
    "giamthi": {
        "password": "123",
        "name": "TS. Nguyễn Văn A",
        "role": "Giám thị (Cán bộ coi thi)",
        "dept": "Khoa Công nghệ thông tin",
        "email": "nva@university.edu.vn"
    },
    "sinhvien": {
        "password": "123",
        "name": "Sinh viên (demo)",
        "role": "Sinh viên",
        "dept": "Tra cứu theo MSSV trong CSDL",
        "email": "an.nv210001@sis.edu.vn"
    },
    "admin": {
        "password": "123",
        "name": "Đỗ Quang Minh",
        "role": "Quản trị viên (IT Helpdesk)",
        "dept": "Trung tâm Mạng & Máy tính",
        "email": "minhdq@university.edu.vn"
    }
}

# Khởi tạo session state cho đăng nhập
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "current_user" not in st.session_state:
    st.session_state["current_user"] = None

def login_user(username):
    if username in ACCOUNTS:
        st.session_state["logged_in"] = True
        st.session_state["current_user"] = {
            "username": username,
            **ACCOUNTS[username]
        }
        st.rerun()

def logout_user():
    st.session_state["logged_in"] = False
    st.session_state["current_user"] = None
    st.rerun()

# ==============================================================================
# MÀN HÌNH ĐĂNG NHẬP (KHI CHƯA XÁC THỰC)
# ==============================================================================
if not st.session_state["logged_in"]:
    col_l, col_center, col_r = st.columns([1, 2, 1])
    
    with col_center:
        st.write("")
        st.write("")
        st.markdown("<h2 style='text-align: center;'>📅 Exam Scheduler</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #64748B;'>Hệ thống xếp lịch thi và phòng máy học phần</p>", unsafe_allow_html=True)
        st.divider()
        
        with st.container():
            st.subheader("🔐 Đăng nhập hệ thống")
            st.caption("Nhập thông tin xác thực để truy cập theo thẩm quyền phân công")
            
            with st.form("login_form"):
                uname_input = st.text_input("Tên đăng nhập / Mã số", placeholder="giaovu / giamthi / sinhvien / admin")
                pwd_input = st.text_input("Mật khẩu", type="password", placeholder="Mật khẩu (mẫu: 123)")
                login_btn = st.form_submit_button("Đăng nhập", type="primary", use_container_width=True)
                
                if login_btn:
                    if uname_input in ACCOUNTS and ACCOUNTS[uname_input]["password"] == pwd_input:
                        login_user(uname_input)
                    else:
                        st.error("❌ Sai tài khoản hoặc mật khẩu! (Mật khẩu mặc định: 123)")
            
            st.write("")
            st.markdown("#### ⚡ Hoặc chọn nhanh tài khoản Demo:")
            st.caption("Bấm một chạm để vào ngay với vai trò tương ứng mà không cần gõ:")
            
            c_d1, c_d2 = st.columns(2)
            with c_d1:
                if st.button("🎓 Đăng nhập: Giáo vụ", use_container_width=True):
                    login_user("giaovu")
                if st.button("👨‍🏫 Đăng nhập: Giám thị", use_container_width=True):
                    login_user("giamthi")
            with c_d2:
                if st.button("👨‍🎓 Đăng nhập: Sinh viên", use_container_width=True):
                    login_user("sinhvien")
                if st.button("🛠️ Đăng nhập: Quản trị viên IT", use_container_width=True):
                    login_user("admin")

# ==============================================================================
# GIAO DIỆN CHÍNH (KHI ĐÃ ĐĂNG NHẬP THÀNH CÔNG)
# ==============================================================================
else:
    user = st.session_state["current_user"]
    user_role = user["role"]

    # -------------------------------------------------------------------------
    # SIDEBAR: THÔNG TIN TÀI KHOẢN & PHÂN QUYỀN
    # -------------------------------------------------------------------------
    with st.sidebar:
        st.markdown("### 📅 **Exam Scheduler**")
        st.caption("Hệ thống xếp lịch thi & phòng máy")
        st.divider()

        st.markdown(f"""
        <div class="user-profile-box">
            <div style="font-weight: 700; font-size: 15px; color: #1E293B;">👤 {user['name']}</div>
            <div style="font-size: 13px; color: #64748B;">{user['dept']}</div>
            <div style="margin-top: 8px;"><span class="role-badge">{user_role}</span></div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("🚪 Đăng xuất", use_container_width=True):
            logout_user()

        if st.button("🔄 Làm mới dữ liệu", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        st.divider()

        if user_role == "Giáo vụ (Quản lý đào tạo)":
            menu_items = [
                "📊 Tổng quan điều hành",
                "📁 Quản lý dữ liệu",
                "⚙️ Thiết lập ràng buộc (ILP/CSP)",
                "🧩 Xếp lịch tự động & Xử lý ngoại lệ",
                "👁️ Xem & Điều chỉnh lịch",
                "📢 Duyệt & Công bố lịch",
                "📈 Báo cáo sử dụng phòng"
            ]
        elif user_role == "Giám thị (Cán bộ coi thi)":
            menu_items = [
                "📋 Lịch coi thi cá nhân",
                "👥 Danh sách sinh viên phòng thi",
                "⚠️ Báo cáo sự cố phòng thi/máy"
            ]
        elif user_role == "Sinh viên":
            menu_items = [
                "🔍 Tra cứu lịch thi cá nhân",
                "🖥️ Tra cứu yêu cầu phòng máy"
            ]
        else:  # Quản trị viên IT
            menu_items = [
                "🎛️ Tham số bộ giải ILP/CSP",
                "👥 Quản lý tài khoản & Phân quyền",
                "🛠️ Giám sát & Hỗ trợ kỹ thuật"
            ]

        selected_page = st.radio("Chức năng của bạn", menu_items)

        st.divider()
        st.caption(f"Đăng nhập với ID: `{user['username']}`")

    # -------------------------------------------------------------------------
    # KIỂM TRA KẾT NỐI CSDL (hiển thị lỗi rõ ràng thay vì crash)
    # -------------------------------------------------------------------------
    _ok, _err = db_ping()
    if not _ok:
        st.error("❌ Không đọc được CSDL `quan_ly_thi`.")
        st.code(_err)
        st.caption("Kiểm tra: (1) MySQL đang chạy, (2) đã chạy `01_schema.sql`, "
                   "(3) `src/backend/db_helper.py` cấu hình đúng.")
        st.stop()

    EMPTY_MSG = ("Chưa có dữ liệu. Giáo vụ vào **📁 Quản lý dữ liệu → 🧪 Sinh dữ liệu mẫu** "
                 "(hoặc chạy `python generate_data.py`).")
    NO_PUBLISHED_MSG = ("Chưa có lịch thi nào được công bố. Giáo vụ cần phê duyệt và công bố một phương án "
                        "(📢 Duyệt & Công bố lịch).")

    # Kết quả của thao tác trước (sau st.rerun) được hiển thị ở đầu trang
    if "flash" in st.session_state:
        _kind, _msg = st.session_state.pop("flash")
        getattr(st, _kind)(_msg)

    # Phương án đang làm việc (chỉ Giáo vụ); các vai trò khác chỉ thấy phương án ĐÃ CÔNG BỐ
    PA, PA_STATUS = None, None
    if user_role == "Giáo vụ (Quản lý đào tạo)":
        PLANS = load_plans()
        plan_ids = PLANS["ma_pa"].astype(int).tolist()
        if "pending_pa" in st.session_state:            # chọn sẵn phương án vừa tạo/sinh
            st.session_state["sel_pa"] = st.session_state.pop("pending_pa")
        if st.session_state.get("sel_pa") not in plan_ids:
            st.session_state.pop("sel_pa", None)
        with st.sidebar:
            if not plan_ids:
                st.caption("Chưa có phương án nào.")
            else:
                plan_info = {int(r.ma_pa): r for r in PLANS.itertuples()}
                PA = st.selectbox("📂 Phương án đang làm việc", plan_ids, key="sel_pa",
                                  format_func=lambda i: f"#{i} · {PLAN_LABEL[plan_info[i].trang_thai]} · {plan_info[i].so_ca} ca")
                PA_STATUS = plan_info[PA].trang_thai

    def render_clone_button(src_pa, key):
        if st.button("📝 Tạo bản nháp từ phương án này", key=key):
            ok, msgs, new_id = clone_plan(int(src_pa))
            if ok:
                st.cache_data.clear()
                st.session_state["pending_pa"] = new_id
                st.session_state["flash"] = ("success", msgs[0])
                st.rerun()
            else:
                for m in msgs:
                    st.error(m)

    # -------------------------------------------------------------------------
    # KHÔNG GIAN LÀM VIỆC THEO VAI TRÒ
    # -------------------------------------------------------------------------

    # 1. GIÁO VỤ (QUẢN LÝ ĐÀO TẠO)
    if user_role == "Giáo vụ (Quản lý đào tạo)":
        if selected_page == "📊 Tổng quan điều hành":
            st.title("📊 Tổng quan điều hành kỳ thi")
            st.caption(f"Xin chào **{user['name']}** - Phòng Đào tạo")
            if PA is None:
                st.info(EMPTY_MSG)
            else:
                st.caption(f"Phương án **#{PA}** · trạng thái: **{PLAN_LABEL[PA_STATUS]}**")
                ov = load_overview(PA)
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Tổng học phần thi", f"{int(ov['mon'])} môn", f"{int(ov['sv'])} sinh viên", delta_color="off")
                c2.metric("Phòng máy khả dụng", f"{int(ov['phong_ok'])} / {int(ov['phong'])} phòng",
                          f"{int(ov['phong'] - ov['phong_ok'])} phòng bảo trì", delta_color="off")
                c3.metric("Ca thi đã xếp", f"{int(ov['lich'])} ca", f"{int(ov['khung'])} khung giờ", delta_color="off")
                c4.metric("Lượt đăng ký thi", f"{int(ov['dk'])}", "Đã xếp chỗ ngồi", delta_color="off")

                if int(ov["lich"]) == 0:
                    st.info("Phương án này chưa có ca thi nào.")
                else:
                    st.markdown("---")
                    col_left, col_right = st.columns([2, 1])
                    with col_left:
                        st.subheader("Lượt thi theo ngày")
                        per_day = query_df("""
                            SELECT CAST(kg.ngay_thi AS CHAR) AS ngay_iso, COUNT(*) AS luot_thi
                            FROM dang_ky_thi dk
                            JOIN lich_thi lt ON lt.ma_lich = dk.ma_lich
                            JOIN khung_gio kg ON kg.ma_khung = lt.ma_khung
                            WHERE lt.ma_pa = %s
                            GROUP BY kg.ngay_thi ORDER BY kg.ngay_thi""", (PA,))
                        per_day["Ngày"] = pd.to_datetime(per_day["ngay_iso"]).dt.strftime("%d/%m")
                        st.bar_chart(per_day.set_index("Ngày")["luot_thi"])
                    with col_right:
                        st.subheader("Cảnh báo nhanh")
                        maint = query_df("SELECT ma_phong FROM phong_may WHERE tinh_trang <> 'Working' ORDER BY ma_phong")
                        if len(maint):
                            st.warning(f"⚠️ {len(maint)} phòng đang bảo trì: " + ", ".join(maint["ma_phong"].head(8))
                                       + ("…" if len(maint) > 8 else ""))
                        else:
                            st.success("✅ Tất cả phòng máy đang hoạt động.")
                        viol = load_violations(PA)
                        if viol.empty:
                            st.success("✅ Phương án không vi phạm ràng buộc cứng nào.")
                        else:
                            summary = ", ".join(f"{LOAI_LABEL[k]} ×{v}" for k, v in viol["loai"].value_counts().items())
                            st.error(f"❌ {len(viol)} vi phạm: {summary}")

        elif selected_page == "📁 Quản lý dữ liệu":
            st.title("📁 Quản lý dữ liệu gốc")
            st.caption("Dữ liệu đọc trực tiếp từ CSDL `quan_ly_thi`")
            t1, t2, t3, t4, t5, t6 = st.tabs(["📘 Học phần", "🏫 Phòng máy", "🎓 Sinh viên",
                                              "🕒 Khung giờ", "🧪 Sinh dữ liệu mẫu", "📥 Nhập dữ liệu (Excel/CSV)"])
            with t1:
                st.subheader("Danh mục học phần")
                hp_df = query_df(f"""
                    SELECT mt.ma_mon, mt.ten_mon, mt.so_tin_chi, mt.thoi_luong_phut, mt.hinh_thuc,
                           COALESCE((SELECT {SW_LIST} FROM mon_thi_phan_mem r
                                     JOIN phan_mem p ON p.ma_pm = r.ma_pm WHERE r.ma_mon = mt.ma_mon), 'Không') AS phan_mem,
                           (SELECT COUNT(*) FROM lich_thi lt JOIN dang_ky_thi dk ON dk.ma_lich = lt.ma_lich
                            WHERE lt.ma_mon = mt.ma_mon AND lt.ma_pa = %s) AS so_sv
                    FROM mon_thi mt ORDER BY mt.ma_mon""", (PA,))
                if hp_df.empty:
                    st.info(EMPTY_MSG)
                else:
                    st.dataframe(hp_df.rename(columns={
                        "ma_mon": "Mã HP", "ten_mon": "Tên học phần", "so_tin_chi": "Tín chỉ",
                        "thoi_luong_phut": "Thời lượng (phút)", "hinh_thuc": "Hình thức thi",
                        "phan_mem": "Yêu cầu phần mềm", "so_sv": "Số SV"}),
                        use_container_width=True, hide_index=True)
            with t2:
                st.subheader("Danh mục phòng máy & cấu hình")
                room_df = query_df(f"""
                    SELECT pm.ma_phong, pm.toa_nha, pm.tang, pm.suc_chua, pm.he_dieu_hanh, pm.tinh_trang,
                           (SELECT {SW_LIST} FROM phong_may_phan_mem l JOIN phan_mem p ON p.ma_pm = l.ma_pm
                            WHERE l.ma_phong = pm.ma_phong) AS phan_mem,
                           (SELECT COUNT(*) FROM lich_thi lt WHERE lt.ma_phong = pm.ma_phong AND lt.ma_pa = %s) AS so_ca
                    FROM phong_may pm ORDER BY pm.ma_phong""", (PA,))
                if room_df.empty:
                    st.info(EMPTY_MSG)
                else:
                    only_ok = st.checkbox("Chỉ hiện phòng đang hoạt động", value=False)
                    if only_ok:
                        room_df = room_df[room_df["tinh_trang"] == "Working"]
                    st.dataframe(room_df.rename(columns={
                        "ma_phong": "Phòng", "toa_nha": "Tòa", "tang": "Tầng", "suc_chua": "Số máy",
                        "he_dieu_hanh": "Hệ điều hành", "tinh_trang": "Tình trạng",
                        "phan_mem": "Phần mềm cài đặt", "so_ca": "Số ca thi (PA đang chọn)"}),
                        use_container_width=True, hide_index=True)
            with t3:
                st.subheader("Danh sách sinh viên")
                sv_df = query_df("""SELECT ma_sv, ho_ten, CAST(ngay_sinh AS CHAR) AS ngay_sinh, gioi_tinh,
                                           email, so_dien_thoai, lop, khoa, khoa_hoc
                                    FROM sinh_vien ORDER BY ma_sv""")
                if sv_df.empty:
                    st.info(EMPTY_MSG)
                else:
                    f1, f2 = st.columns([2, 1])
                    kw = f1.text_input("Tìm theo MSSV / họ tên / lớp", placeholder="VD: SV2023, Nguyễn, D23CNTT01")
                    khoa = f2.selectbox("Khoa", ["Tất cả"] + sorted(sv_df["khoa"].unique()))
                    view = sv_df
                    if kw:
                        mask = (view["ma_sv"].str.contains(kw, case=False, regex=False)
                                | view["ho_ten"].str.contains(kw, case=False, regex=False)
                                | view["lop"].str.contains(kw, case=False, regex=False))
                        view = view[mask]
                    if khoa != "Tất cả":
                        view = view[view["khoa"] == khoa]
                    st.caption(f"{len(view)} / {len(sv_df)} sinh viên (hiển thị tối đa 1000 dòng)")
                    st.dataframe(view.head(1000).rename(columns={
                        "ma_sv": "MSSV", "ho_ten": "Họ tên", "ngay_sinh": "Ngày sinh", "gioi_tinh": "Giới tính",
                        "email": "Email", "so_dien_thoai": "SĐT", "lop": "Lớp", "khoa": "Khoa",
                        "khoa_hoc": "Khóa"}), use_container_width=True, hide_index=True)
            with t4:
                st.subheader("Khung giờ thi")
                st.caption("Schema hiện chưa có bảng giám thị, nên mục này chỉ hiển thị khung giờ.")
                kg_df = query_df(f"""
                    SELECT kg.ma_khung, {SLOT_SQL},
                           (SELECT COUNT(*) FROM lich_thi lt WHERE lt.ma_khung = kg.ma_khung AND lt.ma_pa = %s) AS so_phong
                    FROM khung_gio kg ORDER BY kg.ngay_thi, kg.ca_thi""", (PA,))
                if kg_df.empty:
                    st.info(EMPTY_MSG)
                else:
                    kg_df["Ngày thi"] = fmt_dates(kg_df["ngay_iso"])
                    st.dataframe(kg_df[["ma_khung", "Ngày thi", "ca_thi", "gio_bd", "gio_kt", "so_phong"]].rename(columns={
                        "ma_khung": "Mã khung", "ca_thi": "Ca", "gio_bd": "Bắt đầu", "gio_kt": "Kết thúc",
                        "so_phong": "Số phòng đang dùng (PA đang chọn)"}), use_container_width=True, hide_index=True)
            with t5:
                st.subheader("Sinh dữ liệu mẫu vào CSDL")
                st.caption("Gọi `generate_all()` trong `generate_data.py`. Dữ liệu cũ (kể cả phương án đã công bố) được thay thế trong **một giao dịch** "
                           "(lỗi giữa chừng sẽ rollback, dữ liệu cũ không bị mất).")
                if "gen_summary" in st.session_state:
                    s = st.session_state.pop("gen_summary")
                    st.success(f"✅ Đã sinh: {s['students']} sinh viên, {s['subjects']} môn, {s['rooms']} phòng "
                               f"({s['rooms_maintenance']} bảo trì), {s['slots']} khung giờ, {s['sessions']} ca thi, "
                               f"{s['registrations']} lượt đăng ký.")
                    if s["unscheduled"]:
                        st.warning(f"{s['unscheduled']} lượt đăng ký chưa xếp được — tăng số phòng hoặc số ngày thi.")
                    sv = s.get("solver", {})
                    detail = f"Thuật toán đã dùng: **{sv.get('algorithm', '?')}**"
                    if "solver_status" in sv:
                        detail += (f" · bộ giải {sv['solver_status']} sau {sv['solve_time']}s · "
                                   f"{sv['rooms_opened']} phòng được mở")
                    if sv.get("repaired"):
                        detail += f" · tham lam xếp bù {sv['repaired']} lượt đăng ký"
                    st.info(detail)
                    for key in ("warning", "note"):
                        if sv.get(key):
                            st.warning(sv[key])
                with st.form("gen_form"):
                    g1, g2 = st.columns(2)
                    n_sv = g1.number_input("Số sinh viên", 10, 20000, 300, step=50)
                    n_mon = g2.number_input("Số môn thi (tối đa 22)", 1, 22, 12)
                    n_phong = g1.number_input("Số phòng máy", 3, 500, 10)
                    n_ngay = g2.number_input("Số ngày thi", 1, 30, 5)
                    a1, a2 = st.columns(2)
                    algo_label = a1.selectbox("Thuật toán xếp lịch", list(ALGO_OPTIONS))
                    time_limit = a2.number_input("Giới hạn thời gian bộ giải (giây)", 5, 600, 30)
                    seed_txt = st.text_input("Seed (để trống = ngẫu nhiên)", value="")
                    repro = st.checkbox("Tái lập theo seed (bộ giải chạy 1 luồng: chậm hơn, kết quả kém tối ưu hơn)")
                    publish = st.checkbox("Công bố ngay phương án mẫu (để Sinh viên/Giám thị tra cứu được)", value=True)
                    confirm = st.checkbox("Tôi hiểu thao tác này sẽ XÓA toàn bộ dữ liệu hiện có và thay bằng dữ liệu mới")
                    go = st.form_submit_button("🧪 Sinh dữ liệu", type="primary")
                if go:
                    gen = load_generator()
                    if not confirm:
                        st.warning("Hãy tick ô xác nhận trước khi sinh dữ liệu.")
                    elif gen is None:
                        st.error("Không tìm thấy `generate_data.py` (đặt cùng thư mục với app.py, ở thư mục gốc "
                                 "dự án hoặc trong một thư mục con trực tiếp của nó).")
                    elif seed_txt.strip() and not seed_txt.strip().lstrip("-").isdigit():
                        st.error("Seed phải là số nguyên.")
                    else:
                        conn = get_master_connection()
                        try:
                            with st.spinner(f"Đang sinh dữ liệu và xếp lịch (bộ giải chạy tối đa {int(time_limit)} giây)..."):
                                summary = gen.generate_all(
                                    conn, int(n_sv), int(n_mon), int(n_phong), int(n_ngay),
                                    seed=int(seed_txt) if seed_txt.strip() else None, log=lambda *_: None,
                                    publish=publish, algorithm=ALGO_OPTIONS[algo_label],
                                    time_limit=int(time_limit), workers=1 if repro else None)
                        except Exception as exc:  # noqa: BLE001
                            st.error(f"Sinh dữ liệu thất bại (đã rollback): {exc}")
                        else:
                            st.session_state["gen_summary"] = summary
                            st.session_state["pending_pa"] = summary["ma_pa"]
                            st.cache_data.clear()
                            st.rerun()   # các tab/trang khác hiển thị dữ liệu mới ngay lập tức
                        finally:
                            conn.close()
            with t6:
                st.subheader("Nạp dữ liệu hàng loạt từ Excel / CSV")
                st.file_uploader("Kéo thả file dữ liệu tại đây", type=["xlsx", "csv"])

        elif selected_page == "⚙️ Thiết lập ràng buộc (ILP/CSP)":
            st.title("⚙️ Cấu hình ràng buộc & Mục tiêu tối ưu")
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("🔒 Ràng buộc cứng (Bắt buộc)")
                st.checkbox("Sinh viên không trùng 2 môn cùng thời điểm", value=True, disabled=True)
                st.checkbox("Số sinh viên không vượt quá số máy phòng", value=True, disabled=True)
                st.checkbox("Phòng máy đáp ứng phần mềm của học phần", value=True, disabled=True)
                st.checkbox("Mỗi phòng chỉ có 1 ca thi trong 1 khung giờ", value=True, disabled=True)
            with col2:
                st.subheader("🎯 Mục tiêu mềm (Ưu tiên tối ưu)")
                st.slider("Khoảng cách tối thiểu giữa 2 môn của SV (ngày)", 1, 5, 2)
                st.slider("Độ ưu tiên cân bằng số ca thi giữa các phòng", 1, 10, 8)
                st.slider("Tối ưu tỷ lệ lấp đầy phòng máy để tiết kiệm điện", 1, 10, 7)
            st.button("💾 Lưu cấu hình ràng buộc", type="primary")

        elif selected_page == "🧩 Xếp lịch tự động & Xử lý ngoại lệ":
            st.title("🧩 Chạy bộ giải thuật xếp lịch tự động")
            c_mode, c_btn = st.columns([3, 1])
            with c_mode:
                st.selectbox("Mô hình giải thuật", ["ILP (Quy hoạch nguyên tuyến tính)", "CSP (Thỏa mãn ràng buộc)"])
            with c_btn:
                st.write("")
                st.write("")
                if st.button("🚀 Bắt đầu xếp lịch", type="primary", use_container_width=True):
                    st.success("Bộ giải đã tìm thấy phương án tối ưu trong 3.8s!")

            st.subheader("⚠️ Xử lý ngoại lệ khi vô nghiệm / thiếu tài nguyên")
            st.markdown("*Kích hoạt khi bài toán không thể thỏa mãn đồng thời các ràng buộc cứng:*")
            with st.expander("🛠️ Trợ lý xử lý ngoại lệ (Gợi ý phương án khắc phục)"):
                st.write("1. ➕ **Mở thêm ca thi:** Tăng thêm ca thi ngày Thứ Bảy.")
                st.write("2. 🔄 **Chia nhỏ ca thi:** Chia lớp thực hành 60 sinh viên thành 2 ca liên tiếp.")
                st.write("3. ⚡ **Nới lỏng ràng buộc mềm:** Giảm khoảng cách giãn cách môn từ 2 ngày xuống 1 ngày.")
                st.button("Áp dụng gợi ý tự động")

        elif selected_page == "👁️ Xem & Điều chỉnh lịch":
            st.title("👁️ Xem & Điều chỉnh lịch thi")
            ses = load_sessions(PA) if PA is not None else pd.DataFrame()
            if PA is None:
                st.info(EMPTY_MSG)
            elif ses.empty:
                st.caption(f"Phương án **#{PA}** · **{PLAN_LABEL[PA_STATUS]}**")
                st.info("Phương án này chưa có ca thi nào.")
            else:
                st.caption(f"Phương án **#{PA}** · **{PLAN_LABEL[PA_STATUS]}**")
                viol = load_violations(PA)
                m1, m2 = st.columns(2)
                m1.metric("Số ca thi", len(ses))
                m2.metric("Vi phạm ràng buộc cứng", len(viol), "Hợp lệ" if viol.empty else "Cần xử lý", delta_color="off")
                if not viol.empty:
                    with st.expander(f"Chi tiết {len(viol)} vi phạm", expanded=True):
                        vv = viol.copy()
                        vv["loai"] = vv["loai"].map(LOAI_LABEL)
                        st.dataframe(vv.rename(columns={"ma_lich": "Mã ca", "loai": "Loại vi phạm", "chi_tiet": "Chi tiết"}),
                                     use_container_width=True, hide_index=True)
                bad = set(viol["ma_lich"].astype(int))

                ses["Ngày thi"] = fmt_dates(ses["ngay_iso"])
                ses["Ca thi"] = slot_labels(ses)
                ses["Học phần"] = ses["ten_mon"] + " (" + ses["ma_mon"] + ")"
                ses["Phòng thi"] = ses["ma_phong"] + " (" + ses["suc_chua"].astype(str) + " máy)"
                ses["Trạng thái"] = ["❌ Vi phạm" if int(m) in bad else "✅ Hợp lệ" for m in ses["ma_lich"]]

                f1, f2 = st.columns(2)
                day = f1.selectbox("Lọc theo ngày", ["Tất cả"] + list(dict.fromkeys(ses["Ngày thi"])))
                mon = f2.selectbox("Lọc theo học phần", ["Tất cả"] + sorted(ses["Học phần"].unique()))
                view = ses
                if day != "Tất cả":
                    view = view[view["Ngày thi"] == day]
                if mon != "Tất cả":
                    view = view[view["Học phần"] == mon]
                st.caption(f"{len(view)} / {len(ses)} ca thi")
                st.dataframe(view[["ma_lich", "Ngày thi", "Ca thi", "Học phần", "Phòng thi", "so_sv", "Trạng thái"]]
                             .rename(columns={"ma_lich": "Mã ca", "so_sv": "Số SV"}),
                             use_container_width=True, hide_index=True)

                st.subheader("Điều chỉnh thủ công (Fine-tuning)")
                if PA_STATUS != "NHAP":
                    st.info(f"🔒 Phương án đang ở trạng thái **{PLAN_LABEL[PA_STATUS]}** nên bị khóa chỉnh sửa "
                            "(DB chặn bằng trigger). Hãy tạo bản nháp để điều chỉnh / lập lại lịch.")
                    render_clone_button(PA, "clone_adjust")
                else:
                    labels = {int(r["ma_lich"]): f"#{r['ma_lich']} · {r['Ngày thi']} {r['Ca thi'].split(' (')[0]} · {r['ma_mon']} · {r['ma_phong']}"
                              for _, r in ses.iterrows()}
                    tab_move, tab_split = st.tabs(["🔁 Đổi phòng", "✂️ Tách ca"])
                    with tab_move:
                        st.caption("Số SV của ca không đổi (được đếm từ đăng ký). Hệ thống kiểm tra phòng hoạt động, đủ máy, "
                                   "đủ phần mềm, không trùng khung giờ, và đánh số máy lại nếu cần.")
                        c1, c2, c3 = st.columns([3, 2, 2])
                        pick = c1.selectbox("Chọn ca thi đổi phòng", list(labels), format_func=labels.get)
                        rooms = query_df("SELECT ma_phong FROM phong_may WHERE tinh_trang = 'Working' ORDER BY ma_phong")["ma_phong"].tolist()
                        cur_room = ses.loc[ses["ma_lich"] == pick, "ma_phong"].iloc[0]
                        new_room = c2.selectbox("Chuyển sang phòng", [r for r in rooms if r != cur_room])
                        c3.write("")
                        c3.write("")
                        if c3.button("Kiểm tra xung đột & Cập nhật", use_container_width=True):
                            ok, msgs, _ = move_session(int(pick), new_room)
                            if ok:
                                st.cache_data.clear()
                                st.session_state["flash"] = ("success", msgs[0])
                                st.rerun()
                            else:
                                for m in msgs:
                                    st.error(m)
                    with tab_split:
                        st.caption("Dùng khi phòng mới nhỏ hơn số SV: chuyển bớt SV sang một ca mới (cùng môn, cùng khung giờ) ở phòng khác.")
                        multi = ses[ses["so_sv"] >= 2]
                        if multi.empty:
                            st.info("Không có ca nào đủ 2 sinh viên để tách.")
                        else:
                            split_labels = {int(r["ma_lich"]): f"{labels[int(r['ma_lich'])]} · {r['so_sv']} SV" for _, r in multi.iterrows()}
                            sp = st.selectbox("Chọn ca thi cần tách", list(split_labels), format_func=split_labels.get, key="split_pick")
                            n_sv = int(multi.loc[multi["ma_lich"] == sp, "so_sv"].iloc[0])
                            k = int(st.number_input("Số sinh viên chuyển sang ca mới", 1, n_sv - 1, max(1, n_sv // 2),
                                                    key=f"split_k_{sp}"))
                            cand = candidate_rooms(sp, k)
                            if cand.empty:
                                st.warning(f"Không có phòng nào nhận được {k} SV (cần hoạt động, đủ máy, đủ phần mềm, rảnh khung giờ).")
                            else:
                                room_lbl = {r.ma_phong: f"{r.ma_phong} ({r.suc_chua} máy)" for r in cand.itertuples()}
                                new_room = st.selectbox("Phòng cho ca mới", list(room_lbl), format_func=room_lbl.get,
                                                        key=f"split_room_{sp}_{k}")
                                if st.button("✂️ Tách ca", type="primary"):
                                    ok, msgs, _ = split_session(int(sp), k, new_room)
                                    if ok:
                                        st.cache_data.clear()
                                        st.session_state["flash"] = ("success", msgs[0])
                                        st.rerun()
                                    else:
                                        for m in msgs:
                                            st.error(m)

        elif selected_page == "📢 Duyệt & Công bố lịch":
            st.title("📢 Phê duyệt & Công bố lịch thi")
            st.caption("Vòng đời: Nháp → Chờ duyệt → Đã duyệt → Đã công bố → Lưu trữ. Chỉ một phương án được công bố.")
            plans_view = load_plans()
            if plans_view.empty or PA is None:
                st.info(EMPTY_MSG)
            else:
                pv = plans_view.copy()
                pv["trang_thai"] = pv["trang_thai"].map(PLAN_LABEL)
                st.dataframe(pv.rename(columns={"ma_pa": "Mã PA", "ten_pa": "Tên phương án", "trang_thai": "Trạng thái",
                                                "tao_luc": "Tạo lúc", "ghi_chu": "Ghi chú", "so_ca": "Số ca"}),
                             use_container_width=True, hide_index=True)
                viol = load_violations(PA)
                st.info(f"Phương án đang chọn: **#{PA}** · trạng thái **{PLAN_LABEL[PA_STATUS]}** · "
                        f"{'không có vi phạm' if viol.empty else str(len(viol)) + ' vi phạm ràng buộc'}")

                def move_status(new, frm, clean=False):
                    ok, msgs, _ = set_plan_status(int(PA), new, frm, clean)
                    if ok:
                        st.cache_data.clear()
                        st.session_state["flash"] = ("success", msgs[0])
                        st.rerun()
                    else:
                        for m in msgs:
                            st.error(m)

                if PA_STATUS == "NHAP":
                    if st.button("📨 Gửi duyệt", type="primary"):
                        move_status("CHO_DUYET", ["NHAP"], clean=True)
                elif PA_STATUS == "CHO_DUYET":
                    a1, a2 = st.columns(2)
                    if a1.button("✅ Phê duyệt phương án", type="primary", use_container_width=True):
                        move_status("DA_DUYET", ["CHO_DUYET"])
                    if a2.button("↩️ Trả về nháp", use_container_width=True):
                        move_status("NHAP", ["CHO_DUYET", "DA_DUYET"])
                elif PA_STATUS == "DA_DUYET":
                    a1, a2 = st.columns(2)
                    if a1.button("📢 Phát hành & Công bố cho SV/Giám thị", type="primary", use_container_width=True):
                        move_status("DA_CONG_BO", ["DA_DUYET"], clean=True)
                    if a2.button("↩️ Trả về nháp", use_container_width=True):
                        move_status("NHAP", ["CHO_DUYET", "DA_DUYET"])
                elif PA_STATUS == "DA_CONG_BO":
                    st.success("Đây là lịch thi chính thức: Sinh viên và Giám thị đang xem phương án này.")
                    render_clone_button(PA, "clone_publish")
                else:
                    st.caption("Phương án đã lưu trữ (đã bị thay bằng phương án công bố mới).")
                    render_clone_button(PA, "clone_archive")

        elif selected_page == "📈 Báo cáo sử dụng phòng":
            st.title("📈 Báo cáo & Thống kê sử dụng phòng máy")
            if PA is not None:
                st.caption(f"Phương án **#{PA}** · {PLAN_LABEL[PA_STATUS]}")
            use = query_df("""
                SELECT pm.ma_phong, pm.suc_chua, pm.tinh_trang,
                       COUNT(lt.ma_lich) AS so_ca, COALESCE(SUM(x.n), 0) AS tong_sv
                FROM phong_may pm
                LEFT JOIN lich_thi lt ON lt.ma_phong = pm.ma_phong AND lt.ma_pa = %s
                LEFT JOIN (SELECT ma_lich, COUNT(*) AS n FROM dang_ky_thi GROUP BY ma_lich) x ON x.ma_lich = lt.ma_lich
                GROUP BY pm.ma_phong, pm.suc_chua, pm.tinh_trang ORDER BY pm.ma_phong""", (PA,))
            ov = load_overview(PA)
            if PA is None or use.empty or int(ov["lich"]) == 0:
                st.info(EMPTY_MSG)
            else:
                use["tong_sv"] = use["tong_sv"].astype(float)
                cap_used = float((use["so_ca"] * use["suc_chua"]).sum())
                fill = use["tong_sv"].sum() / cap_used * 100 if cap_used else 0
                slots_total = int(ov["phong_ok"]) * int(ov["khung"])
                occupancy = int(ov["lich"]) / slots_total * 100 if slots_total else 0
                c1, c2, c3 = st.columns(3)
                c1.metric("Tỷ lệ lấp đầy máy TB", f"{fill:.1f}%", "SV / số máy của các ca đã xếp", delta_color="off")
                c2.metric("Tỷ lệ sử dụng phòng × ca", f"{occupancy:.1f}%",
                          f"{int(ov['lich'])} / {slots_total} ô phòng-ca", delta_color="off")
                c3.metric("Phòng đã được dùng", f"{int((use['so_ca'] > 0).sum())} / {len(use)}",
                          f"TB {use['so_ca'].mean():.1f} ca/phòng", delta_color="off")
                use["Lấp đầy (%)"] = (use["tong_sv"] / (use["so_ca"] * use["suc_chua"]).where(use["so_ca"] > 0) * 100).round(1)
                st.subheader("Số ca thi theo phòng")
                st.bar_chart(use.set_index("ma_phong")["so_ca"])
                st.dataframe(use.rename(columns={"ma_phong": "Phòng", "suc_chua": "Số máy", "tinh_trang": "Tình trạng",
                                                 "so_ca": "Số ca", "tong_sv": "Tổng lượt SV"}),
                             use_container_width=True, hide_index=True)

    # 2. CÁN BỘ COI THI (GIÁM THỊ)
    elif user_role == "Giám thị (Cán bộ coi thi)":
        if selected_page == "📋 Lịch coi thi cá nhân":
            st.title("📋 Lịch coi thi cá nhân của bạn")
            st.caption(f"Cán bộ: **{user['name']}** - {user['dept']}")
            st.info("Schema hiện chưa có bảng phân công giám thị, nên dưới đây là **toàn bộ ca thi đã công bố**.")
            ses = load_sessions(published=True)
            if ses.empty:
                st.info(NO_PUBLISHED_MSG)
            else:
                ses["Ngày thi"] = fmt_dates(ses["ngay_iso"])
                ses["Ca thi"] = slot_labels(ses)
                ses["Học phần"] = ses["ten_mon"] + " (" + ses["ma_mon"] + ")"
                ses["Phòng thi"] = ses["ma_phong"] + " (Tầng " + ses["tang"].astype(str) + " - Nhà " + ses["toa_nha"] + ")"
                st.dataframe(ses[["Ngày thi", "Ca thi", "Học phần", "Phòng thi", "so_sv"]].rename(columns={"so_sv": "Số SV"}),
                             use_container_width=True, hide_index=True)
            st.button("✅ Xác nhận tham gia ca coi thi")

        elif selected_page == "👥 Danh sách sinh viên phòng thi":
            st.title("👥 Danh sách sinh viên trong ca coi thi")
            ses = load_sessions(published=True)
            if ses.empty:
                st.info(NO_PUBLISHED_MSG)
            else:
                ses["Ngày thi"] = fmt_dates(ses["ngay_iso"])
                labels = {int(r["ma_lich"]): f"{r['Ngày thi']} - Ca {r['ca_thi']}: {r['ma_mon']} tại {r['ma_phong']} ({r['so_sv']} SV)"
                          for _, r in ses.iterrows()}
                pick = st.selectbox("Chọn ca thi", list(labels), format_func=labels.get)
                sv_list = query_df("""
                    SELECT dk.so_may, sv.ma_sv, sv.ho_ten, sv.lop, sv.khoa
                    FROM dang_ky_thi dk JOIN sinh_vien sv ON sv.ma_sv = dk.ma_sv
                    WHERE dk.ma_lich = %s ORDER BY dk.so_may""", (int(pick),))
                sv_list["so_may"] = "Máy " + sv_list["so_may"].astype(str).str.zfill(2)
                st.dataframe(sv_list.rename(columns={"so_may": "Vị trí máy", "ma_sv": "MSSV", "ho_ten": "Họ và tên",
                                                     "lop": "Lớp", "khoa": "Khoa"}),
                             use_container_width=True, hide_index=True)
                st.download_button("🖨️ Xuất danh sách ký tên (CSV)", data=sv_list.to_csv(index=False).encode("utf-8-sig"),
                                   file_name=f"ds_phong_thi_{pick}.csv", mime="text/csv")

        elif selected_page == "⚠️ Báo cáo sự cố phòng thi/máy":
            st.title("⚠️ Báo cáo sự cố thiết bị tại phòng thi")
            st.caption("Gửi cảnh báo tức thời tới IT Helpdesk")
            room_opts = query_df("SELECT ma_phong FROM phong_may ORDER BY ma_phong")["ma_phong"].tolist() or ["(chưa có phòng)"]
            with st.form("incident_form"):
                st.selectbox("Phòng xảy ra sự cố", room_opts)
                st.selectbox("Loại sự cố", ["Hỏng chuột/bàn phím/máy tính", "Mất kết nối mạng nộp bài", "Lỗi phần mềm/thiếu compiler"])
                st.text_input("Vị trí máy bị lỗi", placeholder="VD: Máy số 12")
                st.text_area("Mô tả ngắn gọn")
                if st.form_submit_button("🚨 Gửi thông báo khẩn cấp"):
                    st.success("Đã gửi sự cố tới bộ phận kỹ thuật IT trực phòng máy!")

    # 3. SINH VIÊN
    elif user_role == "Sinh viên":
        if selected_page == "🔍 Tra cứu lịch thi cá nhân":
            st.title("🔍 Tra cứu lịch thi của bạn")
            st.caption("Chỉ hiển thị lịch thi đã được công bố.")
            first = query_df("SELECT dk.ma_sv FROM dang_ky_thi dk JOIN v_lich_thi_cong_bo lt ON lt.ma_lich = dk.ma_lich "
                             "ORDER BY dk.ma_sv LIMIT 1")
            default_id = first["ma_sv"].iloc[0] if len(first) else ""
            ma_sv = st.text_input("Mã sinh viên (MSSV)", value=default_id, placeholder="VD: SV20230001").strip()
            if not ma_sv:
                st.info(NO_PUBLISHED_MSG)
            else:
                info = query_df("SELECT ho_ten, lop, khoa, email FROM sinh_vien WHERE ma_sv = %s", (ma_sv,))
                if info.empty:
                    st.warning(f"Không tìm thấy sinh viên có MSSV `{ma_sv}`.")
                else:
                    r = info.iloc[0]
                    st.caption(f"Sinh viên: **{r['ho_ten']}** - Lớp {r['lop']} - {r['khoa']} - {r['email']}")
                    my = query_df(f"""
                        SELECT {SLOT_SQL}, mt.ma_mon, mt.ten_mon, mt.hinh_thuc, lt.ma_phong, pm.toa_nha, pm.tang,
                               dk.so_may, dk.diem
                        FROM dang_ky_thi dk
                        JOIN v_lich_thi_cong_bo lt ON lt.ma_lich = dk.ma_lich
                        JOIN khung_gio kg ON kg.ma_khung = lt.ma_khung
                        JOIN mon_thi mt ON mt.ma_mon = lt.ma_mon
                        JOIN phong_may pm ON pm.ma_phong = lt.ma_phong
                        WHERE dk.ma_sv = %s ORDER BY kg.ngay_thi, kg.ca_thi""", (ma_sv,))
                    if my.empty:
                        st.info("Sinh viên này chưa có lịch thi.")
                    else:
                        out = pd.DataFrame({
                            "Ngày thi": fmt_dates(my["ngay_iso"]),
                            "Ca thi": slot_labels(my),
                            "Môn thi": my["ten_mon"] + " (" + my["ma_mon"] + ")",
                            "Hình thức thi": my["hinh_thuc"],
                            "Địa điểm": my["ma_phong"] + " (Tầng " + my["tang"].astype(str) + " - Nhà " + my["toa_nha"] + ")",
                            "Số máy": "Máy số " + my["so_may"].astype(str).str.zfill(2),
                            "Điểm": my["diem"],
                        })
                        st.dataframe(out, use_container_width=True, hide_index=True)
                        st.download_button("📥 Tải lịch thi cá nhân (CSV)", data=out.to_csv(index=False).encode("utf-8-sig"),
                                           file_name=f"lich_thi_{ma_sv}.csv", mime="text/csv")

        elif selected_page == "🖥️ Tra cứu yêu cầu phòng máy":
            st.title("🖥️ Yêu cầu môi trường & Phần mềm phòng máy")
            tools_df = query_df(f"""
                SELECT mt.ma_mon, mt.ten_mon, mt.hinh_thuc,
                       COALESCE((SELECT {SW_LIST} FROM mon_thi_phan_mem r JOIN phan_mem p ON p.ma_pm = r.ma_pm
                                 WHERE r.ma_mon = mt.ma_mon), 'Không') AS phan_mem,
                       (SELECT GROUP_CONCAT(DISTINCT he_dieu_hanh SEPARATOR ', ') FROM phong_may) AS he_dieu_hanh,
                       (SELECT COUNT(*) FROM phong_may rm WHERE rm.tinh_trang = 'Working'
                          AND NOT EXISTS (SELECT 1 FROM mon_thi_phan_mem rq WHERE rq.ma_mon = mt.ma_mon
                                AND NOT EXISTS (SELECT 1 FROM phong_may_phan_mem i
                                                WHERE i.ma_phong = rm.ma_phong AND i.ma_pm = rq.ma_pm))) AS so_phong
                FROM mon_thi mt ORDER BY mt.ma_mon""")
            if tools_df.empty:
                st.info(EMPTY_MSG)
            else:
                st.dataframe(tools_df.rename(columns={
                    "ma_mon": "Mã môn", "ten_mon": "Môn thi", "hinh_thuc": "Hình thức thi", "phan_mem": "Phần mềm / IDE",
                    "he_dieu_hanh": "Hệ điều hành", "so_phong": "Số phòng đáp ứng"}),
                    use_container_width=True, hide_index=True)

    # 4. QUẢN TRỊ VIÊN (IT HELPDESK)
    else:
        if selected_page == "🎛️ Tham số bộ giải ILP/CSP":
            st.title("🎛️ Cấu hình bộ giải toán ILP / CSP")
            st.caption("Tối ưu hóa hiệu năng và thông số tính toán cho hệ thống xếp lịch")
            c1, c2 = st.columns(2)
            with c1:
                st.selectbox("Mô hình Solver Engine", ["HiGHS (Khuyên dùng)", "CBC (COIN-OR)", "Google OR-Tools"])
                st.number_input("Thời gian tối đa (Time limit - giây)", 30, 3600, 300)
                st.number_input("Số luồng CPU (Threads)", 1, 16, 4)
            with c2:
                st.number_input("Trọng số phạt khi thi 2 ca trong 1 ngày", value=100)
                st.number_input("Trọng số phạt khi chênh lệch số ca giữa các phòng", value=50)
                st.checkbox("Bật Solver Log chi tiết", value=True)
            st.button("💾 Cập nhật tham số bộ giải", type="primary")

        elif selected_page == "👥 Quản lý tài khoản & Phân quyền":
            st.title("👥 Quản lý người dùng & Phân quyền")
            users_df = pd.DataFrame({
                "Tài khoản": list(ACCOUNTS),
                "Họ tên": [a["name"] for a in ACCOUNTS.values()],
                "Vai trò gán": [a["role"] for a in ACCOUNTS.values()],
                "Trạng thái": ["Hoạt động"] * len(ACCOUNTS),
            })
            st.dataframe(users_df, use_container_width=True, hide_index=True)
            st.button("➕ Thêm tài khoản mới")

        elif selected_page == "🛠️ Giám sát & Hỗ trợ kỹ thuật":
            st.title("🛠️ Giám sát hệ thống & Hàng đợi sự cố")
            node = query_df("SELECT @@hostname AS host, @@server_id AS sid, @@read_only AS ro").iloc[0]
            counts = query_df("""
                SELECT 'sinh_vien' AS bang, COUNT(*) AS so_ban_ghi FROM sinh_vien
                UNION ALL SELECT 'mon_thi', COUNT(*) FROM mon_thi
                UNION ALL SELECT 'phong_may', COUNT(*) FROM phong_may
                UNION ALL SELECT 'phan_mem', COUNT(*) FROM phan_mem
                UNION ALL SELECT 'phong_may_phan_mem', COUNT(*) FROM phong_may_phan_mem
                UNION ALL SELECT 'mon_thi_phan_mem', COUNT(*) FROM mon_thi_phan_mem
                UNION ALL SELECT 'khung_gio', COUNT(*) FROM khung_gio
                UNION ALL SELECT 'phuong_an', COUNT(*) FROM phuong_an
                UNION ALL SELECT 'lich_thi', COUNT(*) FROM lich_thi
                UNION ALL SELECT 'dang_ky_thi', COUNT(*) FROM dang_ky_thi""")
            maint_n = int(query_df("SELECT COUNT(*) AS n FROM phong_may WHERE tinh_trang <> 'Working'")["n"].iloc[0])
            c1, c2, c3 = st.columns(3)
            c1.metric("Node CSDL (kết nối ghi)", str(node["host"]),
                      f"server_id {int(node['sid'])} · {'CHỈ ĐỌC' if int(node['ro']) else 'ghi được'}", delta_color="off")
            c2.metric("Phòng máy đang bảo trì", f"{maint_n} phòng", "Cần kiểm tra" if maint_n else "Tốt", delta_color="off")
            c3.metric("Trạng thái Solver Engine", "Sẵn sàng", "v1.6", delta_color="off")

            st.subheader("Số bản ghi theo bảng")
            st.dataframe(counts.rename(columns={"bang": "Bảng", "so_ban_ghi": "Số bản ghi"}),
                         use_container_width=True, hide_index=True)

            st.subheader("Phiếu sự cố báo về từ Giám thị các phòng thi")
            tickets_df = pd.DataFrame({
                "Mã vé": ["#TK101", "#TK102"],
                "Phòng": ["PA2001", "PB3010"],
                "Nội dung": ["Máy số 12 bị kẹt bàn phím", "Cần thêm thư viện Python cho ca chiều"],
                "Giám thị báo": ["TS. Nguyễn Văn A", "ThS. Trần Thị B"],
                "Xử lý": ["Đang hỗ trợ", "Đã xử lý"]
            })
            st.dataframe(tickets_df, use_container_width=True, hide_index=True)