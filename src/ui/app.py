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
        "name": "Nguyễn Văn An",
        "role": "Sinh viên",
        "dept": "Lớp CNTT K21A - MSSV: 20210001",
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
            
        st.divider()
        
        # Phân quyền danh mục Menu chỉ dành riêng cho vai trò đã đăng nhập
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
    # KHÔNG GIAN LÀM VIỆC THEO VAI TRÒ
    # -------------------------------------------------------------------------
    
    # 1. GIÁO VỤ (QUẢN LÝ ĐÀO TẠO)
    if user_role == "Giáo vụ (Quản lý đào tạo)":
        if selected_page == "📊 Tổng quan điều hành":
            st.title("📊 Tổng quan điều hành kỳ thi")
            st.caption(f"Xin chào **{user['name']}** - Phòng Đào tạo")
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Tổng học phần thi", "42 môn", "+5 môn so với HK trước")
            c2.metric("Phòng thi khả dụng", "28 phòng", "12 phòng máy, 16 lý thuyết")
            c3.metric("Giám thị đã sẵn sàng", "64 cán bộ", "Đã phân công 48")
            c4.metric("Trạng thái đợt thi", "Chờ phê duyệt", "Đã chạy giải thuật 100%")

            st.markdown("---")
            col_left, col_right = st.columns([2, 1])
            with col_left:
                st.subheader("Tiến trình đợt xếp lịch (Service Blueprint)")
                steps_df = pd.DataFrame({
                    "Giai đoạn": ["1. Chuẩn bị dữ liệu", "2. Thiết lập ràng buộc", "3. Tạo & kiểm tra lịch", "4. Duyệt & Công bố", "5. Tra cứu & Báo cáo"],
                    "Hành động": [
                        "Nhập học phần, phòng máy, giám thị từ Excel",
                        "Cấu hình ràng buộc cứng/mềm",
                        "Bộ giải ILP/CSP tối ưu lịch",
                        "Phê duyệt & phát hành lịch",
                        "Sinh viên & Giám thị xem lịch"
                    ],
                    "Trạng thái": ["✅ Hoàn tất", "✅ Hoàn tất", "⚡ Đã sinh phương án #1", "⏳ Chờ ký duyệt", "🔒 Chưa mở"]
                })
                st.dataframe(steps_df, use_container_width=True, hide_index=True)
            with col_right:
                st.subheader("Cảnh báo nhanh")
                st.info("💡 **Gợi ý:** Có 2 môn thực hành AI yêu cầu phòng máy GPU.")
                st.warning("⚠️ **Lưu ý:** Ngày 15/11 cần bổ sung thêm 2 giám thị dự phòng.")

        elif selected_page == "📁 Quản lý dữ liệu":
            st.title("📁 Quản lý dữ liệu gốc")
            st.caption("Nhập và quản lý danh mục học phần, phòng thi/máy và cán bộ coi thi")
            t1, t2, t3, t4 = st.tabs(["📘 Học phần & Nhóm SV", "🏫 Phòng thi & Cấu hình máy", "👨‍🏫 Giám thị & Khung giờ", "📥 Nhập dữ liệu (Excel/CSV)"])
            with t1:
                st.subheader("Danh mục học phần")
                hp_df = pd.DataFrame({
                    "Mã HP": ["IT101", "IT205", "CS301", "MATH101"],
                    "Tên học phần": ["Cơ sở lập trình", "Cấu trúc dữ liệu", "Học máy & AI", "Toán rời rạc"],
                    "Số SV": [120, 85, 45, 150],
                    "Hình thức thi": ["Thực hành máy", "Thực hành máy", "Thực hành GPU", "Viết trên giấy"],
                    "Yêu cầu phần mềm": ["VS Code, Python", "Dev C++, Java", "CUDA, PyTorch", "Không"]
                })
                st.dataframe(hp_df, use_container_width=True, hide_index=True)
                st.button("➕ Thêm học phần")
            with t2:
                st.subheader("Danh mục phòng thi & cấu hình")
                room_df = pd.DataFrame({
                    "Phòng": ["PM.01", "PM.02", "PM.03 (GPU)", "LT.101"],
                    "Loại": ["Phòng máy", "Phòng máy", "Phòng máy cao cấp", "Lý thuyết"],
                    "Số máy / Sức chứa": [40, 45, 35, 80],
                    "Cấu hình": ["Core i5, 16GB", "Core i5, 8GB", "Core i7, RTX 4060", "Bàn ghế tiêu chuẩn"],
                    "Tình trạng": ["Sẵn sàng", "Sẵn sàng", "Sẵn sàng", "Sẵn sàng"]
                })
                st.dataframe(room_df, use_container_width=True, hide_index=True)
            with t3:
                st.subheader("Danh sách giám thị")
                proctors_df = pd.DataFrame({
                    "Mã CB": ["CB001", "CB002", "CB003"],
                    "Họ tên": ["TS. Nguyễn Văn A", "ThS. Trần Thị B", "ThS. Lê Hoàng C"],
                    "Bộ môn": ["CNTT", "CNTT", "Toán - Tin"],
                    "Khung giờ rảnh": ["Tất cả ca", "Chỉ ca Sáng", "Chỉ ca Chiều"]
                })
                st.dataframe(proctors_df, use_container_width=True, hide_index=True)
            with t4:
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
                st.checkbox("Phân công tối thiểu 1-2 giám thị / phòng", value=True, disabled=True)
            with col2:
                st.subheader("🎯 Mục tiêu mềm (Ưu tiên tối ưu)")
                st.slider("Khoảng cách tối thiểu giữa 2 môn của SV (ngày)", 1, 5, 2)
                st.slider("Độ ưu tiên cân bằng số ca coi thi của Giám thị", 1, 10, 8)
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
            sch_df = pd.DataFrame({
                "Ngày thi": ["10/11/2026", "10/11/2026", "11/11/2026"],
                "Ca thi": ["Ca 1 (07:30 - 09:30)", "Ca 2 (09:45 - 11:45)", "Ca 1 (07:30 - 09:30)"],
                "Học phần": ["Cơ sở lập trình (IT101)", "Cấu trúc dữ liệu (IT205)", "Toán rời rạc (MATH101)"],
                "Phòng thi": ["PM.01 (40 máy)", "PM.02 (45 máy)", "LT.101 (80 chỗ)"],
                "Số SV": [38, 42, 75],
                "Giám thị": ["TS. Nguyễn Văn A", "ThS. Trần Thị B", "TS. Phạm Minh D"],
                "Trạng thái": ["✅ Hợp lệ", "✅ Hợp lệ", "✅ Hợp lệ"]
            })
            st.dataframe(sch_df, use_container_width=True, hide_index=True)
            st.subheader("Điều chỉnh thủ công (Fine-tuning)")
            c1, c2, c3 = st.columns(3)
            c1.selectbox("Chọn học phần đổi phòng", ["IT101 - Cơ sở lập trình"])
            c2.selectbox("Chuyển sang phòng", ["PM.02", "PM.03"])
            c3.write("")
            c3.button("Kiểm tra xung đột & Cập nhật")

        elif selected_page == "📢 Duyệt & Công bố lịch":
            st.title("📢 Phê duyệt & Công bố lịch thi")
            st.info("Trạng thái hiện tại: **CHỜ PHÊ DUYỆT CHÍNH THỨC** (Chỉ công bố sau khi được ký duyệt)")
            c_a1, c_a2 = st.columns(2)
            c_a1.button("✅ Phê duyệt phương án lịch thi", type="primary", use_container_width=True)
            c_a2.button("📢 Phát hành & Công bố cho SV/Giám thị", use_container_width=True)

        elif selected_page == "📈 Báo cáo sử dụng phòng":
            st.title("📈 Báo cáo & Thống kê sử dụng phòng máy")
            c1, c2, c3 = st.columns(3)
            c1.metric("Tỷ lệ lấp đầy máy TB", "87.5%", "+3.2% so với HK trước")
            c2.metric("Tổng số giờ máy chạy", "142 giờ", "Trong 10 ngày thi")
            c3.metric("Số ca bình quân / Giám thị", "4.6 ca", "Phân bổ đồng đều")

    # 2. CÁN BỘ COI THI (GIÁM THỊ)
    elif user_role == "Giám thị (Cán bộ coi thi)":
        if selected_page == "📋 Lịch coi thi cá nhân":
            st.title("📋 Lịch coi thi cá nhân của bạn")
            st.caption(f"Cán bộ: **{user['name']}** - {user['dept']}")
            g_schedule = pd.DataFrame({
                "Ngày thi": ["10/11/2026", "10/11/2026", "13/11/2026"],
                "Ca thi": ["Ca 1 (07:30 - 09:30)", "Ca 2 (09:45 - 11:45)", "Ca 1 (07:30 - 09:30)"],
                "Học phần": ["Cơ sở lập trình (IT101)", "Cấu trúc dữ liệu (IT205)", "Mạng máy tính (IT208)"],
                "Phòng thi": ["PM.01 (Tầng 2 - Nhà A)", "PM.02 (Tầng 2 - Nhà A)", "PM.01 (Tầng 2 - Nhà A)"],
                "Vai trò": ["Giám thị chính (GT1)", "Giám thị 2", "Giám thị chính (GT1)"],
                "Trạng thái ca": ["Đã xác nhận", "Đã xác nhận", "Chờ xác nhận"]
            })
            st.dataframe(g_schedule, use_container_width=True, hide_index=True)
            st.button("✅ Xác nhận tham gia ca coi thi")

        elif selected_page == "👥 Danh sách sinh viên phòng thi":
            st.title("👥 Danh sách sinh viên trong ca coi thi")
            st.selectbox("Chọn ca thi cần điểm danh", ["10/11/2026 - Ca 1: IT101 tại PM.01"])
            sv_list = pd.DataFrame({
                "STT": [1, 2, 3, 4],
                "MSSV": ["20210001", "20210002", "20210003", "20210004"],
                "Họ và tên": ["Nguyễn Văn An", "Trần Thị Bình", "Lê Hoàng Cường", "Phạm Minh Đức"],
                "Vị trí máy": ["Máy 01", "Máy 02", "Máy 03", "Máy 04"],
                "Điểm danh": ["Có mặt", "Có mặt", "Vắng", "Có mặt"]
            })
            st.dataframe(sv_list, use_container_width=True, hide_index=True)
            st.button("🖨️ Xuất danh sách ký tên nộp bài")

        elif selected_page == "⚠️ Báo cáo sự cố phòng thi/máy":
            st.title("⚠️ Báo cáo sự cố thiết bị tại phòng thi")
            st.caption("Gửi cảnh báo tức thời tới IT Helpdesk")
            with st.form("incident_form"):
                st.selectbox("Phòng xảy ra sự cố", ["PM.01", "PM.02", "PM.03 (GPU)"])
                st.selectbox("Loại sự cố", ["Hỏng chuột/bàn phím/máy tính", "Mất kết nối mạng nộp bài", "Lỗi phần mềm/thiếu compiler"])
                st.text_input("Vị trí máy bị lỗi", placeholder="VD: Máy số 12")
                st.text_area("Mô tả ngắn gọn")
                if st.form_submit_button("🚨 Gửi thông báo khẩn cấp"):
                    st.success("Đã gửi sự cố tới bộ phận kỹ thuật IT trực phòng máy!")

    # 3. SINH VIÊN
    elif user_role == "Sinh viên":
        if selected_page == "🔍 Tra cứu lịch thi cá nhân":
            st.title("🔍 Tra cứu lịch thi của bạn")
            st.caption(f"Sinh viên: **{user['name']}** - {user['dept']}")
            
            my_exam = pd.DataFrame({
                "Ngày thi": ["10/11/2026", "13/11/2026", "16/11/2026"],
                "Ca thi": ["Ca 1 (07:30 - 09:30)", "Ca 2 (09:45 - 11:45)", "Ca 1 (07:30 - 09:30)"],
                "Môn thi": ["Cơ sở lập trình (IT101)", "Cấu trúc dữ liệu (IT205)", "Toán rời rạc (MATH101)"],
                "Hình thức thi": ["Thực hành phòng máy", "Thực hành phòng máy", "Thi viết trên giấy"],
                "Địa điểm": ["PM.01 (Nhà A)", "PM.02 (Nhà A)", "LT.101 (Nhà B)"],
                "Chỗ ngồi / Số máy": ["Máy số 01", "Máy số 12", "Bàn số 03"],
                "Lưu ý": ["Mang thẻ SV", "Mang thẻ SV", "Được mang 1 tờ tài liệu A4"]
            })
            st.dataframe(my_exam, use_container_width=True, hide_index=True)
            st.download_button("📥 Tải lịch thi cá nhân (PDF)", data="Mock data", file_name="lich_thi_ca_nhan.pdf")

        elif selected_page == "🖥️ Tra cứu yêu cầu phòng máy":
            st.title("🖥️ Yêu cầu môi trường & Phần mềm phòng máy")
            tools_df = pd.DataFrame({
                "Môn thi": ["Cơ sở lập trình", "Cấu trúc dữ liệu"],
                "Hệ điều hành": ["Windows 11 64-bit", "Windows 10 64-bit"],
                "Phần mềm / IDE": ["Visual Studio Code, PyCharm", "Code::Blocks, Dev C++"],
                "Phiên bản": ["Python 3.11", "GCC 11.2, Java 17"],
                "Mạng Internet": ["Chỉ truy cập web thi nội bộ", "Chỉ truy cập web thi nội bộ"]
            })
            st.dataframe(tools_df, use_container_width=True, hide_index=True)

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
                st.number_input("Trọng số phạt khi chênh lệch số ca giám thị", value=50)
                st.checkbox("Bật Solver Log chi tiết", value=True)
            st.button("💾 Cập nhật tham số bộ giải", type="primary")

        elif selected_page == "👥 Quản lý tài khoản & Phân quyền":
            st.title("👥 Quản lý người dùng & Phân quyền")
            users_df = pd.DataFrame({
                "Tài khoản": ["giaovu", "giamthi", "sinhvien", "admin"],
                "Họ tên": ["Nguyễn Thị Mai", "TS. Nguyễn Văn A", "Nguyễn Văn An", "Đỗ Quang Minh"],
                "Vai trò gán": ["Giáo vụ", "Giám thị", "Sinh viên", "Quản trị viên IT"],
                "Trạng thái": ["Hoạt động", "Hoạt động", "Hoạt động", "Hoạt động"]
            })
            st.dataframe(users_df, use_container_width=True, hide_index=True)
            st.button("➕ Thêm tài khoản mới")

        elif selected_page == "🛠️ Giám sát & Hỗ trợ kỹ thuật":
            st.title("🛠️ Giám sát hệ thống & Hàng đợi sự cố")
            c1, c2, c3 = st.columns(3)
            c1.metric("Bộ nhớ RAM máy chủ", "3.4 GB / 16 GB", "Tốt")
            c2.metric("Sự cố phòng máy đang chờ", "1 sự cố", "Cần kiểm tra")
            c3.metric("Trạng thái Solver Engine", "Sẵn sàng", "v1.6")
            
            st.subheader("Phiếu sự cố báo về từ Giám thị các phòng thi")
            tickets_df = pd.DataFrame({
                "Mã vé": ["#TK101", "#TK102"],
                "Phòng": ["PM.01", "PM.02"],
                "Nội dung": ["Máy số 12 bị kẹt bàn phím", "Cần thêm thư viện Python cho ca chiều"],
                "Giám thị báo": ["TS. Nguyễn Văn A", "ThS. Trần Thị B"],
                "Xử lý": ["Đang hỗ trợ", "Đã xử lý"]
            })
            st.dataframe(tickets_df, use_container_width=True, hide_index=True)
