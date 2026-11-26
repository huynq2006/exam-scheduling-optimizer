# Use Case — Nạp danh sách cấm thi từ CSV và các tính năng liên quan

**Vai trò viết:** BA · **Đối tượng đọc:** backend, frontend, QA
**Trạng thái:** mô tả hệ thống đang chạy trong mã nguồn, không phải đề xuất
**Cập nhật:** 2026-11-18

Tài liệu này mô tả đúng những gì code đang làm, kèm các điểm cần chốt ở mục 9.
Chỗ nào code chưa khớp với ý định thiết kế, tài liệu ghi rõ là chưa khớp.

---

## 1. Bối cảnh nghiệp vụ

Phòng Đào tạo mỗi kỳ nhận một danh sách sinh viên **không được dự thi**, từ hai nguồn:

| Nguồn | Bản chất | Xử lý khi sinh viên khắc phục |
|---|---|---|
| Chưa nộp học phí | Tạm thời | Nộp tiền xong là thi được |
| Cấm thi (kỷ luật, thi hộ, đánh trượt môn) | Vĩnh viễn trong kỳ | Phải có quyết định của Phòng Đào tạo |

**Nguyên tắc thiết kế cốt lõi — cấm thi là ĐÁNH DẤU, không phải XOÁ.**

Sinh viên bị cấm **vẫn nằm trong danh sách dự thi của ca**. Lý do nghiệp vụ: giám thị
cần đủ danh sách để đối chiếu giấy tờ và thẻ sinh viên tại phòng thi. Nếu xoá khỏi ca,
giám thị không biết người đó có đăng ký môn này hay không, và khi sinh viên nộp học phí
xong thì phải xếp lại ca từ đầu.

Hệ quả kỹ thuật: trạng thái là **dữ liệu nghiệp vụ tách hẳn khỏi lịch thi**, nằm ở bảng
riêng, không sửa `dang_ky_thi`.

---

## 2. Actor và quyền

| Actor | Đăng nhập bằng | Làm được |
|---|---|---|
| Giáo vụ | tài khoản nội bộ (`giaovu`) | Toàn bộ luồng nạp, xếp lịch, tra cứu, cấu hình |
| Sinh viên | MSSV (mật khẩu = MSSV) | Chỉ xem lịch thi và phòng máy của mình |
| Quản trị viên | — | Chưa có màn hình riêng; tham số bộ giải đang nằm trong tầm giáo vụ |

Điều hướng theo vai trò nằm ở `src/ui/components/app-shell.tsx`: mỗi vai trò có một
danh sách route riêng, mở route của vai trò khác sẽ bị đẩy về trang chủ của mình.

> **Lưu ý bảo mật:** đăng nhập sinh viên hiện chỉ xác nhận "mã này có trong danh sách",
> mật khẩu trùng MSSV. Đây không phải cơ chế xác thực thật. Đã ghi chú trong
> `app/api/student/login/route.ts`. Nếu triển khai thật phải thay bằng mật khẩu riêng
> + session cookie.

---

## 3. Use case tổng quát

```
UC-01  Nạp danh sách cấm thi từ CSV
UC-02  Xem trước và đối chiếu file trước khi ghi
UC-03  Ghi danh sách vào hệ thống
UC-04  Xem lịch sử các lần nạp
UC-05  Tra cứu sinh viên theo trạng thái
UC-06  Sửa / bỏ đánh dấu trạng thái trực tiếp
UC-07  Xem danh sách dự thi của một ca
UC-08  Xếp lịch thi
UC-09  Xem lịch thi đã xếp
UC-10  Cấu hình ưu tiên xếp lịch
UC-11  Sinh viên xem lịch thi cá nhân
UC-12  Sinh viên xem phòng máy của mình
```

Luồng chính: **UC-01 → UC-02 → UC-03 → UC-08 → UC-09**, các UC còn lại là nhánh phụ.

---

## 4. UC-01/02/03 — Nạp danh sách cấm thi

### 4.1. Tiền điều kiện

