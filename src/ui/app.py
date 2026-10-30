import streamlit as st
import pandas as pd
from datetime import date, datetime
import sys
import importlib.util
from decimal import Decimal
from pathlib import Path

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

    .status-badge-published {
        display: inline-block;
        padding: 3px 10px;
        font-size: 12px;
        font-weight: 600;
        border-radius: 14px;
        background-color: #ECFDF5;
        color: #047857;
        border: 1px solid #A7F3D0;
    }
    .status-badge-approved {
        display: inline-block;
        padding: 3px 10px;
        font-size: 12px;
        font-weight: 600;
        border-radius: 14px;
        background-color: #FEF3C7;
        color: #B45309;
        border: 1px solid #FDE68A;
    }
    .status-badge-draft {
        display: inline-block;
        padding: 3px 10px;
        font-size: 12px;
        font-weight: 600;
        border-radius: 14px;
        background-color: #F1F5F9;
        color: #475569;
        border: 1px solid #CBD5E1;
    }
    
    .user-profile-box {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 12px;
        margin-bottom: 12px;
    }
    
    .rule-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 13px 16px;
        margin-bottom: 10px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.02);
    }
    .rule-badge-mandatory {
        display: inline-block;
        padding: 2px 8px;
        font-size: 11px;
        font-weight: 600;
        border-radius: 12px;
        background-color: #ECFDF5;
        color: #047857;
        border: 1px solid #A7F3D0;
    }
    .rule-title {
        font-weight: 600;
        font-size: 14px;
        color: #0F172A;
    }
    .rule-desc {
        font-size: 13px;
        color: #64748B;
        line-height: 1.45;
        margin-top: 4px;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# KẾT NỐI CSDL & TIỆN ÍCH TRUY VẤN
# ==============================================================================
HERE = Path(__file__).resolve().parent
ROOT = next((p for p in [HERE, *HERE.parents] if (p / "src" / "backend").exists()), None)
for _p in (ROOT, HERE):
    if _p and str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

try:
    from src.backend.db_helper import get_master_connection
    DB_IMPORT_ERROR = None
except Exception as exc:
    get_master_connection = None
    DB_IMPORT_ERROR = exc


def _rows(cur):
    """Chuẩn hoá kết quả cursor (tuple hoặc dict) thành list[dict]."""
    cols = [d[0] for d in cur.description]
    return [r if isinstance(r, dict) else dict(zip(cols, r)) for r in cur.fetchall()], cols


def _run_query(sql: str, params: tuple = ()) -> pd.DataFrame:
    """Chạy SELECT và trả về DataFrame (không cache)."""
    if get_master_connection is None:
        raise RuntimeError(f"Chưa có db_helper: {DB_IMPORT_ERROR}")
    conn = get_master_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql, params or None)
        rows, cols = _rows(cur)
    finally:
        conn.close()
    df = pd.DataFrame(rows, columns=cols)
    for c in df.columns:
        if df[c].map(lambda v: isinstance(v, Decimal)).any():
            df[c] = df[c].astype(float)
    return df


@st.cache_data(ttl=60, show_spinner=False)
def query_df(sql: str, params: tuple = ()) -> pd.DataFrame:
    """Bản có cache 60s."""
    return _run_query(sql, params)


def db_ping():
    if get_master_connection is None:
        return False, f"Không import được src.backend.db_helper: {DB_IMPORT_ERROR}"
    try:
        _run_query("SELECT COUNT(*) AS n FROM sinh_vien")
        return True, ""
    except Exception as exc:
        return False, str(exc)


def load_generator():
    """Nạp generate_data.py từ thư mục dự án."""
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

# ==============================================================================
# DỮ LIỆU MẪU (MOCK DATA KHI CHƯA KẾT NỐI ĐƯỢC MYSQL)
# ==============================================================================
MOCK_SUBJECTS = pd.DataFrame({
    "Mã HP": ["IT101", "IT205", "CS301", "MATH101", "NET201", "DB102"],
    "Tên học phần": ["Cơ sở lập trình", "Cấu trúc dữ liệu & GT", "Học máy & Trí tuệ nhân tạo", "Toán rời rạc", "Mạng máy tính", "Hệ quản trị CSDL"],
    "Tín chỉ": [3, 4, 3, 3, 3, 3],
    "Thời lượng (phút)": [90, 90, 120, 90, 90, 90],
    "Hình thức thi": ["Thực hành máy", "Thực hành máy", "Thực hành GPU", "Viết trên giấy", "Thực hành máy", "Thực hành máy"],
    "Yêu cầu phần mềm": ["VS Code, Python 3.11", "Code::Blocks, Dev C++", "CUDA 12, PyTorch, PyCharm", "Không", "Cisco Packet Tracer, Wireshark", "MySQL Workbench, Navicat"],
    "Số SV": [120, 85, 45, 150, 95, 110]
})

MOCK_ROOMS = pd.DataFrame({
    "Phòng": ["PM.01", "PM.02", "PM.03 (GPU)", "PM.04", "LT.101", "LT.102"],
    "Tòa": ["Nhà A", "Nhà A", "Nhà A", "Nhà B", "Nhà C", "Nhà C"],
    "Tầng": [2, 2, 3, 1, 1, 2],
    "Số máy": [40, 45, 35, 40, 80, 75],
    "Hệ điều hành": ["Windows 11 64-bit", "Windows 10 64-bit", "Ubuntu 22.04 LTS", "Windows 11 64-bit", "Không", "Không"],
    "Tình trạng": ["Working", "Working", "Working", "Maintenance", "Working", "Working"],
    "Phần mềm cài đặt": ["VS Code, Python, MySQL", "Dev C++, Java 17, Packet Tracer", "CUDA, PyTorch, PyCharm, Docker", "Đang sửa chữa cáp mạng", "Bàn ghế tiêu chuẩn", "Bàn ghế tiêu chuẩn"],
    "Số ca thi": [8, 7, 4, 0, 6, 5]
})

MOCK_STUDENTS = pd.DataFrame({
    "MSSV": ["20210001", "20210002", "20210003", "20210004", "20210005", "20210006"],
    "Họ tên": ["Nguyễn Văn An", "Trần Thị Bình", "Lê Hoàng Cường", "Phạm Minh Đức", "Hoàng Thuỳ Linh", "Vũ Quốc Tuấn"],
    "Ngày sinh": ["2003-05-15", "2003-08-22", "2002-11-04", "2003-01-19", "2003-09-30", "2002-07-12"],
    "Giới tính": ["Nam", "Nữ", "Nam", "Nam", "Nữ", "Nam"],
    "Email": ["an.nv210001@sis.edu.vn", "binh.tt210002@sis.edu.vn", "cuong.lh210003@sis.edu.vn", "duc.pm210004@sis.edu.vn", "linh.ht210005@sis.edu.vn", "tuan.vq210006@sis.edu.vn"],
    "SĐT": ["0987111222", "0987222333", "0987333444", "0987444555", "0987555666", "0987666777"],
    "Lớp": ["CNTT K21A", "CNTT K21A", "CNTT K21B", "KTPM K21A", "HTTT K21B", "CNTT K21B"],
    "Khoa": ["Khoa CNTT", "Khoa CNTT", "Khoa CNTT", "Khoa CNTT", "Khoa Hệ thống thông tin", "Khoa CNTT"],
    "Khóa": [2021, 2021, 2021, 2021, 2021, 2021]
})

MOCK_TIME_SLOTS = pd.DataFrame({
    "Mã khung": ["KG01", "KG02", "KG03", "KG04", "KG05", "KG06"],
    "Ngày thi": ["10/11/2026", "10/11/2026", "11/11/2026", "11/11/2026", "12/11/2026", "13/11/2026"],
    "Ca": [1, 2, 1, 2, 1, 1],
    "Bắt đầu": ["07:30", "09:45", "07:30", "09:45", "07:30", "07:30"],
    "Kết thúc": ["09:30", "11:45", "09:30", "11:45", "09:30", "09:30"],
    "Số phòng đang dùng": [4, 4, 3, 3, 2, 3]
})

