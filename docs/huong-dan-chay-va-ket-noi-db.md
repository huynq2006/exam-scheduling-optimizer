# Hướng dẫn chạy và kết nối database

**Đối tượng:** mọi người trong team, mỗi người một máy
**Cập nhật:** 2026-11-18
**Trạng thái:** mô tả cấu hình đang chạy thật trên máy dev, không phải đề xuất

---

## 0. Đọc mục này trước — vì sao hay lỗi khi làm nhiều máy

Hệ thống có **hai đường kết nối DB khác nhau**, và gần như mọi lỗi "máy tôi không chạy được" đều do nhầm giữa hai đường này:

| Ai kết nối | Dùng địa chỉ nào | Cổng |
|---|---|---|
| **Next.js** (chạy trên máy thật, ngoài Docker) | `127.0.0.1` | **23306** / **23307** |
| **Script Python** (chạy trong container Docker) | `mysql-master` / `mysql-slave` | **3306** |

Next.js **không** chạy trong Docker. Nó ở trên máy bạn, nên phải đi qua cổng đã map ra host. Dùng `mysql-master:3306` trong `DB_MASTER_URL` sẽ lỗi `getaddrinfo ENOTFOUND` vì máy bạn không phân giải được tên đó.

Đây là lý do `.env` có **hai nhóm biến** cho cùng một database:

- `DB_MASTER_HOST` / `DB_SLAVE_HOST` / `DB_PORT`: cho Python trong Docker.
- `DB_MASTER_URL` / `DB_SLAVE_URL`: cho Next.js trên máy thật.

---

## 1. Yêu cầu môi trường

| Thành phần | Phiên bản | Kiểm tra |
|---|---|---|
| Docker Desktop | đang chạy | `docker --version` |
| Node.js | 20 trở lên | `node --version` |
| Python | 3.11+ **có ortools** | xem mục 6 |

**Cảnh báo về Python trên Windows:** nếu `python --version` trỏ tới `C:\msys64\...` (MSYS2/MinGW) thì **không cài được ortools**. Bản đó báo tag `mingw_x86_64_ucrt`, PyPI không có wheel nào khớp, và `pip install ortools` trả `from versions: none` — trông như mất mạng nhưng thật ra là sai nền tảng. Phải dùng bản CPython chính thức của Windows.

---

## 2. Tạo file `.env`

File `.env` nằm ở **gốc repo**, không phải trong `src/ui`.

```powershell
# Windows
Copy-Item .env.example .env
```

```bash
# macOS / Linux
cp .env.example .env
```

Sau đó sửa mật khẩu. Nội dung mẫu đầy đủ:

```ini
# ---------- Tài khoản root của MySQL ----------
MYSQL_ROOT_PASSWORD=doi_mat_khau_root_tai_day
MYSQL_ROOT_HOST=%

# ---------- Database ----------
MYSQL_DATABASE=quan_ly_thi

# ---------- Tài khoản ứng dụng ----------
MYSQL_USER=app_user
MYSQL_PASSWORD=doi_mat_khau_app_tai_day

# ---------- Tài khoản đồng bộ master-slave ----------
REPL_USER=repl_user
REPL_PASSWORD=doi_mat_khau_repl_tai_day

# ---------- Địa chỉ DB nhìn từ TRONG Docker (cho Python) ----------
DB_MASTER_HOST=mysql-master
DB_SLAVE_HOST=mysql-slave
DB_PORT=3306

# ---------- Chuỗi kết nối cho Next.js (chạy trên MÁY THẬT) ----------
DB_MASTER_URL=mysql+pymysql://app_user:doi_mat_khau_app_tai_day@127.0.0.1:23306/quan_ly_thi
DB_SLAVE_URL=mysql+pymysql://app_user:doi_mat_khau_app_tai_day@127.0.0.1:23307/quan_ly_thi
```

### Ba điều dễ sai trong file này

**a) Cổng.** Master map ra **23306**, slave map ra **23307**. Không phải 3306. Nhìn `docker-compose.yml`:

```yaml
mysql-master:  ports: "23306:3306"
mysql-slave:   ports: "23307:3306"
```

**b) Mật khẩu có ký tự đặc biệt.** Bộ đọc trong `src/ui/lib/db.ts` tách theo dấu `@` **cuối cùng**, nên mật khẩu chứa `@` vẫn đúng. Ví dụ `App_Pass@123` viết thẳng vào URL là được, không cần mã hoá.

**c) Không có dấu cách quanh `=`.** Bộ đọc `.env` cắt theo `=` đầu tiên rồi `trim()`, nhưng giá trị chứa dấu cách ở giữa sẽ bị giữ nguyên và gây lỗi xác thực.

---

## 3. Khởi động database

```powershell
cd mysql-replication
docker compose up -d
docker compose ps
```

Kỳ vọng:

```
mysql-master   Up   0.0.0.0:23306->3306/tcp
mysql-slave    Up   0.0.0.0:23307->3306/tcp
```

Lần đầu chạy, MySQL nạp toàn bộ file trong `database/` theo thứ tự tên file:

| File | Nội dung |
|---|---|
| `01.schema.sql` | Tạo database + 10 bảng gốc |
| `02.views.sql` | View kiểm tra vi phạm, view lịch công bố, trigger khoá phương án |
| `03.trang_thai_thi.sql` | Bảng trạng thái dự thi + nhật ký import + view trạng thái theo ca |
| `05.replication.sql`, `06.replication_setup.sql` | Cấu hình đồng bộ |

**Quan trọng:** các file này chỉ chạy khi volume còn trống. Nếu đã có dữ liệu, thêm file `.sql` mới vào `database/` **sẽ không tự chạy**. Phải nạp tay (mục 7).

---

## 4. Kiểm tra kết nối — làm đúng thứ tự này

Đừng chạy app trước rồi đoán lỗi. Kiểm tra từng tầng.

### 4.1. Container có sống không

```powershell
docker compose ps
```

### 4.2. Đăng nhập được bằng tài khoản app chưa

```powershell
$pw = (Select-String -Path ..\.env -Pattern '^MYSQL_PASSWORD=(.*)$').Matches.Groups[1].Value
docker exec mysql-master mysql -uapp_user -p"$pw" -e "SELECT COUNT(*) FROM quan_ly_thi.sinh_vien;"
```

### 4.3. Master và slave có **cùng số bảng** chưa

Đây là bước hay bị bỏ qua nhất, và cũng là lỗi đã gặp thật.

```powershell
$pw = (Select-String -Path ..\.env -Pattern '^MYSQL_PASSWORD=(.*)$').Matches.Groups[1].Value
$m = docker exec mysql-master mysql -uapp_user -p"$pw" -N -e "SELECT table_name FROM information_schema.tables WHERE table_schema='quan_ly_thi' ORDER BY table_name;" 2>$null
$s = docker exec mysql-slave  mysql -uapp_user -p"$pw" -N -e "SELECT table_name FROM information_schema.tables WHERE table_schema='quan_ly_thi' ORDER BY table_name;" 2>$null
"master: $($m.Count) | slave: $($s.Count)"
Compare-Object $m $s
```

Kỳ vọng: **cả hai 15 bảng**, `Compare-Object` không in gì.

Nếu slave ít hơn, nhảy sang mục 5.

### 4.4. Replication có đang chạy không

```powershell
"SHOW REPLICA STATUS" | docker exec -i mysql-slave bash -c 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" --vertical' 2>&1 | Select-String -Pattern "Replica_IO_Running|Replica_SQL_Running|Last_Errno|Last_SQL_Error"
```

Kỳ vọng:

```
Replica_IO_Running: Yes
Replica_SQL_Running: Yes
Last_Errno: 0
```

Nếu `Replica_SQL_Running: No`, nhảy sang mục 5.

### 4.5. Next.js đọc được DB chưa

```powershell
cd src/ui
npm run dev
```

Mở `http://localhost:3000/login`, đăng nhập `giaovu` / `giaovu`. Vào trang **Dữ liệu xếp lịch** — nếu thấy danh sách học phần là DB thông.