- Đã đăng nhập với vai trò giáo vụ.
- File CSV có ít nhất hai cột: `ma_sv` và `trang_thai`.
- Dữ liệu `sinh_vien` và `mon_thi` đã có trong DB (nếu không, mọi dòng sẽ báo
  "mã sinh viên không có trong hệ thống").

### 4.2. Luồng chính

1. Giáo vụ mở **Chuẩn bị → Danh sách cấm thi** (`/import`).
2. Chọn hoặc kéo-thả file CSV.
3. Hệ thống **tự động** gọi chế độ `preview` ngay khi nhận file — không cần bấm thêm.
4. Hệ thống hiện bảng xem trước: từng dòng, đối chiếu với DB, đánh dấu dòng lỗi.
5. Giáo vụ kiểm tra, bấm **Nạp N dòng**.
6. Hệ thống gọi chế độ `commit`, ghi các dòng hợp lệ, tạo một dòng nhật ký.
7. Hệ thống hiện kết quả: số dòng ghi được, số dòng bị bỏ, danh sách lỗi (tối đa 10
   dòng hiển thị, phần còn lại gộp thành "… và N dòng khác").

### 4.3. Vì sao tách preview và commit

Đây là quyết định thiết kế quan trọng, backend phải giữ nguyên:

> Người dùng phải thấy được "file này có 12 mã không tồn tại" **trước khi** bấm nút làm
> thay đổi dữ liệu thật.

`preview` **không ghi gì cả**. `commit` mới ghi. Hai chế độ dùng chung một hàm đọc file
(`previewImport`), nên kết quả xem trước và kết quả ghi không bao giờ lệch nhau.

### 4.4. Định dạng file được chấp nhận

Bộ đọc `src/ui/lib/csv.ts` xử lý các trường hợp file thật của Phòng Đào tạo:

| Tình huống | Cách xử lý |
|---|---|
| Excel ghi BOM (`\ufeff`) | Cắt BOM trước khi đọc tiêu đề |
| Máy đặt vùng Việt Nam dùng `;` | Tự đoán dấu phân cách từ dòng tiêu đề: `,` `;` hoặc tab |
| Ô có ngoặc kép, có dấu phẩy bên trong | Tách ô tôn trọng ngoặc kép; `""` = một dấu `"` thật |
| Tiêu đề tiếng Việt có dấu | Bỏ dấu, hạ chữ thường, ký tự lạ → `_` |
| Dòng trống giữa file | Bỏ qua nhưng **giữ số dòng gốc** để báo lỗi đúng dòng trong Excel |
| Xuống dòng kiểu Windows/Mac | Nhận `\r\n`, `\n`, `\r` |

### 4.5. Tên cột được chấp nhận

Tiêu đề được chuẩn hoá rồi so với danh sách bí danh. Backend **phải** giữ nguyên các
bí danh này vì file thật dùng đủ kiểu:

| Trường | Bí danh |
|---|---|
| `maSv` | `ma_sv`, `masv`, `mssv`, `ma_so_sinh_vien`, `ma_sinh_vien`, `student_id`, `ma` |
| `maMon` | `ma_mon`, `mamon`, `ma_hoc_phan`, `ma_hp`, `mahp`, `ma_mon_hoc`, `subject_id`, `mon` |
| `trangThai` | `trang_thai`, `trangthai`, `status`, `tinh_trang`, `loai` |
| `lyDo` | `ly_do`, `lydo`, `reason`, `ghi_chu`, `ghichu`, `note`, `noi_dung` |

**Bắt buộc:** `ma_sv`, `trang_thai`. **Không bắt buộc:** `ma_mon`, `ly_do`.

### 4.6. Giá trị trạng thái được chấp nhận

| Nhập vào (sau chuẩn hoá) | Lưu thành | Màu |
|---|---|---|
| `chua_nop_hoc_phi`, `chua_nop_hp`, `chuanophocphi`, `no_hoc_phi`, `hoc_phi`, `no_fee`, `unpaid`, `tam_hoan` | `CHUA_NOP_HOC_PHI` | Vàng |
| `cam_thi`, `camthi`, `banned`, `ky_luat`, `danh_truot`, `truot_mon`, `cam` | `CAM_THI` | Đỏ |

Giá trị khác → dòng lỗi `Không hiểu trạng thái "…"`.

