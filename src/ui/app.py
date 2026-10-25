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
    if get_master_connection is None:
        return False, f"Không import được src.backend.db_helper: {DB_IMPORT_ERROR}"
    try:
        _run_query("SELECT COUNT(*) AS n FROM sinh_vien")
        return True, ""
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


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


def load_overview():
    return query_df("""
        SELECT (SELECT COUNT(*) FROM mon_thi) AS mon,
               (SELECT COUNT(*) FROM phong_may) AS phong,
               (SELECT COUNT(*) FROM phong_may WHERE tinh_trang = 'Working') AS phong_ok,
               (SELECT COUNT(*) FROM sinh_vien) AS sv,
               (SELECT COUNT(*) FROM lich_thi) AS lich,
               (SELECT COUNT(*) FROM dang_ky_thi) AS dk,
               (SELECT COUNT(*) FROM khung_gio) AS khung""").iloc[0]


def load_sessions():
    return query_df(f"""
        SELECT lt.ma_lich, {SLOT_SQL}, lt.ma_mon, mt.ten_mon, lt.ma_phong,
               pm.suc_chua, pm.toa_nha, pm.tang,
               (SELECT COUNT(*) FROM dang_ky_thi dk WHERE dk.ma_lich = lt.ma_lich) AS so_sv
        FROM lich_thi lt
        JOIN khung_gio kg ON kg.ma_khung = lt.ma_khung
        JOIN mon_thi mt ON mt.ma_mon = lt.ma_mon
        JOIN phong_may pm ON pm.ma_phong = lt.ma_phong
        ORDER BY kg.ngay_thi, kg.ca_thi, lt.ma_phong""")


