import { query } from "./db";
import type { Enrollment, Room, Slot, Student, StudentExam, Subject } from "./types";

/**
 * Đọc dữ liệu đầu vào cho bộ giải từ MySQL (replica) và map sang kiểu của UI.
 *
 * Nguồn: sinh_vien, mon_thi (+ mon_thi_phan_mem), phong_may (+ phong_may_phan_mem),
 * khung_gio, và dang_ky_thi (đăng ký thật của sinh viên).
 */

interface SubjectRow {
  ma_mon: string;
  ten_mon: string;
  so_tin_chi: number;
  thoi_luong_phut: number;
  hinh_thuc: Subject["hinhThuc"];
  phan_mem: string | null;
}

interface RoomRow {
  ma_phong: string;
  ten_phong: string;
  toa_nha: string;
  tang: number;
  suc_chua: number;
  he_dieu_hanh: string;
  tinh_trang: Room["tinhTrang"];
  phan_mem: string | null;
}

interface SlotRow {
  ma_khung: number;
  ngay_thi: string;
  ca_thi: number;
  gio_bat_dau: string;
  gio_ket_thuc: string;
}

interface StudentRow {
  ma_sv: string;
  ho_ten: string;
  ngay_sinh: string;
  gioi_tinh: Student["gioiTinh"];
  email: string;
  lop: string;
  khoa: string;
}

interface EnrollmentRow {
  ma_sv: string;
  ma_mon: string;
}

/** "07:00:00" -> "07:00" */
function hhmm(value: string): string {
  return value.slice(0, 5);
}

function splitList(value: string | null): string[] {
  if (!value) return [];
  return value
    .split("||")
    .map((s) => s.trim())
    .filter(Boolean);
}

export async function fetchSubjects(): Promise<Subject[]> {
  const rows = await query<SubjectRow>(`
    SELECT m.ma_mon, m.ten_mon, m.so_tin_chi, m.thoi_luong_phut, m.hinh_thuc,
           GROUP_CONCAT(DISTINCT pm.ten_pm ORDER BY pm.ten_pm SEPARATOR '||') AS phan_mem
      FROM mon_thi m
      LEFT JOIN mon_thi_phan_mem r ON r.ma_mon = m.ma_mon
      LEFT JOIN phan_mem pm        ON pm.ma_pm = r.ma_pm
     GROUP BY m.ma_mon, m.ten_mon, m.so_tin_chi, m.thoi_luong_phut, m.hinh_thuc
     ORDER BY m.ma_mon
  `);

  return rows.map((r) => ({
    maMon: r.ma_mon,
    tenMon: r.ten_mon,
    soTinChi: Number(r.so_tin_chi),
    thoiLuongPhut: Number(r.thoi_luong_phut),
    hinhThuc: r.hinh_thuc,
    phanMem: splitList(r.phan_mem),
  }));
}

export async function fetchRooms(): Promise<Room[]> {
  const rows = await query<RoomRow>(`
    SELECT p.ma_phong, p.ten_phong, p.toa_nha, p.tang, p.suc_chua,
           p.he_dieu_hanh, p.tinh_trang,
           GROUP_CONCAT(DISTINCT pm.ten_pm ORDER BY pm.ten_pm SEPARATOR '||') AS phan_mem
      FROM phong_may p
      LEFT JOIN phong_may_phan_mem x ON x.ma_phong = p.ma_phong
      LEFT JOIN phan_mem pm          ON pm.ma_pm = x.ma_pm
     GROUP BY p.ma_phong, p.ten_phong, p.toa_nha, p.tang, p.suc_chua,
              p.he_dieu_hanh, p.tinh_trang
     ORDER BY p.ma_phong
  `);

  return rows.map((r) => ({
    maPhong: r.ma_phong,
    tenPhong: r.ten_phong,
    toaNha: r.toa_nha,
    tang: Number(r.tang),
    sucChua: Number(r.suc_chua),
    heDieuHanh: r.he_dieu_hanh,
    tinhTrang: r.tinh_trang,
    phanMem: splitList(r.phan_mem),
  }));
}