### 4.7. Phạm vi áp dụng — quy tắc quan trọng nhất

| Cột `ma_mon` | Ý nghĩa | Khoá duy nhất |
|---|---|---|
| Để trống | Cấm **toàn bộ** học phần của sinh viên | `(ma_sv, '*')` |
| Có mã môn, ví dụ `INT101` | Chỉ cấm **đúng môn đó** | `(ma_sv, 'INT101')` |

Hai dòng này **độc lập, không đè nhau**. Một sinh viên có thể vừa bị cấm toàn bộ vừa có
ghi chú riêng cho một môn.

Cài đặt: cột sinh `ma_mon_key = IFNULL(ma_mon, '*')` kiểu `STORED`, gắn `UNIQUE
uq_tt_sv_mon (ma_sv, ma_mon_key)`. Cần cột sinh vì MySQL cho phép nhiều `NULL` trong
`UNIQUE`, nên nếu không quy `NULL` về `'*'` thì hai dòng "cấm toàn bộ" cho cùng một sinh
viên sẽ lọt qua.

### 4.8. Kiểm tra ở bước xem trước

Thứ tự kiểm tra (dừng ở lỗi đầu tiên của mỗi dòng):

1. **Thiếu mã sinh viên** — ô `ma_sv` rỗng.
2. **Thiếu cột trạng thái / không hiểu trạng thái**.
3. **Trùng mã trong cùng file** — khoá `maSv::maMon`, dòng sau bị bỏ và đếm vào `trungLap`.
4. **Mã sinh viên không có trong hệ thống** — tra bảng `sinh_vien`.
5. **Mã học phần không có trong danh mục môn thi** — tra bảng `mon_thi`.

Bước 5 tồn tại để bắt lỗi gõ sai mã môn **ngay ở xem trước**. Nếu bỏ qua, dòng sai sẽ nổ
ở `FOREIGN KEY` giữa lúc ghi và người dùng chỉ thấy một câu lỗi SQL khó hiểu.

Tra cứu theo lô: một truy vấn `IN (...)` cho toàn bộ mã sinh viên, một cho toàn bộ mã môn.
Không truy vấn từng dòng.

### 4.9. Ghi dữ liệu

- Chỉ ghi dòng `hopLe = true`.
- Mỗi dòng dùng `INSERT … ON DUPLICATE KEY UPDATE` trên `uq_tt_sv_mon`, nên nạp lại cùng
  file là cập nhật, không tạo bản trùng.
- `nguon` của mọi dòng nạp từ file là `IMPORT_CSV` (phân biệt với `THU_CONG` khi sửa tay).
- Tạo trước một dòng `dot_import_cam_thi` để lấy `ma_dot`, ghi xong cập nhật lại
  `so_thanh_cong` / `so_loi`.

### 4.10. Ngoại lệ và mã lỗi HTTP

| Tình huống | HTTP | Thông điệp |
|---|---|---|
| Body không phải `multipart/form-data` | 400 | Dữ liệu gửi lên phải là multipart/form-data có file CSV. |
| Thiếu file | 400 | Thiếu file CSV. |
| File rỗng (0 byte) | 400 | File rỗng. |
| File > 5 MB | 413 | File quá lớn (N KB). Giới hạn 5 MB. |
| Không đọc được nội dung file | 400 | Không đọc được nội dung file. |
| Lỗi DB khi đọc/ghi | 503 | Không xử lý được file CSV. |

Giới hạn 5 MB đặt ở `MAX_BYTES` trong `app/api/exam-status/import/route.ts`. Danh sách
thật chỉ vài trăm KB.

---

## 5. Hiển thị — đặc tả cho frontend

### 5.1. Trang `/import` gồm bốn khối, theo thứ tự

**Khối 1 — Ba ô số liệu tổng quan**

| Ô | Giá trị | Ghi chú |
|---|---|---|
| Sinh viên đang bị đánh dấu | `statuses.length` | Gồm cả cấm toàn bộ và cấm theo môn. Đổi màu cảnh báo khi > 0 |
| Cấm thi hẳn | đếm `trangThai === 'CAM_THI'` | Luôn tone nguy hiểm |
| Chưa nộp học phí | đếm `trangThai === 'CHUA_NOP_HOC_PHI'` | Tone cảnh báo |