Hoặc gọi thẳng:

```powershell
Invoke-WebRequest -Uri "http://localhost:3000/api/dataset" -UseBasicParsing | Select-Object -ExpandProperty Content | Select-Object -First 1
```

---

## 5. Sự cố đã gặp thật: replication dừng, slave thiếu bảng

### Triệu chứng

- Slave có **12 bảng**, master có **15**.
- Thiếu đúng ba thứ của tính năng import CSV: `trang_thai_thi`, `dot_import_cam_thi`, `v_trang_thai_theo_ca`.
- Giao diện chạy được phần xếp lịch nhưng trang **Danh sách cấm thi** lỗi, vì bảng trạng thái không tồn tại trên slave.

### Nguyên nhân

Replication dừng giữa đường với lỗi `1062` (duplicate entry):

```
Could not execute Write_rows event on table quan_ly_thi.phan_mem;
Duplicate entry '1' for key 'phan_mem.PRIMARY', Error_code: 1062
```

Nghĩa là: slave đã có sẵn dòng đó (do volume cũ còn dữ liệu), master lại gửi lệnh chèn cùng khoá chính. SQL thread dừng, và **mọi thay đổi sau đó không bao giờ được áp dụng** — kể cả `CREATE TABLE` của ba bảng mới.

Đây là cái bẫy của việc dùng `docker-compose` có volume: `01.schema.sql` có `DROP DATABASE` nên master được tạo lại sạch, nhưng slave giữ volume cũ, và hai bên lệch nhau ngay từ đầu.

### Cách sửa (đã áp dụng, an toàn với dữ liệu)

Bỏ qua **đúng một** event lỗi rồi cho chạy tiếp. Không xoá dữ liệu, không tạo lại volume.

```powershell
"STOP REPLICA; SET GLOBAL SQL_SLAVE_SKIP_COUNTER = 1; START REPLICA;" | docker exec -i mysql-slave bash -c 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD"'
```

Đợi vài giây rồi kiểm tra lại bằng 4.3 và 4.4. Kết quả trên máy dev sau khi sửa:

```
master: 15 bang | slave: 15 bang
=== KHOP HOAN TOAN ===
trang_thai_thi : master=2 slave=2
dot_import_cam_thi : master=2 slave=2
```

### Nếu cách trên không đủ

Khi lệch quá nhiều, dựng lại slave từ đầu. **Chỉ làm khi chấp nhận mất dữ liệu trên slave** (slave là bản sao, master mới là nguồn thật):

```powershell
cd mysql-replication
docker compose down
docker volume rm mysql-replication_slave-data
docker compose up -d
```

Tên volume có thể khác tuỳ thư mục. Xem bằng `docker volume ls`.

---

## 6. Cấu hình Python cho bộ giải

Bộ giải CP-SAT cần `ortools`. Server tự dò trình nào import được, theo thứ tự:

1. Biến môi trường `EXAM_SCHEDULER_PYTHON`
2. Các bản CPython trong `%LOCALAPPDATA%\Programs\Python\Python3*`
3. `py -3`
4. venv của `src/ui_streamlit`
5. `python3`, `python`

### Kiểm tra máy mình

```powershell
python -c "from ortools.sat.python import cp_model; print('OK')"
```

Nếu báo `ModuleNotFoundError`, cài vào bản CPython chính thức:

```powershell
# Tìm bản CPython thật
py -0p

# Cài ortools vào đó
& "$env:LOCALAPPDATA\Programs\Python\Python314\python.exe" -m pip install ortools
```

Nếu máy có nhiều bản và muốn chỉ định rõ, thêm vào `.env`:

```ini
EXAM_SCHEDULER_PYTHON=C:\Users\ten\AppData\Local\Programs\Python\Python314\python.exe
```

### Về `src/ui_streamlit/.venv`

Thư mục này trên máy dev là **venv hỏng**: tạo bằng Python MinGW nên không cài được ortools, và gần như trống. Nó chỉ còn là đường dự phòng cuối trong danh sách dò. Nếu muốn dọn, xoá đi và dựa vào Python 3.14; nếu muốn dùng, tạo lại bằng bản CPython chính thức.