def move_session(ma_lich: int, new_room: str):
    """Đổi phòng cho 1 ca thi sau khi kiểm tra: phòng hoạt động, đủ chỗ, đủ phần mềm, không trùng ca."""
    conn = get_master_connection()
    try:
        cur = conn.cursor()

        def fetch(sql, args):
            cur.execute(sql, args)
            return _rows(cur)[0]

        s = fetch("SELECT ma_mon, ma_khung FROM lich_thi WHERE ma_lich = %s", (ma_lich,))[0]
        room = fetch("SELECT tinh_trang, suc_chua FROM phong_may WHERE ma_phong = %s", (new_room,))[0]
        n = fetch("SELECT COUNT(*) AS n FROM dang_ky_thi WHERE ma_lich = %s", (ma_lich,))[0]["n"]
        errors = []
        if room["tinh_trang"] != "Working":
            errors.append("Phòng đang bảo trì.")
        if n > room["suc_chua"]:
            errors.append(f"Phòng chỉ có {room['suc_chua']} máy nhưng ca thi có {n} sinh viên.")
        missing = [r["ten_pm"] for r in fetch(
            """SELECT p.ten_pm FROM mon_thi_phan_mem r JOIN phan_mem p ON p.ma_pm = r.ma_pm
               WHERE r.ma_mon = %s AND r.ma_pm NOT IN
                     (SELECT ma_pm FROM phong_may_phan_mem WHERE ma_phong = %s)""",
            (s["ma_mon"], new_room))]
        if missing:
            errors.append("Phòng thiếu phần mềm: " + ", ".join(missing))
        if fetch("SELECT 1 AS x FROM lich_thi WHERE ma_phong = %s AND ma_khung = %s AND ma_lich <> %s",
                 (new_room, s["ma_khung"], ma_lich)):
            errors.append("Phòng đã có ca thi khác trong cùng khung giờ.")
        if errors:
            return False, errors
        cur.execute("UPDATE lich_thi SET ma_phong = %s WHERE ma_lich = %s", (new_room, ma_lich))
        conn.commit()
        return True, [f"Đã chuyển ca thi #{ma_lich} sang phòng {new_room}."]
    finally:
        conn.close()


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

        # Hộp thông tin cá nhân của người dùng đã xác thực

        st.markdown(f"""
        <div class="user-profile-box">
            <div style="font-weight: 700; font-size: 15px; color: #1E293B;">👤 {user['name']}</div>
            <div style="font-size: 13px; color: #64748B;">{user['dept']}</div>
            <div style="margin-top: 8px;"><span class="role-badge">{user_role}</span></div>
        </div>
        """, unsafe_allow_html=True)
        
        # Nút Đăng xuất

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

    # -------------------------------------------------------------------------
    # KHÔNG GIAN LÀM VIỆC THEO VAI TRÒ
    # -------------------------------------------------------------------------

    # 1. GIÁO VỤ (QUẢN LÝ ĐÀO TẠO)
    if user_role == "Giáo vụ (Quản lý đào tạo)":
        if selected_page == "📊 Tổng quan điều hành":
            st.title("📊 Tổng quan điều hành kỳ thi")
            st.caption(f"Xin chào **{user['name']}** - Phòng Đào tạo")

            ov = load_overview()
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Tổng học phần thi", f"{int(ov['mon'])} môn", f"{int(ov['sv'])} sinh viên", delta_color="off")
            c2.metric("Phòng máy khả dụng", f"{int(ov['phong_ok'])} / {int(ov['phong'])} phòng",
                      f"{int(ov['phong'] - ov['phong_ok'])} phòng bảo trì", delta_color="off")
            c3.metric("Ca thi đã xếp", f"{int(ov['lich'])} ca", f"{int(ov['khung'])} khung giờ", delta_color="off")
            c4.metric("Lượt đăng ký thi", f"{int(ov['dk'])}", "Đã xếp chỗ ngồi", delta_color="off")

            if int(ov["lich"]) == 0:
                st.info(EMPTY_MSG)
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
                        GROUP BY kg.ngay_thi ORDER BY kg.ngay_thi""")
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
                    over = load_sessions()
                    over = over[over["so_sv"] > over["suc_chua"]]
                    if len(over):
                        st.error(f"❌ {len(over)} ca thi vượt sức chứa phòng.")
                    else:
                        st.info("💡 Không có ca thi nào vượt sức chứa phòng.")

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
                            WHERE lt.ma_mon = mt.ma_mon) AS so_sv
                    FROM mon_thi mt ORDER BY mt.ma_mon""")
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
                           (SELECT COUNT(*) FROM lich_thi lt WHERE lt.ma_phong = pm.ma_phong) AS so_ca
                    FROM phong_may pm ORDER BY pm.ma_phong""")
                if room_df.empty:
                    st.info(EMPTY_MSG)
                else:
                    only_ok = st.checkbox("Chỉ hiện phòng đang hoạt động", value=False)
                    if only_ok:
                        room_df = room_df[room_df["tinh_trang"] == "Working"]
                    st.dataframe(room_df.rename(columns={
                        "ma_phong": "Phòng", "toa_nha": "Tòa", "tang": "Tầng", "suc_chua": "Số máy",
                        "he_dieu_hanh": "Hệ điều hành", "tinh_trang": "Tình trạng",
                        "phan_mem": "Phần mềm cài đặt", "so_ca": "Số ca thi"}),
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
                           (SELECT COUNT(*) FROM lich_thi lt WHERE lt.ma_khung = kg.ma_khung) AS so_phong
                    FROM khung_gio kg ORDER BY kg.ngay_thi, kg.ca_thi""")
                if kg_df.empty:
                    st.info(EMPTY_MSG)
                else:
                    kg_df["Ngày thi"] = fmt_dates(kg_df["ngay_iso"])
                    st.dataframe(kg_df[["ma_khung", "Ngày thi", "ca_thi", "gio_bd", "gio_kt", "so_phong"]].rename(columns={
                        "ma_khung": "Mã khung", "ca_thi": "Ca", "gio_bd": "Bắt đầu", "gio_kt": "Kết thúc",
                        "so_phong": "Số phòng đang dùng"}), use_container_width=True, hide_index=True)
            with t5:
                st.subheader("Sinh dữ liệu mẫu vào CSDL")
                st.caption("Gọi `generate_all()` trong `generate_data.py`. Dữ liệu cũ được thay thế trong **một giao dịch** "
                           "(lỗi giữa chừng sẽ rollback, dữ liệu cũ không bị mất).")
                if "gen_summary" in st.session_state:
                    s = st.session_state.pop("gen_summary")
                    st.success(f"✅ Đã sinh: {s['students']} sinh viên, {s['subjects']} môn, {s['rooms']} phòng "
                               f"({s['rooms_maintenance']} bảo trì), {s['slots']} khung giờ, {s['sessions']} ca thi, "
                               f"{s['registrations']} lượt đăng ký.")
                    if s["unscheduled"]:
                        st.warning(f"{s['unscheduled']} lượt đăng ký chưa xếp được — tăng số phòng hoặc số ngày thi.")
                with st.form("gen_form"):
                    g1, g2 = st.columns(2)
                    n_sv = g1.number_input("Số sinh viên", 10, 20000, 300, step=50)
                    n_mon = g2.number_input("Số môn thi (tối đa 22)", 1, 22, 12)
                    n_phong = g1.number_input("Số phòng máy", 3, 500, 10)
                    n_ngay = g2.number_input("Số ngày thi", 1, 30, 5)
                    seed_txt = st.text_input("Seed (để trống = ngẫu nhiên)", value="")
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
                            with st.spinner("Đang sinh và ghi dữ liệu..."):
                                summary = gen.generate_all(
                                    conn, int(n_sv), int(n_mon), int(n_phong), int(n_ngay),
                                    seed=int(seed_txt) if seed_txt.strip() else None, log=lambda *_: None)
                        except Exception as exc:  # noqa: BLE001
                            st.error(f"Sinh dữ liệu thất bại (đã rollback): {exc}")
                        else:
                            st.session_state["gen_summary"] = summary
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
            ses = load_sessions()
            if ses.empty:
                st.info(EMPTY_MSG)
            else:
                ses["Ngày thi"] = fmt_dates(ses["ngay_iso"])
                ses["Ca thi"] = slot_labels(ses)
                ses["Học phần"] = ses["ten_mon"] + " (" + ses["ma_mon"] + ")"
                ses["Phòng thi"] = ses["ma_phong"] + " (" + ses["suc_chua"].astype(str) + " máy)"
                ses["Trạng thái"] = ses.apply(lambda r: "✅ Hợp lệ" if r["so_sv"] <= r["suc_chua"] else "❌ Vượt sức chứa", axis=1)

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
                st.caption("Hệ thống kiểm tra: phòng hoạt động, đủ chỗ, đủ phần mềm, không trùng khung giờ trước khi cập nhật.")
                labels = {
                    int(r["ma_lich"]): f"#{r['ma_lich']} · {r['Ngày thi']} {r['Ca thi'].split(' (')[0]} · {r['ma_mon']} · {r['ma_phong']}"
                    for _, r in ses.iterrows()}
                c1, c2, c3 = st.columns([3, 2, 2])
                pick = c1.selectbox("Chọn ca thi đổi phòng", list(labels), format_func=labels.get)
                rooms = query_df("SELECT ma_phong FROM phong_may WHERE tinh_trang = 'Working' ORDER BY ma_phong")["ma_phong"].tolist()
                cur_room = ses.loc[ses["ma_lich"] == pick, "ma_phong"].iloc[0]
                new_room = c2.selectbox("Chuyển sang phòng", [r for r in rooms if r != cur_room])
                c3.write("")
                c3.write("")
                if c3.button("Kiểm tra xung đột & Cập nhật", use_container_width=True):
                    ok, msgs = move_session(int(pick), new_room)
                    if ok:
                        st.cache_data.clear()
                        st.success(msgs[0])
                    else:
                        for m in msgs:
                            st.error(m)

        elif selected_page == "📢 Duyệt & Công bố lịch":
            st.title("📢 Phê duyệt & Công bố lịch thi")
            st.info("Trạng thái hiện tại: **CHỜ PHÊ DUYỆT CHÍNH THỨC** (Chỉ công bố sau khi được ký duyệt)")
            c_a1, c_a2 = st.columns(2)
            c_a1.button("✅ Phê duyệt phương án lịch thi", type="primary", use_container_width=True)
            c_a2.button("📢 Phát hành & Công bố cho SV/Giám thị", use_container_width=True)

        elif selected_page == "📈 Báo cáo sử dụng phòng":
            st.title("📈 Báo cáo & Thống kê sử dụng phòng máy")
            use = query_df("""
                SELECT pm.ma_phong, pm.suc_chua, pm.tinh_trang,
                       COUNT(lt.ma_lich) AS so_ca, COALESCE(SUM(x.n), 0) AS tong_sv
                FROM phong_may pm
                LEFT JOIN lich_thi lt ON lt.ma_phong = pm.ma_phong
                LEFT JOIN (SELECT ma_lich, COUNT(*) AS n FROM dang_ky_thi GROUP BY ma_lich) x ON x.ma_lich = lt.ma_lich
                GROUP BY pm.ma_phong, pm.suc_chua, pm.tinh_trang ORDER BY pm.ma_phong""")
            ov = load_overview()
            if use.empty or int(ov["lich"]) == 0:
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
            st.info("Schema hiện chưa có bảng phân công giám thị, nên dưới đây là **toàn bộ ca thi** trong hệ thống.")
            ses = load_sessions()
            if ses.empty:
                st.info(EMPTY_MSG)
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
            ses = load_sessions()
            if ses.empty:
                st.info(EMPTY_MSG)
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
            first = query_df("SELECT ma_sv FROM dang_ky_thi ORDER BY ma_sv LIMIT 1")
            default_id = first["ma_sv"].iloc[0] if len(first) else ""
            ma_sv = st.text_input("Mã sinh viên (MSSV)", value=default_id, placeholder="VD: SV20230001").strip()
            if not ma_sv:
                st.info(EMPTY_MSG)
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
                        JOIN lich_thi lt ON lt.ma_lich = dk.ma_lich
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
            counts = query_df("""
                SELECT 'sinh_vien' AS bang, COUNT(*) AS so_ban_ghi FROM sinh_vien
                UNION ALL SELECT 'mon_thi', COUNT(*) FROM mon_thi
                UNION ALL SELECT 'phong_may', COUNT(*) FROM phong_may
                UNION ALL SELECT 'phan_mem', COUNT(*) FROM phan_mem
                UNION ALL SELECT 'phong_may_phan_mem', COUNT(*) FROM phong_may_phan_mem
                UNION ALL SELECT 'mon_thi_phan_mem', COUNT(*) FROM mon_thi_phan_mem
                UNION ALL SELECT 'khung_gio', COUNT(*) FROM khung_gio
                UNION ALL SELECT 'lich_thi', COUNT(*) FROM lich_thi
                UNION ALL SELECT 'dang_ky_thi', COUNT(*) FROM dang_ky_thi""")
            maint_n = int(query_df("SELECT COUNT(*) AS n FROM phong_may WHERE tinh_trang <> 'Working'")["n"].iloc[0])
            c1, c2, c3 = st.columns(3)
            c1.metric("Kết nối CSDL", "Hoạt động", "quan_ly_thi", delta_color="off")
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