**Khối 2 — Vùng nạp file**

- Khung viền đứt nét, đổi màu khi kéo file vào.
- Nút **Chọn file CSV**, nhận `.csv` và `text/csv`.
- Đang đọc file thì nút đổi chữ thành "Đang đọc file…" và bị khoá.
- Chọn xong hiện tên file.
- Nút **Tải file mẫu** ở góc phải tiêu đề trang, xuất CSV có BOM để Excel mở đúng tiếng Việt.

File mẫu:

```csv
ma_sv,ma_mon,trang_thai,ly_do
SV20210001,,CAM_THI,Kỷ luật thi hộ
SV20210002,,CHUA_NOP_HOC_PHI,Nợ học phí HK1
SV20210003,INT101,CAM_THI,Đánh trượt môn
```

**Khối 3 — Bảng xem trước** (chỉ hiện khi có kết quả preview)

Cột: `Dòng | Mã SV | Họ tên | Lớp | Học phần | Trạng thái | Ghi chú | Kết quả`

Quy tắc hiển thị:

- `Dòng` là số dòng **thật trong file Excel của người dùng**, không phải số thứ tự dòng dữ liệu.
- `Học phần` trống → hiện chữ "Toàn bộ" màu xám.
- `Kết quả`: dấu tích xanh nếu hợp lệ, dấu X đỏ nếu lỗi; rê chuột vào X hiện lý do.
- Dòng có trạng thái được tô nền theo màu trạng thái (xem 5.3).
- Thanh tổng hợp phía trên: `Tổng N dòng · X mã khớp sinh viên · Y mã không tồn tại · Z dòng trùng trong file`.
- Chân bảng: "N dòng hợp lệ sẽ được nạp. Dòng lỗi được bỏ qua." + nút **Huỷ** và **Nạp N dòng**.
- Nút nạp bị khoá khi không có dòng hợp lệ nào.

**Khối 4 — Lịch sử nạp**

Cột: `Đợt | File | Tổng dòng | Thành công | Lỗi | Người nạp | Thời điểm`

- Ban đầu hiện trạng thái rỗng "Chưa tải lịch sử" kèm nút **Xem lịch sử** (không tự tải,
  để trang nhẹ).
- Số lỗi khác 0 thì tô đỏ.
- Tối đa 20 đợt gần nhất.

**Khối 5 — Sinh viên đang bị đánh dấu**

Cột: `Mã SV | Học phần | Trạng thái | Ghi chú | Nguồn | Cập nhật`

- `Học phần` trống → "Toàn bộ".
- `Nguồn`: `IMPORT_CSV` → "Nạp CSV", `THU_CONG` → "Nhập tay".
- Hiện tối đa 100 dòng, vượt thì ghi chú "Đang hiện 100/N dòng. Xem đầy đủ ở trang Truy vấn."

### 5.2. Bốn trạng thái màn hình phải xử lý

| Trạng thái | Hiển thị |
|---|---|
| Chưa chọn file | Khung nạp trống, không có bảng xem trước |
| Đang đọc file | Nút khoá, chữ "Đang đọc file…" |
| Có xem trước | Bảng xem trước + nút nạp |
| Đã ghi xong | Khối kết quả xanh "Đã nạp xong đợt #N", bảng xem trước biến mất, ô chọn file được xoá |

Lỗi mạng/DB hiện trong khung đỏ ngay dưới vùng nạp, không phải popup.

### 5.3. Quy ước màu — dùng chung toàn hệ thống

Định nghĩa một chỗ duy nhất ở `src/ui/lib/labels.ts`, hàm `rowToneClass`:

| Trạng thái | Nền dòng | Nhãn |
|---|---|---|
| `CAM_THI` | `bg-rose-50/80` | Chấm đỏ + "Cấm thi" |
| `CHUA_NOP_HOC_PHI` | `bg-amber-50/70` | Chấm vàng + "Chưa nộp học phí" |
| Không có | Trắng | "—" màu xám nhạt |