---

## 7. Nạp file SQL mới vào DB đã có dữ liệu

Khi thêm file `.sql` vào `database/` mà volume đã tồn tại, MySQL **không** tự chạy. Nạp tay vào master:

```powershell
Get-Content ..\database\03.trang_thai_thi.sql | docker exec -i mysql-master bash -c 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD"'
```

Sau khi nạp vào master, slave sẽ nhận qua replication **nếu** replication đang chạy (kiểm tra 4.4). Nếu không, chạy lại mục 5.

---

## 8. Chạy ứng dụng

```powershell
cd src/ui
npm install          # lần đầu
npm run dev          # http://localhost:3000
```

Tài khoản:

| Vai trò | Đăng nhập | Mật khẩu |
|---|---|---|
| Giáo vụ | `giaovu` | `giaovu` |
| Sinh viên | mã số sinh viên, ví dụ `SV20210003` | chính mã đó |

Lệnh khác:

```powershell
npm run typecheck    # tsc --noEmit
npm run build        # build production
```

---

## 9. Sinh lại dữ liệu mẫu

Script nằm ở `scripts/`, cần `faker` và `unidecode`:

```powershell
python -m pip install faker unidecode
python scripts/run_generate.py 200 16 8 5 20261111
```

Tham số: `số sinh viên`, `số học phần`, `số phòng`, `số ngày thi`, `seed`.

Script ghi vào **master** qua `src/backend/db_helper.py`, dùng `DB_MASTER_HOST` (tên trong Docker). Nếu chạy ngoài Docker thì phải đổi biến đó sang `127.0.0.1` và cổng `23306`.

---

## 10. Bảng tra lỗi nhanh

| Thông báo | Nguyên nhân | Sửa |
|---|---|---|
| `getaddrinfo ENOTFOUND mysql-master` | Next.js dùng tên Docker | `DB_*_URL` phải là `127.0.0.1:23306/23307` |
| `ECONNREFUSED 127.0.0.1:3306` | Dùng cổng 3306 | Đổi sang 23306 / 23307 |
| `Access denied for user 'app_user'` | Mật khẩu trong `.env` khác mật khẩu trong volume | Volume giữ mật khẩu lúc tạo. Đổi trong `.env` không đổi được DB cũ. Dựng lại volume hoặc `ALTER USER` |
| `Thiếu biến môi trường DB_MASTER_URL` | Không có `.env` ở gốc repo | Tạo theo mục 2 |
| `Table 'quan_ly_thi.trang_thai_thi' doesn't exist` | Replication dừng, slave thiếu bảng | Mục 5 |
| `from versions: none` khi `pip install ortools` | Python là MSYS2/MinGW | Mục 6, dùng CPython chính thức |
| `Không chạy được bộ giải CP-SAT` | Không Python nào có ortools | Mục 6 |
| `Too many connections` | Pool rò rỉ | Đã xử lý bằng `globalThis`; nếu vẫn gặp, khởi động lại dev server |

---

## 11. Checklist cho người mới clone repo

```
[ ] 1. docker --version, node --version chạy được
[ ] 2. Copy .env.example -> .env, sửa mật khẩu
[ ] 3. cd mysql-replication && docker compose up -d
[ ] 4. docker compose ps: cả hai container Up
[ ] 5. Kiểm tra master 15 bảng, slave 15 bảng (mục 4.3)
[ ] 6. Replica_SQL_Running: Yes (mục 4.4)
[ ] 7. python -c "import ortools" OK (mục 6)
[ ] 8. cd src/ui && npm install && npm run dev
[ ] 9. Đăng nhập giaovu/giaovu, mở trang Dữ liệu xếp lịch thấy dữ liệu
[ ] 10. Bấm Xếp lịch thi, thấy kết quả trong vài chục giây
```

Bước 5 và 6 là hai bước hay bị bỏ qua nhất, và cũng là nguồn của phần lớn lỗi khó hiểu.