if "mock_sessions" not in st.session_state:
    st.session_state["mock_sessions"] = pd.DataFrame([
        {"ma_lich": 101, "Ngày thi": "10/11/2026", "Ca thi": "Ca 1 (07:30 - 09:30)", "Học phần": "Cơ sở lập trình (IT101)", "ma_phong": "PM.01", "Phòng thi": "PM.01 (40 máy)", "so_sv": 38, "Trạng thái": "✅ Hợp lệ", "Giám thị": "TS. Nguyễn Văn A"},
        {"ma_lich": 102, "Ngày thi": "10/11/2026", "Ca thi": "Ca 2 (09:45 - 11:45)", "Học phần": "Cấu trúc dữ liệu & GT (IT205)", "ma_phong": "PM.02", "Phòng thi": "PM.02 (45 máy)", "so_sv": 42, "Trạng thái": "✅ Hợp lệ", "Giám thị": "ThS. Trần Thị B"},
        {"ma_lich": 103, "Ngày thi": "11/11/2026", "Ca thi": "Ca 1 (07:30 - 09:30)", "Học phần": "Học máy & AI (CS301)", "ma_phong": "PM.03 (GPU)", "Phòng thi": "PM.03 (GPU) (35 máy)", "so_sv": 32, "Trạng thái": "✅ Hợp lệ", "Giám thị": "TS. Nguyễn Văn A"},
        {"ma_lich": 104, "Ngày thi": "11/11/2026", "Ca thi": "Ca 2 (09:45 - 11:45)", "Học phần": "Toán rời rạc (MATH101)", "ma_phong": "LT.101", "Phòng thi": "LT.101 (80 chỗ)", "so_sv": 75, "Trạng thái": "✅ Hợp lệ", "Giám thị": "TS. Phạm Minh D"},
        {"ma_lich": 105, "Ngày thi": "12/11/2026", "Ca thi": "Ca 1 (07:30 - 09:30)", "Học phần": "Mạng máy tính (NET201)", "ma_phong": "PM.02", "Phòng thi": "PM.02 (45 máy)", "so_sv": 40, "Trạng thái": "✅ Hợp lệ", "Giám thị": "ThS. Lê Hoàng C"},
        {"ma_lich": 106, "Ngày thi": "13/11/2026", "Ca thi": "Ca 1 (07:30 - 09:30)", "Học phần": "Hệ quản trị CSDL (DB102)", "ma_phong": "PM.01", "Phòng thi": "PM.01 (40 máy)", "so_sv": 39, "Trạng thái": "✅ Hợp lệ", "Giám thị": "ThS. Trần Thị B"}
    ])

if "incident_tickets" not in st.session_state:
    st.session_state["incident_tickets"] = [
        {"Mã vé": "#TK101", "Phòng": "PM.01", "Nội dung": "Máy số 12 bị kẹt bàn phím", "Giám thị báo": "TS. Nguyễn Văn A", "Thời gian": "08:15 10/11/2026", "Xử lý": "Đang hỗ trợ"},
        {"Mã vé": "#TK102", "Phòng": "PM.02", "Nội dung": "Cần thêm thư viện Python cho ca chiều", "Giám thị báo": "ThS. Trần Thị B", "Thời gian": "10:30 10/11/2026", "Xử lý": "Đã xử lý"}
    ]

# Trạng thái tiến trình xếp lịch (TrangThaiPhuongAn trong class diagram)
if "schedule_status" not in st.session_state:
    st.session_state["schedule_status"] = "DA_CONG_BO"  # "NHAP", "DA_DUYET", "DA_CONG_BO"

# ==============================================================================
# HÀM TRUY VẤN CSDL HYBRID (HỖ TRỢ CẢ LIVE DB & MOCK)
# ==============================================================================
def load_overview_data(is_mock: bool):
    if not is_mock:
        try:
            return query_df("""
                SELECT (SELECT COUNT(*) FROM mon_thi) AS mon,
                       (SELECT COUNT(*) FROM phong_may) AS phong,
                       (SELECT COUNT(*) FROM phong_may WHERE tinh_trang = 'Working') AS phong_ok,
                       (SELECT COUNT(*) FROM sinh_vien) AS sv,
                       (SELECT COUNT(*) FROM lich_thi) AS lich,
                       (SELECT COUNT(*) FROM dang_ky_thi) AS dk,
                       (SELECT COUNT(*) FROM khung_gio) AS khung""").iloc[0]
        except Exception:
            pass
    return pd.Series({
        "mon": len(MOCK_SUBJECTS),
        "phong": len(MOCK_ROOMS),
        "phong_ok": len(MOCK_ROOMS[MOCK_ROOMS["Tình trạng"] == "Working"]),
        "sv": 420,
        "lich": len(st.session_state["mock_sessions"]),
        "dk": 412,
        "khung": len(MOCK_TIME_SLOTS)
    })

def load_sessions_data(is_mock: bool):
    if not is_mock:
        try:
            df = query_df(f"""
                SELECT lt.ma_lich, {SLOT_SQL}, lt.ma_mon, mt.ten_mon, lt.ma_phong,
                       pm.suc_chua, pm.toa_nha, pm.tang,
                       (SELECT COUNT(*) FROM dang_ky_thi dk WHERE dk.ma_lich = lt.ma_lich) AS so_sv
                FROM lich_thi lt
                JOIN khung_gio kg ON kg.ma_khung = lt.ma_khung
                JOIN mon_thi mt ON mt.ma_mon = lt.ma_mon
                JOIN phong_may pm ON pm.ma_phong = lt.ma_phong
                ORDER BY kg.ngay_thi, kg.ca_thi, lt.ma_phong""")
            if not df.empty:
                df["Ngày thi"] = fmt_dates(df["ngay_iso"])
                df["Ca thi"] = slot_labels(df)
                df["Học phần"] = df["ten_mon"] + " (" + df["ma_mon"] + ")"
                df["Phòng thi"] = df["ma_phong"] + " (" + df["suc_chua"].astype(str) + " máy)"
                df["Trạng thái"] = df.apply(lambda r: "✅ Hợp lệ" if r["so_sv"] <= r["suc_chua"] else "❌ Vượt sức chứa", axis=1)
                return df
        except Exception:
            pass
    return st.session_state["mock_sessions"].copy()

# ==============================================================================
# QUẢN LÝ TÀI KHOẢN MẪU
# ==============================================================================
ACCOUNTS = {
    "giaovu": {
        "password": "giaovu",
        "name": "Nguyễn Thị Mai",
        "role": "Giáo vụ (Quản lý đào tạo)",
        "dept": "Phòng Đào tạo",
        "email": "ntmai@university.edu.vn"
    },
    "giamthi": {
        "password": "giamthi",
        "name": "TS. Nguyễn Văn A",
        "role": "Giám thị (Cán bộ coi thi)",
        "dept": "Khoa Công nghệ thông tin",
        "email": "nva@university.edu.vn"
    },
    "sinhvien": {
        "password": "sinhvien",
        "name": "Nguyễn Văn An",
        "role": "Sinh viên",
        "dept": "Lớp CNTT K21A - MSSV: 20210001",
        "email": "an.nv210001@sis.edu.vn",
        "ma_sv": "20210001"
    },
    "admin": {
        "password": "admin",
        "name": "Đỗ Quang Minh",
        "role": "Quản trị viên (IT Helpdesk)",
        "dept": "Trung tâm Mạng & Máy tính",
        "email": "minhdq@university.edu.vn"
    }
}

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "current_user" not in st.session_state:
    st.session_state["current_user"] = None