Bảng nào có cột trạng thái cũng phải dùng đúng hàm này. Đây là lý do tồn tại của nó:
trước đây mỗi trang tự tô một kiểu, lệch cả màu lẫn sắc độ.

### 5.4. Trạng thái hiệu lực — quy tắc gộp

Khi một sinh viên có nhiều dòng trạng thái, hiển thị theo **một** dòng hiệu lực:

```
điểm = (CAM_THI ? 2 : 1) * 10 + (có ma_mon ? 1 : 0)
```

Thứ tự thắng: `CAM_THI + theo môn` (21) > `CAM_THI + toàn bộ` (20) >
`CHUA_NOP + theo môn` (11) > `CHUA_NOP + toàn bộ` (10).

Nghĩa là: **cấm thi hẳn luôn thắng chưa nộp học phí**; cùng mức thì phạm vi hẹp thắng
phạm vi rộng.

Hàm dùng chung: `effectiveStatus` ở `src/ui/lib/status-shared.ts`. **Phải** import từ file
này, không import từ `lib/status.ts`, vì file kia mở kết nối MySQL và không chạy được ở
trình duyệt.

Quy tắc này khớp với view `v_trang_thai_theo_ca` trong `database/03.trang_thai_thi.sql`.
Sửa một bên phải sửa bên kia.

---

## 6. UC-04 — Lịch sử nạp

**Mục đích nghiệp vụ:** trả lời được câu "danh sách cấm thi này do ai nạp, nạp lúc nào,
từ file nào" khi sinh viên khiếu nại.

Bảng `dot_import_cam_thi`: `ma_dot`, `ten_file`, `tong_dong`, `so_thanh_cong`, `so_loi`,
`nguoi_import`, `ghi_chu`, `tao_luc`.

`nguoi_import` lấy từ tên người đang đăng nhập, gửi kèm form. Hiện **không có ràng buộc
khoá ngoại** tới bảng người dùng — ai gọi API cũng đặt được tên bất kỳ.

---

## 7. UC-05/06 — Tra cứu và sửa trạng thái

### 7.1. Trang `/query`

Ba tab dùng **chung một endpoint** `/api/students`, khác nhau ở tham số `trangThai`:

| Tab | `trangThai` | Ý nghĩa |
|---|---|---|
| Tất cả sinh viên | (không gửi) | Toàn bộ |
| Chưa nộp học phí | `CHUA_NOP_HOC_PHI` | Có ít nhất một dòng trạng thái này |
| Bị cấm thi | `CAM_THI` | Có ít nhất một dòng trạng thái này |

Bộ lọc: từ khoá (mã SV, họ tên, lớp, mã/tên học phần), học phần, lớp.

Hành vi gõ từ khoá: chờ **300 ms** rồi mới gọi API, tránh bắn request mỗi phím. Đổi tab
thì gọi ngay.

Cột bảng: `Mã SV | Họ tên | Lớp | Khoa | Số môn | Trạng thái | Ghi chú | (nút Sửa)`

- Cột Ghi chú hiện lý do; nếu có cấm theo môn thì thêm dòng "Cấm môn: INT101, …".
- Bấm **Sửa** mở một dòng con ngay dưới, có ô chọn trạng thái. **Chọn xong là lưu ngay**,
  không có nút Lưu riêng.
- Nút **Xuất CSV** xuất đúng tập đang lọc, có BOM, tên file `truy-van-{tab}-{ngày}.csv`.

### 7.2. Sửa trạng thái

| Thao tác | Endpoint |
|---|---|
| Đặt / cập nhật | `POST /api/exam-status` |
| Bỏ đánh dấu | `DELETE /api/exam-status?maSv=…&maMon=…` |

Quy tắc dữ liệu vào:

- `maSv` và `maMon` được **trim + viết hoa** ở server. Client gửi chữ thường vẫn đúng.
- `trangThai` chỉ nhận `CHUA_NOP_HOC_PHI` hoặc `CAM_THI`, khác thì 400.
- `lyDo` cắt còn tối đa 255 ký tự.
- `maMon` rỗng → `null` (cấm toàn bộ).
- Khi sửa tay, `nguon` ghi là `THU_CONG`.

