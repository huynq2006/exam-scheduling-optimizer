/* Kiểu dữ liệu bám theo hợp đồng của src/algo/exam_scheduler.py */

export type Role = "giaovu" | "sinhvien";

export interface User {
  username: string;
  name: string;
  dept: string;
  email: string;
  role: Role;
  /* Chỉ có khi role = "sinhvien" */
  maSv?: string;
  lop?: string;
  khoa?: string;
  khoaHoc?: number;
}

/* ------------------------------------------------------------------ */
/* Lịch thi của một sinh viên (chỉ đọc từ phương án đã công bố)         */
/* ------------------------------------------------------------------ */

export interface StudentExam {
  maLich: number;
  maMon: string;
  tenMon: string;
  soTinChi: number;
  thoiLuongPhut: number;
  hinhThuc: string;
  ngayThi: string;
  caThi: number;
  gioBd: string;
  gioKt: string;
  maPhong: string;
  tenPhong: string;
  toaNha: string;
  tang: number;
  sucChua: number;
  heDieuHanh: string;
  phanMemPhong: string[];
  soMay: number;
  diem: number | null;
}

/* ------------------------------------------------------------------ */
/* Đầu vào của bộ giải (C, R, T, f, n)                                 */
/* ------------------------------------------------------------------ */

export interface Subject {
  maMon: string;
  tenMon: string;
  soTinChi: number;
  thoiLuongPhut: number;
  hinhThuc: "On-screen" | "Computer-based test" | "Practical";
  phanMem: string[];
}

export interface Room {
  maPhong: string;
  tenPhong: string;
  toaNha: string;
  tang: number;
  sucChua: number;
  heDieuHanh: string;
  tinhTrang: "Working" | "Maintenance";
  phanMem: string[];
}

export interface Slot {
  maKhung: number;
  ngayThi: string;
  caThi: number;
  gioBd: string;
  gioKt: string;
}

export interface Student {
  maSv: string;
  hoTen: string;
  ngaySinh: string;
  gioiTinh: "Nam" | "Nu";
  email: string;
  lop: string;
  khoa: string;
}

/** Một dòng đăng ký môn: quyết định n[c] và các nhóm sinh viên trong mô hình. */
export interface Enrollment {
  maSv: string;
  maMon: string;
}

/* ------------------------------------------------------------------ */
/* Tham số mục tiêu của mô hình                                        */
/* ------------------------------------------------------------------ */

export interface SolverParams {
  alpha: number; // phạt mở phòng
  beta: number; // phạt dồn nhiều ca trong một ngày
  gamma: number; // phạt tách môn sang nhiều phòng
  skipPenalty: number; // phạt bỏ môn không xếp được
  timeLimit: number; // giây
  seed: number;
  workers: number;
}

/* ------------------------------------------------------------------ */
/* Đầu ra của bộ giải                                                  */
/* ------------------------------------------------------------------ */

export interface SolveSession {
  maLich: number;
  maMon: string;
  maPhong: string;
  maKhung: number;
}

export interface SolveRegistration {
  maSv: string;
  maLich: number;
  soMay: number;
  diem: number | null;
}

export interface SolveStats {
  status: string;
  solveTime: number;
  objective: number;
  bestBound: number;
  roomsOpened: number;
  sessions: number;
  unscheduledSubjects: number;
  Z1: number;
  Z2: number;
}

export interface SolveResult {
  sessions: SolveSession[];
  registrations: SolveRegistration[];
  unscheduled: { maSv: string; maMon: string }[];
  stats: SolveStats;
  ranAt: string;
  params: SolverParams;
}