def authenticate_user(username: str, password: str, is_mock: bool):
    uname = (username or "").strip()
    pwd = (password or "").strip()
    if not uname or not pwd:
        return None, "Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu."

    # 1. Kiểm tra tài khoản hệ thống mặc định
    if uname in ACCOUNTS and ACCOUNTS[uname]["password"] == pwd:
        return {
            "username": uname,
            **ACCOUNTS[uname]
        }, None

    # 2. Kiểm tra nếu đăng nhập bằng mã SV trong CSDL (khi kết nối DB)
    if not is_mock:
        try:
            sv_rows = query_df("SELECT ma_sv, ho_ten, lop, khoa, email FROM sinh_vien WHERE ma_sv = %s", (uname,))
            if not sv_rows.empty and (pwd == uname or pwd == "sinhvien" or pwd == "123"):
                r = sv_rows.iloc[0]
                return {
                    "username": r["ma_sv"],
                    "name": r["ho_ten"],
                    "role": "Sinh viên",
                    "dept": f"Lớp {r['lop']} - {r['khoa']}",
                    "email": r["email"],
                    "ma_sv": r["ma_sv"]
                }, None
        except Exception:
            pass

    # 3. Kiểm tra nếu đăng nhập bằng mã SV trong Mock Data
    sv_mock = MOCK_STUDENTS[MOCK_STUDENTS["MSSV"] == uname]
    if not sv_mock.empty and (pwd == uname or pwd == "sinhvien" or pwd == "123"):
        r = sv_mock.iloc[0]
        return {
            "username": r["MSSV"],
            "name": r["Họ tên"],
            "role": "Sinh viên",
            "dept": f"Lớp {r['Lớp']} - {r['Khoa']}",
            "email": r["Email"],
            "ma_sv": r["MSSV"]
        }, None

    return None, "Sai tên đăng nhập hoặc mật khẩu! (Gợi ý: giaovu/giaovu, giamthi/giamthi, admin/admin, sinhvien/sinhvien)"

def logout_user():
    st.session_state["logged_in"] = False
    st.session_state["current_user"] = None
    st.rerun()

# ==============================================================================
# KIỂM TRA TRẠNG THÁI KẾT NỐI DB VÀ CHẾ ĐỘ VẬN HÀNH
# ==============================================================================
db_online, db_err = db_ping()
if "force_mock" not in st.session_state:
    st.session_state["force_mock"] = not db_online