### 7.3. UC-07 — Danh sách dự thi của một ca

Mở từ trang `/solution`: bấm một dòng ca thi → drawer trượt từ phải.

`GET /api/session/{maLich}/roster` trả về danh sách sinh viên **kèm trạng thái hiệu lực
đã tính sẵn**, cùng hai con số tổng hợp `biCamThi`, `chuaNopHocPhi`.

Bộ lọc trong drawer: `Tất cả | Cấm thi | Chưa nộp học phí | Bình thường`, mỗi nút có số đếm.
Có ô tìm theo mã SV, họ tên, lớp trong phạm vi ca đó.

Sửa trạng thái ngay trong drawer: bấm **Đánh dấu** / **Sửa** ở cuối dòng, một thanh soạn
hiện ra ở chân drawer, có ô trạng thái và ô ghi chú tự do (tối đa 255 ký tự).

**Hiệu năng:** một truy vấn cho cả ca, không phải một truy vấn mỗi sinh viên. Trang
`/solution` cũng tính trạng thái từ danh sách đăng ký đã có trong bộ nhớ, không gọi API
cho từng ca.

---

## 8. UC-08 đến UC-12 — Các tính năng sau đó

### 8.1. UC-08 — Xếp lịch thi (`/solve`)

Gửi `POST /api/solve` với bảy tham số: `alpha`, `beta`, `gamma`, `skipPenalty`,
`timeLimit`, `seed`, `workers`.

Server đọc dữ liệu từ MySQL, gọi bộ giải CP-SAT qua `src/algo/solve_cli.py`, trả về
`sessions`, `registrations`, `unscheduled`, `stats`.

Giao diện: nút **Xếp lịch thi** là hành động chính. Bốn mức ưu tiên và mã lần chạy giấu
trong mục gập **Tuỳ chọn nâng cao (dành cho quản trị)** — người dùng thường không cần mở.

Kết quả hiện ngay dưới: một câu tóm tắt bằng lời, bốn ô số liệu, và mục gập **Thông số kỹ
thuật của lần chạy** (trạng thái bộ giải, hàm mục tiêu, cận dưới, Z1, Z2).

**Chọn Python:** server dò xem trình nào `import` được `ortools` thật rồi mới dùng, theo
thứ tự: biến môi trường `EXAM_SCHEDULER_PYTHON` → các bản CPython trong
`%LOCALAPPDATA%\Programs\Python` → `py -3` → venv của `src/ui_streamlit` → `python`.

Không đoán theo đường dẫn cứng, vì bản Python MSYS2/MinGW (`C:\msys64`) báo tag
`mingw_x86_64_ucrt` và **không có wheel ortools nào khớp** — `pip install ortools` ở đó
trả "from versions: none", trông như mất mạng nhưng thật ra là sai nền tảng.

### 8.2. UC-09 — Xem lịch thi đã xếp (`/solution`)

Bốn ô số liệu: số ca thi, số sinh viên đã có chỗ, **lượt thi bị cấm**, **lượt chưa nộp
học phí**. Hai ô sau là lý do trang này tồn tại: giáo vụ cần biết ngay có bao nhiêu lượt
dự thi bị ảnh hưởng, tính trên **toàn bộ lịch** chứ không chỉ dòng đang lọc.

Bộ lọc: theo ngày, theo học phần, và hộp **Chỉ ca có vấn đề**.

Bảng: `Ngày & ca thi | Học phần | Phòng thi | Sĩ số | Trạng thái dự thi`

- Sĩ số hiện `đã xếp / sức chứa · N trống`.
- Cột trạng thái hiện nhãn "N cấm thi" / "N chưa nộp HP", hoặc "Bình thường" nếu sạch.
- **Cả dòng** tô nền đỏ nếu có người bị cấm, vàng nếu có người chưa nộp.
- Bấm dòng → mở drawer danh sách (UC-07).

Ba khối phụ:

1. **Chú giải màu** — nói rõ đỏ là cấm thi, vàng là chưa nộp học phí.
2. **Mức sử dụng phòng theo từng ngày** — thanh tiến trình, quá 90% đổi màu cảnh báo.
3. **Học phần chưa xếp được** — bảng nêu nguyên nhân khả dĩ và cách xử lý, kèm 5 mã sinh
   viên bị ảnh hưởng đầu tiên. Không có học phần nào bị bỏ thì hiện một dòng xanh.

Gợi ý nguyên nhân (`unscheduledHint`) suy từ dữ liệu, chia ba trường hợp: không phòng nào
đủ phần mềm → thiếu chỗ so với sĩ số → đủ điều kiện nhưng bị ca khác chiếm. Đây là **suy
luận từ dữ liệu đầu vào, không phải kết luận của bộ giải** — ghi rõ trong mã nguồn.

### 8.3. UC-10 — Cấu hình ưu tiên (`/params`)

Ba preset chọn nhanh: **Tiết kiệm phòng máy**, **Giãn lịch cho sinh viên**, **Mỗi môn gọn
một phòng**. Mỗi preset nêu rõ mục tiêu và **cái giá phải trả** (ví dụ "Có thể phải tách
một học phần ra nhiều phòng").

Bốn mức ưu tiên, câu mô tả dùng ngôn ngữ nghiệp vụ chứ không dùng ký hiệu α β γ:

| Tham số | Nhãn hiển thị |
|---|---|
| `alpha` | Hạn chế mở thêm phòng |
| `beta` | Hạn chế dồn nhiều ca trong một ngày |
| `gamma` | Hạn chế tách môn sang nhiều phòng |
| `skipPenalty` | Mức phạt khi phải bỏ học phần |

Có nút **Lưu cấu hình**, **Hoàn tác**, và chỉ báo "Có thay đổi chưa lưu" / "Đã lưu".

### 8.4. UC-11/12 — Cổng sinh viên

`/my-exams` — lịch thi cá nhân. Nổi bật **ca thi gần nhất** với số ngày còn lại, tô cảnh
báo khi ≤ 3 ngày. Bảng đầy đủ có cột máy số.

`/my-rooms` — nhóm theo phòng, mỗi phòng một thẻ: vị trí, sức chứa, hệ điều hành, phần mềm
đã cài, và các ca thi của sinh viên ở phòng đó.

Cả hai chỉ đọc **phương án đã công bố** (`v_lich_thi_cong_bo`, lọc `trang_thai = 'DA_CONG_BO'`).

---

## 9. Điểm cần chốt — chỗ code chưa khớp ý định

Mục này để team quyết, không phải lỗi tài liệu.

### 9.1. `commitImport` không dừng khi một dòng lỗi — nhưng chú thích nói là có

Chú thích trong `src/ui/lib/status.ts` viết:

> Không ghi nửa vời: nếu một dòng làm lỗi thì cả lượt import dừng và báo, vì danh sách
> cấm thi mà nạp thiếu còn tệ hơn nạp lại.

Nhưng mã thực tế bọc từng dòng trong `try/catch`, gặp lỗi thì ghi vào `failures` rồi
**tiếp tục dòng sau**. Kết quả: một lượt nạp có thể ghi được 90/100 dòng và báo "90 thành
công, 10 lỗi".

**Cần chốt:** muốn nguyên tử (all-or-nothing, dùng transaction) hay chấp nhận ghi một
phần? Nếu chọn nguyên tử thì phải bọc `BEGIN/COMMIT` và sửa lại chú thích. Nếu chấp nhận
ghi một phần thì sửa chú thích cho khớp và ghi rõ trên giao diện là "đã ghi một phần".

### 9.2. `khop` và `hopLe` đang bằng nhau

Trong `previewImport`, cả hai trường đều gán `hopLe.length`. Theo tên gọi, `khop` phải là
"số dòng khớp được sinh viên trong DB", khác với "số dòng hợp lệ". Hiện giao diện hiện
"N mã khớp sinh viên trong hệ thống" nhưng con số này thật ra là số dòng hợp lệ.

### 9.3. Chưa có xác thực thật

Đăng nhập sinh viên: mật khẩu = MSSV. Đăng nhập giáo vụ: tài khoản nằm trong bundle
(`src/ui/lib/data.ts`), ai đọc mã nguồn cũng thấy. Mọi API nghiệp vụ **không kiểm tra
quyền** — gọi thẳng `POST /api/exam-status` từ ngoài vẫn ghi được dữ liệu.

Trước khi triển khai thật phải có: session cookie, kiểm tra vai trò ở từng route, và
chuyển tài khoản giáo vụ vào DB.

### 9.4. Chưa có cơ chế công bố lịch

Sơ đồ use case (`docs/use_case.puml`) có UC11 "Phê duyệt và công bố lịch", nhưng giao
diện hiện chưa có nút công bố. Bảng `phuong_an` có cột `trang_thai` với giá trị
`NHAP` / `DA_CONG_BO`, và trigger chặn sửa khi đã khoá — nhưng chưa có đường nào để
chuyển từ `NHAP` sang `DA_CONG_BO` từ giao diện.

Hệ quả: cổng sinh viên (`/my-exams`) đọc `v_lich_thi_cong_bo`, nên nếu dữ liệu chưa được
đánh dấu công bố thì sinh viên thấy trống dù lịch đã xếp xong.

### 9.5. Kết quả xếp lịch chỉ nằm trong bộ nhớ trình duyệt

`result` lưu ở `localStorage` phía client. Đóng trình duyệt hoặc đổi máy là mất. Kết quả
**không được ghi vào** `phuong_an` / `lich_thi` / `dang_ky_thi`.

Nghĩa là: xếp lịch xong, giáo vụ xem được, nhưng sinh viên **không** thấy gì, và lịch sử
các phương án không tồn tại. Đây là khoảng trống lớn nhất giữa giao diện và schema DB.

---

## 10. Phụ lục — Hợp đồng API

Tất cả route đặt `runtime = "nodejs"` và `dynamic = "force-dynamic"`.

| Method | Đường dẫn | Vào | Ra |
|---|---|---|---|
| GET | `/api/dataset` | — | `{subjects, rooms, slots, students, enrollment, source, fetchedAt}` |
| GET | `/api/exam-status` | — | `{statuses: StudentExamStatus[]}` |
| POST | `/api/exam-status` | `{maSv, maMon?, trangThai, lyDo?}` | `{ok, maSv, maMon, trangThai}` |
| DELETE | `/api/exam-status` | `?maSv=&maMon=` | `{ok, maSv, maMon}` |
| GET | `/api/exam-status/import` | — | `{history: [...]}` |
| POST | `/api/exam-status/import` | form: `file`, `mode`, `nguoiImport` | preview hoặc commit result |
| GET | `/api/session/{maLich}/roster` | — | `{maLich, roster, total, biCamThi, chuaNopHocPhi}` |
| GET | `/api/students` | `?q=&maMon=&lop=&trangThai=&limit=` | `{students, classes, total, fetchedAt}` |
| POST | `/api/solve` | `SolverParams` | `{sessions, registrations, unscheduled, stats, python}` |
| POST | `/api/student/login` | `{maSv, password}` | `{student}` |
| GET | `/api/student/{maSv}/schedule` | — | `{student, exams, published, fetchedAt}` |

Mã lỗi dùng chung: `400` dữ liệu vào sai, `401` sai mật khẩu, `404` không tồn tại,
`409` thiếu dữ liệu đầu vào để xếp lịch, `413` file quá lớn, `503` lỗi DB hoặc bộ giải.

Mọi phản hồi lỗi đều có dạng `{error: string, detail?: string}`. `error` là câu tiếng Việt
hiển thị được cho người dùng; `detail` là thông tin kỹ thuật, chỉ để gỡ lỗi.

### Đọc master hay slave

Bảng `trang_thai_thi` **luôn đọc từ MASTER**, không đọc replica. Lý do: trạng thái vừa ghi
ở master mà đọc ở slave thì giao diện hiện dữ liệu cũ ngay sau khi người dùng bấm lưu.
Áp dụng cho `fetchAllStatuses`, `fetchStudentStatuses`, `fetchRoster`, `searchStudents`,
`fetchImportLog`.

Dữ liệu đọc-only (học phần, phòng, khung giờ, sinh viên, đăng ký) đọc từ slave.