export async function fetchSlots(): Promise<Slot[]> {
  const rows = await query<SlotRow>(`
    SELECT ma_khung, ngay_thi, ca_thi, gio_bat_dau, gio_ket_thuc
      FROM khung_gio
     ORDER BY ngay_thi, ca_thi
  `);

  return rows.map((r) => ({
    maKhung: Number(r.ma_khung),
    ngayThi: String(r.ngay_thi).slice(0, 10),
    caThi: Number(r.ca_thi),
    gioBd: hhmm(String(r.gio_bat_dau)),
    gioKt: hhmm(String(r.gio_ket_thuc)),
  }));
}

export async function fetchStudents(): Promise<Student[]> {
  const rows = await query<StudentRow>(`
    SELECT ma_sv, ho_ten, ngay_sinh, gioi_tinh, email, lop, khoa
      FROM sinh_vien
     ORDER BY ma_sv
  `);

  return rows.map((r) => ({
    maSv: r.ma_sv,
    hoTen: r.ho_ten,
    ngaySinh: String(r.ngay_sinh).slice(0, 10),
    gioiTinh: r.gioi_tinh,
    email: r.email,
    lop: r.lop,
    khoa: r.khoa,
  }));
}

/**
 * Đăng ký môn = các cặp (sinh viên, môn) thật trong dang_ky_thi.
 * Một môn có thể mở nhiều ca ở nhiều phòng, nên phải DISTINCT theo (ma_sv, ma_mon).
 */
export async function fetchEnrollment(): Promise<Enrollment[]> {
  const rows = await query<EnrollmentRow>(`
    SELECT DISTINCT d.ma_sv, l.ma_mon
      FROM dang_ky_thi d
      JOIN lich_thi l ON l.ma_lich = d.ma_lich
     ORDER BY d.ma_sv, l.ma_mon
  `);

  return rows.map((r) => ({ maSv: r.ma_sv, maMon: r.ma_mon }));
}

export interface Dataset {
  subjects: Subject[];
  rooms: Room[];
  slots: Slot[];
  students: Student[];
  enrollment: Enrollment[];
}

export async function fetchDataset(): Promise<Dataset> {
  const [subjects, rooms, slots, students, enrollment] = await Promise.all([
    fetchSubjects(),
    fetchRooms(),
    fetchSlots(),
    fetchStudents(),
    fetchEnrollment(),
  ]);

  return { subjects, rooms, slots, students, enrollment };
}

/* ==================================================================== */
/* Đăng nhập sinh viên bằng mã số sinh viên (MSSV)                       */
/* ==================================================================== */

export interface StudentAccount {
  maSv: string;
  hoTen: string;
  lop: string;
  khoa: string;
  khoaHoc: number;
  email: string;
  gioiTinh: string;
  ngaySinh: string;
}

interface StudentAccountRow {
  ma_sv: string;
  ho_ten: string;
  lop: string;
  khoa: string;
  khoa_hoc: number;
  email: string;
  gioi_tinh: string;
  ngay_sinh: string;
}

/**
 * Tra một sinh viên theo MSSV. Trả null nếu không có.
 *
 * Lưu ý bảo mật: đây là tra cứu công khai, nên chọn đúng các cột cần hiển thị.
 * `so_dien_thoai` cố ý không lấy.
 */
export async function findStudent(maSv: string): Promise<StudentAccount | null> {
  const rows = await query<StudentAccountRow>(
    `SELECT ma_sv, ho_ten, lop, khoa, khoa_hoc, email, gioi_tinh, ngay_sinh
       FROM sinh_vien
      WHERE ma_sv = ?
      LIMIT 1`,
    [maSv],
  );
  if (!rows.length) return null;

  const r = rows[0];
  return {
    maSv: r.ma_sv,
    hoTen: r.ho_ten,
    lop: r.lop,
    khoa: r.khoa,
    khoaHoc: Number(r.khoa_hoc),
    email: r.email,
    gioiTinh: r.gioi_tinh,
    ngaySinh: String(r.ngay_sinh).slice(0, 10),
  };
}