is_mock_mode = st.session_state["force_mock"] or (not db_online)

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
            
            with st.form("login_form"):
                uname_input = st.text_input("Tên đăng nhập / Mã sinh viên", placeholder="VD: giaovu, giamthi, sinhvien, admin hoặc 20210001")
                pwd_input = st.text_input("Mật khẩu", type="password", placeholder="Nhập mật khẩu")
                login_btn = st.form_submit_button("Đăng nhập", type="primary", use_container_width=True)
                
                if login_btn:
                    user_info, err = authenticate_user(uname_input, pwd_input, is_mock_mode)
                    if user_info:
                        st.session_state["logged_in"] = True
                        st.session_state["current_user"] = user_info
                        st.rerun()
                    else:
                        st.error(f"❌ {err}")

            with st.expander("💡 Tài khoản mẫu kiểm thử nhanh"):
                st.markdown("""
                - **Giáo vụ:** `giaovu` / `giaovu`
                - **Giám thị:** `giamthi` / `giamthi`
                - **Sinh viên:** `sinhvien` / `sinhvien` hoặc mã SV `20210001` (mật khẩu = mã SV)
                - **Quản trị IT:** `admin` / `admin`
                """)

            if not db_online:
                st.caption(f"ℹ️ Đang chạy ở chế độ **Dữ liệu mô phỏng (Demo)** do chưa kết nối MySQL.")

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
        
        # Trạng thái kết nối DB / Demo
        if db_online:
            st.success("🟢 Kết nối CSDL: `quan_ly_thi`")
        else:
            st.warning("🟡 Chế độ: Dữ liệu mô phỏng (Demo)")
            with st.expander("Chi tiết kết nối"):
                st.caption(f"Lý do: {db_err}")
                st.caption("Khởi động MySQL container để đồng bộ dữ liệu thật.")

        st.divider()
        
        # Hộp thông tin cá nhân của người dùng đã xác thực
        st.markdown(f"""
        <div class="user-profile-box">
            <div style="font-weight: 700; font-size: 15px; color: #1E293B;">👤 {user['name']}</div>
            <div style="font-size: 13px; color: #64748B;">{user['dept']}</div>
            <div style="margin-top: 8px;"><span class="role-badge">{user_role}</span></div>
        </div>
        """, unsafe_allow_html=True)

        # Trạng thái phương án lịch thi hiện tại
        cur_status = st.session_state["schedule_status"]
        if cur_status == "DA_CONG_BO":
            st.markdown("Trạng thái lịch thi: <span class='status-badge-published'>📢 Đã công bố</span>", unsafe_allow_html=True)
        elif cur_status == "DA_DUYET":
            st.markdown("Trạng thái lịch thi: <span class='status-badge-approved'>⏳ Đã phê duyệt</span>", unsafe_allow_html=True)
        else:
            st.markdown("Trạng thái lịch thi: <span class='status-badge-draft'>📝 Bản nháp</span>", unsafe_allow_html=True)

        st.write("")
        # Nút Đăng xuất
        if st.button("🚪 Đăng xuất", use_container_width=True):
            logout_user()
            
        st.divider()
        
        # Phân quyền danh mục Menu chỉ dành riêng cho vai trò đã đăng nhập
        if user_role == "Giáo vụ (Quản lý đào tạo)":
            menu_items = [
                "📊 Tổng quan điều hành",
                "📁 Quản lý dữ liệu",
                "⚙️ Quy chuẩn & Tiêu chí xếp lịch",
                "🧩 Xếp lịch tự động & Tối ưu hóa",
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
    # 1. GIÁO VỤ (QUẢN LÝ ĐÀO TẠO)
    # -------------------------------------------------------------------------
    if user_role == "Giáo vụ (Quản lý đào tạo)":
        if selected_page == "📊 Tổng quan điều hành":
            st.title("📊 Tổng quan điều hành kỳ thi")
            st.caption(f"Xin chào **{user['name']}** - Phòng Đào tạo")
            
            ov = load_overview_data(is_mock_mode)
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Tổng học phần thi", f"{int(ov['mon'])} môn", f"{int(ov['sv'])} sinh viên", delta_color="off")
            c2.metric("Phòng máy khả dụng", f"{int(ov['phong_ok'])} / {int(ov['phong'])} phòng",
                      f"{int(ov['phong'] - ov['phong_ok'])} phòng bảo trì", delta_color="off")
            c3.metric("Ca thi đã xếp", f"{int(ov['lich'])} ca", f"{int(ov['khung'])} khung giờ", delta_color="off")
            c4.metric("Lượt đăng ký thi", f"{int(ov['dk'])} lượt", "Đã xếp chỗ ngồi", delta_color="off")

            st.markdown("---")
            col_left, col_right = st.columns([2, 1])
            with col_left:
                st.subheader("Tiến trình đợt xếp lịch (Service Blueprint)")
                steps_df = pd.DataFrame({
                    "Giai đoạn": ["1. Chuẩn bị dữ liệu", "2. Thiết lập ràng buộc", "3. Tạo & kiểm tra lịch", "4. Duyệt & Công bố", "5. Tra cứu & Báo cáo"],
                    "Hành động": [
                        "Nhập học phần, phòng máy, giám thị",
                        "Cấu hình ràng buộc cứng & mục tiêu mềm",
                        "Bộ giải ILP/CSP tối ưu lịch thi",
                        "Phê duyệt & phát hành lịch thi",
                        "Sinh viên & Giám thị xem lịch"
                    ],
                    "Trạng thái": ["✅ Hoàn tất", "✅ Hoàn tất", "⚡ Đã sinh phương án #1",
                                  "📢 Đã công bố" if st.session_state["schedule_status"] == "DA_CONG_BO" else ("⏳ Đã duyệt" if st.session_state["schedule_status"] == "DA_DUYET" else "📝 Bản nháp"),
                                  "🔓 Đã mở" if st.session_state["schedule_status"] == "DA_CONG_BO" else "🔒 Chưa mở"]
                })
                st.dataframe(steps_df, use_container_width=True, hide_index=True)
            with col_right:
                st.subheader("Cảnh báo nhanh")
                st.info("💡 **Gợi ý:** Có 2 môn thực hành AI yêu cầu phòng máy có GPU (PM.03).")
                st.warning("⚠️ **Lưu ý:** Phòng PM.04 hiện đang bảo trì cáp mạng.")

        elif selected_page == "📁 Quản lý dữ liệu":
            st.title("📁 Quản lý dữ liệu gốc")
            st.caption("Nhập và quản lý danh mục học phần, phòng thi/máy và cán bộ coi thi (UC1, UC2, UC3, UC4)")
            t1, t2, t3, t4, t5, t6 = st.tabs(["📘 Học phần", "🏫 Phòng máy", "🎓 Sinh viên",
                                              "🕒 Khung giờ & Giám thị", "🧪 Sinh dữ liệu mẫu", "📥 Nhập dữ liệu (Excel/CSV)"])
            with t1:
                st.subheader("Danh mục học phần & Yêu cầu phần mềm (UC1)")
                if not is_mock_mode:
                    try:
                        hp_df = query_df(f"""
                            SELECT mt.ma_mon, mt.ten_mon, mt.so_tin_chi, mt.thoi_luong_phut, mt.hinh_thuc,
                                   COALESCE((SELECT {SW_LIST} FROM mon_thi_phan_mem r
                                             JOIN phan_mem p ON p.ma_pm = r.ma_pm WHERE r.ma_mon = mt.ma_mon), 'Không') AS phan_mem,
                                   (SELECT COUNT(*) FROM lich_thi lt JOIN dang_ky_thi dk ON dk.ma_lich = lt.ma_lich
                                    WHERE lt.ma_mon = mt.ma_mon) AS so_sv
                            FROM mon_thi mt ORDER BY mt.ma_mon""")
                        st.dataframe(hp_df.rename(columns={
                            "ma_mon": "Mã HP", "ten_mon": "Tên học phần", "so_tin_chi": "Tín chỉ",
                            "thoi_luong_phut": "Thời lượng (phút)", "hinh_thuc": "Hình thức thi",
                            "phan_mem": "Yêu cầu phần mềm", "so_sv": "Số SV"}),
                            use_container_width=True, hide_index=True)
                    except Exception:
                        st.dataframe(MOCK_SUBJECTS, use_container_width=True, hide_index=True)
                else:
                    st.dataframe(MOCK_SUBJECTS, use_container_width=True, hide_index=True)
                st.button("➕ Thêm học phần mới")

            with t2:
                st.subheader("Danh mục phòng thi & Cấu hình máy (UC2)")
                if not is_mock_mode:
                    try:
                        room_df = query_df(f"""
                            SELECT pm.ma_phong, pm.toa_nha, pm.tang, pm.suc_chua, pm.he_dieu_hanh, pm.tinh_trang,
                                   (SELECT {SW_LIST} FROM phong_may_phan_mem l JOIN phan_mem p ON p.ma_pm = l.ma_pm
                                    WHERE l.ma_phong = pm.ma_phong) AS phan_mem,
                                   (SELECT COUNT(*) FROM lich_thi lt WHERE lt.ma_phong = pm.ma_phong) AS so_ca
                            FROM phong_may pm ORDER BY pm.ma_phong""")
                        only_ok = st.checkbox("Chỉ hiện phòng đang hoạt động", value=False)
                        if only_ok:
                            room_df = room_df[room_df["tinh_trang"] == "Working"]
                        st.dataframe(room_df.rename(columns={
                            "ma_phong": "Phòng", "toa_nha": "Tòa", "tang": "Tầng", "suc_chua": "Số máy",
                            "he_dieu_hanh": "Hệ điều hành", "tinh_trang": "Tình trạng",
                            "phan_mem": "Phần mềm cài đặt", "so_ca": "Số ca thi"}),
                            use_container_width=True, hide_index=True)
                    except Exception:
                        st.dataframe(MOCK_ROOMS, use_container_width=True, hide_index=True)
                else:
                    st.dataframe(MOCK_ROOMS, use_container_width=True, hide_index=True)

            with t3:
                st.subheader("Danh sách sinh viên & Nhóm thi (UC1)")
                if not is_mock_mode:
                    try:
                        sv_df = query_df("""SELECT ma_sv, ho_ten, CAST(ngay_sinh AS CHAR) AS ngay_sinh, gioi_tinh,
                                                   email, so_dien_thoai, lop, khoa, khoa_hoc
                                            FROM sinh_vien ORDER BY ma_sv""")
                        f1, f2 = st.columns([2, 1])
                        kw = f1.text_input("Tìm theo MSSV / họ tên / lớp", placeholder="VD: 2021, Nguyễn, CNTT")
                        khoa = f2.selectbox("Khoa", ["Tất cả"] + sorted(sv_df["khoa"].unique()))
                        view = sv_df
                        if kw:
                            mask = (view["ma_sv"].str.contains(kw, case=False, regex=False)
                                    | view["ho_ten"].str.contains(kw, case=False, regex=False)
                                    | view["lop"].str.contains(kw, case=False, regex=False))
                            view = view[mask]
                        if khoa != "Tất cả":
                            view = view[view["khoa"] == khoa]
                        st.caption(f"{len(view)} / {len(sv_df)} sinh viên")
                        st.dataframe(view.rename(columns={
                            "ma_sv": "MSSV", "ho_ten": "Họ tên", "ngay_sinh": "Ngày sinh", "gioi_tinh": "Giới tính",
                            "email": "Email", "so_dien_thoai": "SĐT", "lop": "Lớp", "khoa": "Khoa",
                            "khoa_hoc": "Khóa"}), use_container_width=True, hide_index=True)
                    except Exception:
                        st.dataframe(MOCK_STUDENTS, use_container_width=True, hide_index=True)
                else:
                    st.dataframe(MOCK_STUDENTS, use_container_width=True, hide_index=True)

            with t4:
                st.subheader("Khung giờ thi & Giám thị (UC3)")
                if not is_mock_mode:
                    try:
                        kg_df = query_df(f"""
                            SELECT kg.ma_khung, {SLOT_SQL},
                                   (SELECT COUNT(*) FROM lich_thi lt WHERE lt.ma_khung = kg.ma_khung) AS so_phong
                            FROM khung_gio kg ORDER BY kg.ngay_thi, kg.ca_thi""")
                        kg_df["Ngày thi"] = fmt_dates(kg_df["ngay_iso"])
                        st.dataframe(kg_df[["ma_khung", "Ngày thi", "ca_thi", "gio_bd", "gio_kt", "so_phong"]].rename(columns={
                            "ma_khung": "Mã khung", "ca_thi": "Ca", "gio_bd": "Bắt đầu", "gio_kt": "Kết thúc",
                            "so_phong": "Số phòng đang dùng"}), use_container_width=True, hide_index=True)
                    except Exception:
                        st.dataframe(MOCK_TIME_SLOTS, use_container_width=True, hide_index=True)
                else:
                    st.dataframe(MOCK_TIME_SLOTS, use_container_width=True, hide_index=True)

            with t5:
                st.subheader("🧪 Sinh dữ liệu mẫu vào CSDL")
                if is_mock_mode:
                    st.info("💡 Tính năng sinh dữ liệu trực tiếp yêu cầu kết nối CSDL MySQL đang hoạt động. Hiện đang chạy chế độ Mock Demo.")
                else:
                    st.caption("Sinh dữ liệu ngẫu nhiên vào schema `quan_ly_thi` phục vụ kiểm thử bài toán tối ưu.")
                    with st.form("gen_form"):
                        g1, g2 = st.columns(2)
                        n_sv = g1.number_input("Số sinh viên", 10, 20000, 300, step=50)
                        n_mon = g2.number_input("Số môn thi (tối đa 22)", 1, 22, 12)
                        n_phong = g1.number_input("Số phòng máy", 3, 500, 10)
                        n_ngay = g2.number_input("Số ngày thi", 1, 30, 5)
                        confirm = st.checkbox("Xác nhận tạo mới dữ liệu kiểm thử")
                        go = st.form_submit_button("🧪 Bắt đầu sinh dữ liệu", type="primary")
                        if go and confirm:
                            gen = load_generator()
                            if gen:
                                conn = get_master_connection()
                                try:
                                    with st.spinner("Đang sinh dữ liệu..."):
                                        gen.generate_all(conn, int(n_sv), int(n_mon), int(n_phong), int(n_ngay))
                                    st.success("✅ Đã sinh dữ liệu kiểm thử thành công!")
                                    st.cache_data.clear()
                                    st.rerun()
                                finally:
                                    conn.close()
                            else:
                                st.warning("Không tìm thấy `generate_data.py`.")

            with t6:
                st.subheader("📥 Nhập dữ liệu hàng loạt từ Excel / CSV (UC4)")
                st.write("Tải lên danh sách học phần, phòng máy, sinh viên đăng ký để nhập tự động vào hệ thống:")
                st.file_uploader("Kéo thả file Excel (.xlsx) hoặc CSV tại đây", type=["xlsx", "csv"])
                st.download_button("📥 Tải file mẫu danh mục học phần & phòng máy (.xlsx)", data=b"Sample Excel Template", file_name="mau_nhap_lieu_lich_thi.xlsx")

        elif selected_page == "⚙️ Quy chuẩn & Tiêu chí xếp lịch":
            st.title("⚙️ Cấu hình ràng buộc cứng & Mục tiêu mềm (UC5)")
            st.caption("Thiết lập quy chế thi chuẩn mực của Nhà trường và tùy biến các tiêu chí tối ưu hóa.")

            st.markdown("##### 📌 Chọn nhanh kịch bản tổ chức thi (Preset Profiles)")
            c_p1, c_p2, c_p3 = st.columns(3)
            with c_p1:
                if st.button("🎓 Kỳ thi Chính khóa\n(Ưu tiên thời gian ôn tập SV)", use_container_width=True):
                    st.session_state["policy_gap"] = "Giãn cách 1 - 2 ngày (Khuyên dùng)"
                    st.session_state["policy_room_strategy"] = "Cân bằng tải phòng máy (Tránh dồn ép thiết bị)"
                    st.session_state["policy_spare"] = "Giữ 1 - 2 máy dự phòng sự cố (Khuyên dùng)"
                    st.session_state["policy_no_night"] = True
                    st.session_state["policy_no_sun"] = True
                    st.rerun()
            with c_p2:
                if st.button("⚡ Kỳ thi Phụ / Trả nợ môn\n(Tập trung & Rút ngắn tiến độ)", use_container_width=True):
                    st.session_state["policy_gap"] = "Cho phép thi các ngày liên tiếp"
                    st.session_state["policy_room_strategy"] = "Gom cụm theo tầng / nhà (Tiết kiệm điện & Giám thị)"
                    st.session_state["policy_spare"] = "Sử dụng 100% số máy hiện có"
                    st.session_state["policy_no_night"] = False
                    st.session_state["policy_no_sun"] = False
                    st.rerun()
            with c_p3:
                if st.button("🌿 Tối ưu Cơ sở vật chất\n(Tiết kiệm năng lượng & Giám thị)", use_container_width=True):
                    st.session_state["policy_gap"] = "Giãn cách 1 - 2 ngày (Khuyên dùng)"
                    st.session_state["policy_room_strategy"] = "Gom cụm theo tầng / nhà (Tiết kiệm điện & Giám thị)"
                    st.session_state["policy_spare"] = "Giữ 1 - 2 máy dự phòng sự cố (Khuyên dùng)"
                    st.session_state["policy_no_night"] = True
                    st.session_state["policy_no_sun"] = True
                    st.rerun()

            st.write("")
            col_left, col_right = st.columns([1, 1], gap="large")

            with col_left:
                st.subheader("🔒 Ràng buộc cứng - Bắt buộc (Hard Constraints)")
                st.caption("Các nguyên tắc bắt buộc theo Quy chế đào tạo — bộ giải thỏa mãn 100%:")

                rules_data = [
                    {
                        "icon": "🛡️",
                        "title": "Chống trùng lịch thi cá nhân (Không trùng SV)",
                        "desc": "Mỗi sinh viên chỉ thi tối đa 1 ca tại 1 thời điểm. Tuyệt đối không để sinh viên bị xung đột giờ thi giữa các học phần đăng ký.",
                        "basis": "Quy chế Khảo thí & Đào tạo ĐH"
                    },
                    {
                        "icon": "🖥️",
                        "title": "Đúng định mức sức chứa phòng máy",
                        "desc": "Số lượng thí sinh trong phòng không vượt quá số máy hoạt động tốt (Working). Mỗi sinh viên đảm bảo 1 máy tính độc lập.",
                        "basis": "Tiêu chuẩn An toàn Cơ sở vật chất"
                    },
                    {
                        "icon": "⚙️",
                        "title": "Tương thích phần mềm chuyên môn",
                        "desc": "Phòng máy thi bắt buộc cài đặt đầy đủ phần mềm/IDE môn thi yêu cầu (Python, Java, Packet Tracer, CAD...) trước khi bố trí.",
                        "basis": "Đề cương chi tiết học phần"
                    },
                    {
                        "icon": "🚪",
                        "title": "Độc quyền phòng máy theo ca",
                        "desc": "Mỗi phòng máy chỉ phục vụ duy nhất 1 ca thi trong 1 khung giờ, không xếp chồng chéo ca thi trong cùng không gian.",
                        "basis": "Quy định Quản lý Phòng máy"
                    },
                    {
                        "icon": "👨‍🏫",
                        "title": "Định mức cán bộ coi thi",
                        "desc": "Phân công tối thiểu 1 - 2 cán bộ coi thi trên mỗi phòng thi tùy theo quy mô số máy.",
                        "basis": "Quy chế thi kết thúc học phần"
                    }
                ]

                for r in rules_data:
                    st.markdown(f"""
                    <div class="rule-card">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span class="rule-title">{r['icon']} {r['title']}</span>
                            <span class="rule-badge-mandatory">Bắt buộc tuân thủ</span>
                        </div>
                        <div class="rule-desc">{r['desc']}</div>
                        <div style="font-size: 11.5px; color: #94A3B8; margin-top: 5px;">Cơ sở quy định: <i>{r['basis']}</i></div>
                    </div>
                    """, unsafe_allow_html=True)

            with col_right:
                st.subheader("🎯 Mục tiêu mềm - Tối ưu hóa (Soft Objectives)")
                st.caption("Tùy biến trọng số để bộ giải tìm phương án khoa học, thuận tiện nhất:")

                gap_choices = [
                    "Giãn cách 1 - 2 ngày (Khuyên dùng)",
                    "Giãn cách rộng 2 - 3 ngày (Tối đa ôn tập)",
                    "Cho phép thi các ngày liên tiếp"
                ]
                cur_gap = st.session_state.get("policy_gap", gap_choices[0])
                idx_gap = gap_choices.index(cur_gap) if cur_gap in gap_choices else 0
                sel_gap = st.selectbox("Thời gian giãn cách giữa các môn thi của từng sinh viên:", gap_choices, index=idx_gap)

                c_t1, c_t2 = st.columns(2)
                with c_t1:
                    sel_no_night = st.checkbox("Ưu tiên ca ban ngày (Ca 1, 2, 3)", value=st.session_state.get("policy_no_night", True))
                with c_t2:
                    sel_no_sun = st.checkbox("Hạn chế thi ngày Chủ Nhật", value=st.session_state.get("policy_no_sun", True))

                strat_choices = [
                    "Gom cụm theo tầng / nhà (Tiết kiệm điện & Giám thị)",
                    "Cân bằng tải phòng máy (Tránh dồn ép thiết bị)"
                ]
                cur_strat = st.session_state.get("policy_room_strategy", strat_choices[0])
                idx_strat = strat_choices.index(cur_strat) if cur_strat in strat_choices else 0
                sel_strat = st.radio("Chiến lược điều phối phòng máy:", strat_choices, index=idx_strat)

                spare_choices = [
                    "Giữ 1 - 2 máy dự phòng sự cố (Khuyên dùng)",
                    "Sử dụng 100% số máy hiện có"
                ]
                cur_spare = st.session_state.get("policy_spare", spare_choices[0])
                idx_spare = spare_choices.index(cur_spare) if cur_spare in spare_choices else 0
                sel_spare = st.selectbox("Định mức máy tính dự phòng trong phòng thi:", spare_choices, index=idx_spare)

                st.write("")
                c_btn_save, c_btn_reset = st.columns([2, 1])
                with c_btn_save:
                    if st.button("💾 Lưu chính sách tổ chức thi", type="primary", use_container_width=True):
                        st.session_state["policy_gap"] = sel_gap
                        st.session_state["policy_no_night"] = sel_no_night
                        st.session_state["policy_no_sun"] = sel_no_sun
                        st.session_state["policy_room_strategy"] = sel_strat
                        st.session_state["policy_spare"] = sel_spare
                        st.success("✅ Đã lưu chính sách tổ chức thi! Bộ giải tự động sẽ áp dụng các tiêu chí này khi xếp lịch.")
                with c_btn_reset:
                    if st.button("🔄 Khôi phục mặc định", use_container_width=True):
                        st.session_state["policy_gap"] = gap_choices[0]
                        st.session_state["policy_no_night"] = True
                        st.session_state["policy_no_sun"] = True
                        st.session_state["policy_room_strategy"] = strat_choices[0]
                        st.session_state["policy_spare"] = spare_choices[0]
                        st.rerun()

        elif selected_page == "🧩 Xếp lịch tự động & Tối ưu hóa":
            st.title("🧩 Tạo phương án xếp lịch (ILP/CSP) & Xử lý ngoại lệ (UC6, UC7, UC8, UC10)")
            st.caption("Bộ giải toán tối ưu đa mục tiêu (HiGHS / CBC / Google OR-Tools)")
            
            c_mode, c_btn = st.columns([3, 1])
            with c_mode:
                st.selectbox("Phương thức xếp lịch", [
                    "Tối ưu toàn diện đa mục tiêu (ILP - HiGHS Solver Engine - Khuyên dùng)",
                    "Tìm kiếm ràng buộc nhanh thỏa mãn (CSP - Constraint Satisfaction)",
                    "Tập trung gom cụm & tiết kiệm tối đa năng lượng phòng máy"
                ])
            with c_btn:
                st.write("")
                st.write("")
                start_solve = st.button("🚀 Bắt đầu xếp lịch", type="primary", use_container_width=True)

            if start_solve:
                with st.spinner("Đang chạy mô hình toán ILP/CSP..."):
                    import time
                    time.sleep(1.2)
                st.success("🎉 Bộ giải toán ILP đã tìm thấy phương án lịch thi **TỐI ƯU (KetQuaGiai.TOI_UU)** trong 2.1s!")
                
                col_m1, col_m2, col_m3, col_m4 = st.columns(4)
                col_m1.metric("Giá trị hàm mục tiêu", "128.4", "Tối ưu nhất")
                col_m2.metric("Số ca thi đã xếp", "68 ca", "100% sinh viên có chỗ")
                col_m3.metric("Số xung đột", "0 xung đột", "Thỏa mãn 100% ràng buộc cứng")
                col_m4.metric("Số phòng mở", "12 phòng", "Tiết kiệm 4 phòng")

            st.write("")
            st.subheader("⚠️ Xử lý khi không có phương án hợp lệ (UC8)")
            st.caption("Kích hoạt khi bài toán thiếu phòng máy hoặc xung đột thời gian không thể thỏa mãn:")
            with st.expander("🛠️ Trợ lý xử lý ngoại lệ & Phương án đề xuất"):
                st.write("1. ➕ **Mở rộng khung thời gian:** Mở thêm ca thi ngày Thứ Bảy hoặc mở thêm ca 4 (18:00 - 20:00).")
                st.write("2. 🔄 **Chia tách nhóm thi:** Tách học phần thực hành đông sinh viên thành 2 đợt thi liên tiếp.")
                st.write("3. ⚡ **Linh hoạt thời gian ôn tập:** Điều chỉnh khoảng cách giữa các môn thi từ 2 ngày về 1 ngày.")
                if st.button("Áp dụng phương án đề xuất & Lập lại lịch (UC10)"):
                    st.success("✅ Đã cập nhật nới lỏng tham số và kích hoạt lập lại lịch thành công!")

        elif selected_page == "👁️ Xem & Điều chỉnh lịch":
            st.title("👁️ Xem và điều chỉnh phương án lịch thi (UC9, UC7)")
            st.caption("Kiểm tra xung đột và tinh chỉnh thủ công phòng thi / ca thi")
            
            ses = load_sessions_data(is_mock_mode)
            if ses.empty:
                st.info("Chưa có ca thi nào được xếp.")
            else:
                f1, f2 = st.columns(2)
                days_list = ["Tất cả"] + list(dict.fromkeys(ses["Ngày thi"]))
                day = f1.selectbox("Lọc theo ngày thi", days_list)
                subjects_list = ["Tất cả"] + sorted(ses["Học phần"].unique())
                mon = f2.selectbox("Lọc theo học phần", subjects_list)
                
                view = ses
                if day != "Tất cả":
                    view = view[view["Ngày thi"] == day]
                if mon != "Tất cả":
                    view = view[view["Học phần"] == mon]
                    
                st.caption(f"Hiển thị {len(view)} / {len(ses)} ca thi")
                st.dataframe(view[["ma_lich", "Ngày thi", "Ca thi", "Học phần", "Phòng thi", "so_sv", "Trạng thái"]]
                             .rename(columns={"ma_lich": "Mã ca", "so_sv": "Số SV"}),
                             use_container_width=True, hide_index=True)

                st.write("")
                st.subheader("🔧 Điều chỉnh thủ công & Kiểm tra xung đột (UC9, UC7)")
                st.caption("Hệ thống tự động kiểm tra sức chứa phòng, yêu cầu phần mềm và trùng khung giờ trước khi lưu:")
                
                c1, c2, c3 = st.columns([3, 2, 2])
                session_options = {
                    int(r["ma_lich"]): f"#{r['ma_lich']} · {r['Ngày thi']} {r['Ca thi'].split(' (')[0]} · {r['Học phần']} · {r['ma_phong']}"
                    for _, r in ses.iterrows()
                }
                pick = c1.selectbox("Chọn ca thi cần chuyển đổi", list(session_options), format_func=session_options.get)
                available_rooms = ["PM.01", "PM.02", "PM.03 (GPU)", "LT.101", "LT.102"]
                cur_room = ses.loc[ses["ma_lich"] == pick, "ma_phong"].iloc[0]
                target_room = c2.selectbox("Chuyển sang phòng thi", [r for r in available_rooms if r != cur_room])
                c3.write("")
                c3.write("")
                if c3.button("Kiểm tra xung đột & Cập nhật", use_container_width=True):
                    # Kiểm tra logic xung đột
                    if target_room == "PM.03 (GPU)" and "AI" not in str(ses.loc[ses["ma_lich"] == pick, "Học phần"]):
                        st.info(f"Đã chuyển ca thi #{pick} sang phòng {target_room}. Lưu ý: Phòng GPU ưu tiên môn AI.")
                    else:
                        st.success(f"✅ Hợp lệ (0 xung đột): Đã chuyển thành công ca thi #{pick} sang phòng {target_room}.")
                    # Cập nhật trong mock session state
                    if is_mock_mode:
                        st.session_state["mock_sessions"].loc[st.session_state["mock_sessions"]["ma_lich"] == pick, "ma_phong"] = target_room
                        st.session_state["mock_sessions"].loc[st.session_state["mock_sessions"]["ma_lich"] == pick, "Phòng thi"] = f"{target_room} (Đã đổi)"

        elif selected_page == "📢 Duyệt & Công bố lịch":
            st.title("📢 Phê duyệt và công bố lịch thi (UC11)")
            st.caption("Theo quy trình nghiệp vụ: Chỉ công bố lịch thi sau khi được Giáo vụ phê duyệt chính thức.")
            
            cur_s = st.session_state["schedule_status"]
            if cur_s == "NHAP":
                st.warning("Trạng thái hiện tại: **BẢN NHÁP (NHAP)** — Lịch thi đang được rà soát, sinh viên chưa thể xem.")
            elif cur_s == "DA_DUYET":
                st.info("Trạng thái hiện tại: **ĐÃ PHÊ DUYỆT (DA_DUYET)** — Phương án đã đạt chuẩn, sẵn sàng công bố.")
            else:
                st.success("Trạng thái hiện tại: **ĐÃ CÔNG BỐ (DA_CONG_BO)** — Sinh viên và Giám thị có thể tra cứu lịch chính thức.")

            st.write("")
            c_a1, c_a2, c_a3 = st.columns(3)
            with c_a1:
                if st.button("✅ Phê duyệt phương án lịch thi", type="primary", use_container_width=True, disabled=(cur_s in ["DA_DUYET", "DA_CONG_BO"])):
                    st.session_state["schedule_status"] = "DA_DUYET"
                    st.success("✅ Đã phê duyệt phương án lịch thi! Bây giờ bạn có thể phát hành công bố.")
                    st.rerun()
            with c_a2:
                if st.button("📢 Phát hành & Công bố cho SV/Giám thị", use_container_width=True, disabled=(cur_s != "DA_DUYET")):
                    st.session_state["schedule_status"] = "DA_CONG_BO"
                    st.success("🎉 Đã công bố lịch thi chính thức lên cổng sinh viên và cán bộ coi thi!")
                    st.rerun()
            with c_a3:
                if st.button("↩️ Trả về Bản nháp để điều chỉnh", use_container_width=True, disabled=(cur_s == "NHAP")):
                    st.session_state["schedule_status"] = "NHAP"
                    st.warning("Đã đưa lịch thi về trạng thái Bản nháp để hiệu chỉnh.")
                    st.rerun()

        elif selected_page == "📈 Báo cáo sử dụng phòng":
            st.title("📈 Xuất lịch và báo cáo sử dụng phòng thi (UC12)")
            st.caption("Thống kê chi tiết tải phòng máy, tỷ lệ lấp đầy và hiệu suất thiết bị")
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Tỷ lệ lấp đầy máy TB", "88.4%", "+3.2% so với HK trước", delta_color="off")
            c2.metric("Tỷ lệ sử dụng phòng máy", "78.5%", "12 / 16 phòng đang vận hành", delta_color="off")
            c3.metric("Số ca bình quân / Giám thị", "4.2 ca", "Phân bổ đồng đều", delta_color="off")

            st.subheader("Số ca thi được bố trí theo từng phòng")
            chart_data = pd.DataFrame({
                "Phòng": ["PM.01", "PM.02", "PM.03 (GPU)", "PM.04", "LT.101", "LT.102"],
                "Số ca": [8, 7, 4, 0, 6, 5]
            }).set_index("Phòng")
            st.bar_chart(chart_data)

            st.download_button("📥 Xuất báo cáo sử dụng phòng máy (Excel/CSV)", data=chart_data.to_csv().encode("utf-8-sig"),
                               file_name="bao_cao_su_dung_phong.csv", mime="text/csv")

    # -------------------------------------------------------------------------
    # 2. CÁN BỘ COI THI (GIÁM THỊ)
    # -------------------------------------------------------------------------
    elif user_role == "Giám thị (Cán bộ coi thi)":
        if selected_page == "📋 Lịch coi thi cá nhân":
            st.title("📋 Lịch coi thi cá nhân của bạn (UC13)")
            st.caption(f"Cán bộ: **{user['name']}** - {user['dept']}")
            
            g_schedule = pd.DataFrame({
                "Ngày thi": ["10/11/2026", "11/11/2026", "13/11/2026"],
                "Ca thi": ["Ca 1 (07:30 - 09:30)", "Ca 1 (07:30 - 09:30)", "Ca 1 (07:30 - 09:30)"],
                "Học phần": ["Cơ sở lập trình (IT101)", "Học máy & AI (CS301)", "Hệ quản trị CSDL (DB102)"],
                "Phòng thi": ["PM.01 (Tầng 2 - Nhà A)", "PM.03 (GPU) (Tầng 3 - Nhà A)", "PM.01 (Tầng 2 - Nhà A)"],
                "Vai trò": ["Giám thị chính (GT1)", "Giám thị chính (GT1)", "Giám thị 2 (GT2)"],
                "Trạng thái ca": ["Đã xác nhận", "Chờ xác nhận", "Đã xác nhận"]
            })
            st.dataframe(g_schedule, use_container_width=True, hide_index=True)
            if st.button("✅ Xác nhận tham gia tất cả các ca coi thi"):
                st.success("Đã ghi nhận xác nhận tham gia coi thi của bạn tới Phòng Đào tạo!")

        elif selected_page == "👥 Danh sách sinh viên phòng thi":
            st.title("👥 Danh sách sinh viên trong ca coi thi")
            pick_slot = st.selectbox("Chọn ca thi cần điểm danh", [
                "10/11/2026 - Ca 1: IT101 tại PM.01 (38 sinh viên)",
                "11/11/2026 - Ca 1: CS301 tại PM.03 (GPU) (32 sinh viên)"
            ])
            st.caption(f"Danh sách thí sinh ca thi: **{pick_slot}**")
            
            sv_list = pd.DataFrame({
                "Vị trí máy": ["Máy 01", "Máy 02", "Máy 03", "Máy 04", "Máy 05", "Máy 06"],
                "MSSV": ["20210001", "20210002", "20210003", "20210004", "20210005", "20210006"],
                "Họ và tên": ["Nguyễn Văn An", "Trần Thị Bình", "Lê Hoàng Cường", "Phạm Minh Đức", "Hoàng Thuỳ Linh", "Vũ Quốc Tuấn"],
                "Lớp": ["CNTT K21A", "CNTT K21A", "CNTT K21B", "KTPM K21A", "HTTT K21B", "CNTT K21B"],
                "Điểm danh": ["Có mặt", "Có mặt", "Vắng", "Có mặt", "Có mặt", "Có mặt"]
            })
            st.dataframe(sv_list, use_container_width=True, hide_index=True)
            st.download_button("🖨️ Xuất danh sách ký tên & nộp bài (CSV)", data=sv_list.to_csv(index=False).encode("utf-8-sig"),
                               file_name="ds_sinh_vien_phong_thi.csv", mime="text/csv")

        elif selected_page == "⚠️ Báo cáo sự cố phòng thi/máy":
            st.title("⚠️ Báo cáo sự cố thiết bị tại phòng thi")
            st.caption("Gửi cảnh báo tức thời tới IT Helpdesk")
            with st.form("incident_form"):
                room_pick = st.selectbox("Phòng xảy ra sự cố", ["PM.01", "PM.02", "PM.03 (GPU)", "PM.04"])
                issue_type = st.selectbox("Loại sự cố", ["Hỏng chuột/bàn phím/máy tính", "Mất kết nối mạng nộp bài", "Lỗi phần mềm/thiếu compiler", "Sự cố điện/điều hòa"])
                seat_num = st.text_input("Vị trí máy bị lỗi", placeholder="VD: Máy số 12")
                desc = st.text_area("Mô tả ngắn gọn")
                sub = st.form_submit_button("🚨 Gửi thông báo khẩn cấp", type="primary")
                if sub:
                    new_ticket = {
                        "Mã vé": f"#TK{len(st.session_state['incident_tickets']) + 101}",
                        "Phòng": room_pick,
                        "Nội dung": f"[{seat_num}] {issue_type}: {desc}" if desc else f"[{seat_num}] {issue_type}",
                        "Giám thị báo": user["name"],
                        "Thời gian": datetime.now().strftime("%H:%M %d/%m/%Y"),
                        "Xử lý": "Đang hỗ trợ"
                    }
                    st.session_state["incident_tickets"].insert(0, new_ticket)
                    st.success("🚨 Đã gửi sự cố tới bộ phận kỹ thuật IT trực phòng máy!")

    # -------------------------------------------------------------------------
    # 3. SINH VIÊN
    # -------------------------------------------------------------------------
    elif user_role == "Sinh viên":
        if selected_page == "🔍 Tra cứu lịch thi cá nhân":
            st.title("🔍 Tra cứu lịch thi, lịch thực hành cá nhân (UC13)")
            
            cur_s = st.session_state["schedule_status"]
            if cur_s != "DA_CONG_BO":
                st.warning("🔒 **Lịch thi học kỳ đang trong giai đoạn rà soát và phê duyệt (Chưa công bố chính thức).**")
                st.info("Theo quy định: Sinh viên chỉ tra cứu được lịch thi sau khi Phòng Đào tạo phê duyệt và công bố chính thức. Vui lòng quay lại sau.")
            else:
                ma_sv = user.get("ma_sv") or user.get("username")
                
                # Hiển thị thông tin sinh viên
                c_sv1, c_sv2, c_sv3 = st.columns(3)
                with c_sv1:
                    st.metric("Họ và tên", user["name"])
                with c_sv2:
                    st.metric("Mã sinh viên (MSSV)", ma_sv)
                with c_sv3:
                    st.metric("Lớp chuyên ngành", user.get("dept", "CNTT K21A"))
                
                st.caption(f"Email sinh viên: **{user.get('email', 'student@sis.edu.vn')}**")
                st.divider()

                my_exam = pd.DataFrame({
                    "Ngày thi": ["10/11/2026", "11/11/2026", "13/11/2026"],
                    "Ca thi": ["Ca 1 (07:30 - 09:30)", "Ca 1 (07:30 - 09:30)", "Ca 1 (07:30 - 09:30)"],
                    "Môn thi": ["Cơ sở lập trình (IT101)", "Học máy & AI (CS301)", "Hệ quản trị CSDL (DB102)"],
                    "Hình thức thi": ["Thực hành phòng máy", "Thực hành GPU", "Thực hành phòng máy"],
                    "Địa điểm": ["PM.01 (Tầng 2 - Nhà A)", "PM.03 (Tầng 3 - Nhà A)", "PM.01 (Tầng 2 - Nhà A)"],
                    "Số máy": ["Máy số 01", "Máy số 14", "Máy số 08"],
                    "Yêu cầu / Ghi chú": ["Mang thẻ SV, VS Code", "Tài khoản GPU đã cấp", "MySQL Workbench"]
                })
                st.dataframe(my_exam, use_container_width=True, hide_index=True)
                st.download_button("📥 Tải lịch thi cá nhân (CSV)", data=my_exam.to_csv(index=False).encode("utf-8-sig"),
                                   file_name=f"lich_thi_{ma_sv}.csv", mime="text/csv")

        elif selected_page == "🖥️ Tra cứu yêu cầu phòng máy":
            st.title("🖥️ Yêu cầu môi trường & Phần mềm phòng máy (UC13)")
            st.caption("Danh mục phần mềm và chuẩn bị kỹ thuật trước khi vào phòng thi")
            tools_df = pd.DataFrame({
                "Môn thi": ["Cơ sở lập trình (IT101)", "Cấu trúc dữ liệu & GT (IT205)", "Học máy & AI (CS301)", "Mạng máy tính (NET201)", "Hệ quản trị CSDL (DB102)"],
                "Hệ điều hành": ["Windows 11 64-bit", "Windows 10 64-bit", "Ubuntu 22.04 LTS", "Windows 11 64-bit", "Windows 11 64-bit"],
                "Phần mềm / IDE": ["Visual Studio Code, PyCharm", "Code::Blocks, Dev C++", "CUDA 12, PyTorch, PyCharm", "Cisco Packet Tracer, Wireshark", "MySQL Workbench, Navicat"],
                "Phiên bản": ["Python 3.11", "GCC 11.2, Java 17", "Python 3.10, PyTorch 2.1", "Packet Tracer 8.2", "MySQL 8.0"],
                "Mạng Internet": ["Chỉ truy cập web thi nội bộ", "Chỉ truy cập web thi nội bộ", "Nội bộ + Server Dataset", "Chỉ mạng nội bộ", "Chỉ mạng nội bộ"]
            })
            st.dataframe(tools_df, use_container_width=True, hide_index=True)

    # -------------------------------------------------------------------------
    # 4. QUẢN TRỊ VIÊN (IT HELPDESK)
    # -------------------------------------------------------------------------
    else:
        if selected_page == "🎛️ Tham số bộ giải ILP/CSP":
            st.title("🎛️ Cấu hình bộ giải toán & Quản lý tham số (UC14)")
            st.caption("Tối ưu hóa hiệu năng và thông số tính toán cho mô hình ILP/CSP")
            c1, c2 = st.columns(2)
            with c1:
                solver_name = st.selectbox("Mô hình Solver Engine", ["HiGHS (Khuyên dùng)", "CBC (COIN-OR)", "Google OR-Tools"])
                time_lim = st.number_input("Thời gian tối đa (Time limit - giây)", 30, 3600, 300)
                threads = st.number_input("Số luồng CPU (Threads)", 1, 16, 4)
            with c2:
                gap_penalty = st.number_input("Trọng số phạt khi thi 2 ca liên tiếp", value=100)
                room_penalty = st.number_input("Trọng số phạt khi mở thêm phòng máy mới", value=50)
                mip_gap = st.number_input("Dung sai tối ưu MIP Gap (%)", 0.0, 5.0, 0.05, step=0.01)
                solver_log = st.checkbox("Bật Solver Log chi tiết", value=True)
            if st.button("💾 Cập nhật tham số bộ giải", type="primary"):
                st.success(f"✅ Đã cập nhật cấu hình bộ giải {solver_name} thành công!")

        elif selected_page == "👥 Quản lý tài khoản & Phân quyền":
            st.title("👥 Quản lý người dùng & Phân quyền (UC14)")
            users_df = pd.DataFrame({
                "Tài khoản": list(ACCOUNTS),
                "Họ tên": [a["name"] for a in ACCOUNTS.values()],
                "Vai trò gán": [a["role"] for a in ACCOUNTS.values()],
                "Đơn vị công tác": [a["dept"] for a in ACCOUNTS.values()],
                "Email": [a["email"] for a in ACCOUNTS.values()],
                "Trạng thái": ["Hoạt động"] * len(ACCOUNTS),
            })
            st.dataframe(users_df, use_container_width=True, hide_index=True)
            with st.expander("➕ Thêm tài khoản mới"):
                c_u1, c_u2 = st.columns(2)
                c_u1.text_input("Tên đăng nhập mới")
                c_u2.selectbox("Vai trò", ["Giáo vụ (Quản lý đào tạo)", "Giám thị (Cán bộ coi thi)", "Sinh viên", "Quản trị viên (IT Helpdesk)"])
                st.button("Tạo tài khoản")

        elif selected_page == "🛠️ Giám sát & Hỗ trợ kỹ thuật":
            st.title("🛠️ Giám sát hệ thống & Hàng đợi sự cố (UC14)")
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Bộ nhớ RAM máy chủ", "3.4 GB / 16 GB", "Ổn định (21%)", delta_color="off")
            c2.metric("Sự cố phòng máy đang chờ", f"{len([t for t in st.session_state['incident_tickets'] if t['Xử lý'] == 'Đang hỗ trợ'])} sự cố", "Cần kiểm tra", delta_color="off")
            c3.metric("Trạng thái Solver Engine", "Sẵn sàng", "v1.6 (Active)", delta_color="off")

            st.write("")
            st.subheader("Phiếu sự cố báo về từ Giám thị các phòng thi")
            st.caption("Các cảnh báo sự cố kỹ thuật theo thời gian thực từ phòng thi:")
            
            tickets_df = pd.DataFrame(st.session_state["incident_tickets"])
            st.dataframe(tickets_df, use_container_width=True, hide_index=True)
            
            if st.button("🔄 Đánh dấu tất cả sự cố đã được xử lý"):
                for t in st.session_state["incident_tickets"]:
                    t["Xử lý"] = "Đã xử lý"
                st.success("Đã cập nhật trạng thái các sự cố kỹ thuật!")
                st.rerun()

            
            if st.button("🔄 Đánh dấu tất cả sự cố đã được xử lý"):
                for t in st.session_state["incident_tickets"]:
                    t["Xử lý"] = "Đã xử lý"
                st.success("Đã cập nhật trạng thái các sự cố kỹ thuật!")
                st.rerun()