/* ==================================================================== */
/* Lịch thi cá nhân của sinh viên                                        */
/* ==================================================================== */

interface StudentExamRow {
  ma_lich: number;
  ma_mon: string;
  ten_mon: string;
  so_tin_chi: number;
  thoi_luong_phut: number;
  hinh_thuc: string;
  ngay_thi: string;
  ca_thi: number;
  gio_bat_dau: string;
  gio_ket_thuc: string;
  ma_phong: string;
  ten_phong: string;
  toa_nha: string;
  tang: number;
  suc_chua: number;
  he_dieu_hanh: string;
  phan_mem: string | null;
  so_may: number;
  diem: string | number | null;
}

/**
 * Các ca thi của một sinh viên, CHỈ trong phương án đã công bố.
 *
 * Đi qua `v_lich_thi_cong_bo` (view lọc `trang_thai = 'DA_CONG_BO'`) chứ không
 * đọc thẳng `lich_thi`, để sinh viên không thấy bản nháp đang xếp dở.
 */
export async function fetchStudentExams(maSv: string): Promise<StudentExam[]> {
  const rows = await query<StudentExamRow>(
    `SELECT v.ma_lich, v.ma_mon, m.ten_mon, m.so_tin_chi, m.thoi_luong_phut, m.hinh_thuc,
            k.ngay_thi, k.ca_thi, k.gio_bat_dau, k.gio_ket_thuc,
            p.ma_phong, p.ten_phong, p.toa_nha, p.tang, p.suc_chua, p.he_dieu_hanh,
            GROUP_CONCAT(DISTINCT pm.ten_pm ORDER BY pm.ten_pm SEPARATOR '||') AS phan_mem,
            d.so_may, d.diem
       FROM v_lich_thi_cong_bo v
       JOIN dang_ky_thi d ON d.ma_lich = v.ma_lich AND d.ma_sv = ?
       JOIN mon_thi m     ON m.ma_mon   = v.ma_mon
       JOIN khung_gio k   ON k.ma_khung = v.ma_khung
       JOIN phong_may p   ON p.ma_phong = v.ma_phong
       LEFT JOIN phong_may_phan_mem x ON x.ma_phong = p.ma_phong
       LEFT JOIN phan_mem pm          ON pm.ma_pm   = x.ma_pm
      GROUP BY v.ma_lich, v.ma_mon, m.ten_mon, m.so_tin_chi, m.thoi_luong_phut, m.hinh_thuc,
               k.ngay_thi, k.ca_thi, k.gio_bat_dau, k.gio_ket_thuc,
               p.ma_phong, p.ten_phong, p.toa_nha, p.tang, p.suc_chua, p.he_dieu_hanh,
               d.so_may, d.diem
      ORDER BY k.ngay_thi, k.ca_thi, p.ma_phong`,
    [maSv],
  );

  return rows.map((r) => ({
    maLich: Number(r.ma_lich),
    maMon: r.ma_mon,
    tenMon: r.ten_mon,
    soTinChi: Number(r.so_tin_chi),
    thoiLuongPhut: Number(r.thoi_luong_phut),
    hinhThuc: r.hinh_thuc,
    ngayThi: String(r.ngay_thi).slice(0, 10),
    caThi: Number(r.ca_thi),
    gioBd: hhmm(String(r.gio_bat_dau)),
    gioKt: hhmm(String(r.gio_ket_thuc)),
    maPhong: r.ma_phong,
    tenPhong: r.ten_phong,
    toaNha: r.toa_nha,
    tang: Number(r.tang),
    sucChua: Number(r.suc_chua),
    heDieuHanh: r.he_dieu_hanh,
    phanMemPhong: splitList(r.phan_mem),
    soMay: Number(r.so_may),
    diem: r.diem === null || r.diem === undefined ? null : Number(r.diem),
  }));
}
