import { execute, query } from "./db";
import { missingColumns, parseCsv, toDraftRows } from "./csv";
import { effectiveStatus } from "./status-shared";
import type {
  ExamStatus,
  ImportPreview,
  ImportPreviewRow,
  RosterEntry,
  StudentExamStatus,
} from "./types";

/* ==================================================================== */
/* Trạng thái dự thi                                                    */
/* ==================================================================== */

interface StatusRow {
  ma_sv: string;
  ma_mon: string | null;
  trang_thai: ExamStatus;
  ly_do: string | null;
  nguon: StudentExamStatus["nguon"];
  cap_nhat_luc: string;
}

function mapStatus(r: StatusRow): StudentExamStatus {
  return {
    maSv: r.ma_sv,
    maMon: r.ma_mon,
    trangThai: r.trang_thai,
    lyDo: r.ly_do,
    nguon: r.nguon,
    capNhatLuc: String(r.cap_nhat_luc),
  };
}

/**
 * Toàn bộ trạng thái đang có hiệu lực.
 *
 * Bảng này nhỏ (chỉ sinh viên có vấn đề), nên nạp hết một lần rồi tra trong
 * bộ nhớ còn hơn bắn một truy vấn cho mỗi ca thi.
 */
export async function fetchAllStatuses(): Promise<StudentExamStatus[]> {
  const rows = await query<StatusRow>(
    `
    SELECT ma_sv, ma_mon, trang_thai, ly_do, nguon, cap_nhat_luc
      FROM trang_thai_thi
     ORDER BY ma_sv, ma_mon IS NULL DESC, ma_mon
  `,
    [],
    // Đọc từ MASTER, không phải replica: trạng thái vừa ghi ở master mà đọc
    // ở slave thì giao diện sẽ hiện dữ liệu cũ ngay sau khi người dùng bấm lưu.
    "master",
  );
  return rows.map(mapStatus);
}

/** Trạng thái của một sinh viên, kèm cả dòng cấm toàn bộ lẫn dòng theo môn. */
export async function fetchStudentStatuses(maSv: string): Promise<StudentExamStatus[]> {
  const rows = await query<StatusRow>(
    `SELECT ma_sv, ma_mon, trang_thai, ly_do, nguon, cap_nhat_luc
       FROM trang_thai_thi
      WHERE ma_sv = ?
      ORDER BY ma_mon IS NULL DESC, ma_mon`,
    [maSv],
    "master",
  );
  return rows.map(mapStatus);
}

/**
 * Trạng thái hiệu lực cho một cặp (sinh viên, học phần).
 *
 * Quy tắc: CAM_THI thắng CHUA_NOP_HOC_PHI; cùng mức thì phạm vi hẹp (theo
 * môn) thắng phạm vi rộng. Khớp đúng với view v_trang_thai_theo_ca.
 *
 * Cài đặt nằm ở `status-shared.ts` để client component dùng lại được mà
 * không kéo theo mysql2 vào bundle trình duyệt.
 */
export { effectiveStatus } from "./status-shared";

/* ==================================================================== */
/* Danh sách dự thi của một ca                                          */
/* ==================================================================== */

interface RosterRow {
  ma_sv: string;
  ho_ten: string;
  lop: string;
  khoa: string;
  so_may: number;
  diem: string | number | null;
}

/**
 * Sinh viên ngồi trong một ca thi.
 *
 * `maLich` ở đây là mã ca trong phương án đang xếp (kết quả bộ giải), nên
 * nguồn là `dang_ky_thi` của phương án đã công bố. Sinh viên bị cấm thi vẫn
 * nằm trong danh sách — chỉ khác là có trạng thái để tô màu.
 */
export async function fetchRoster(maLich: number): Promise<RosterEntry[]> {
  const rows = await query<RosterRow>(
    `SELECT dk.ma_sv, sv.ho_ten, sv.lop, sv.khoa, dk.so_may, dk.diem
       FROM dang_ky_thi dk
       JOIN sinh_vien sv ON sv.ma_sv = dk.ma_sv
      WHERE dk.ma_lich = ?
      ORDER BY dk.so_may`,
    [maLich],
  );

  if (!rows.length) return [];

  // Mã học phần của ca thi này — cần để trạng thái theo môn khớp đúng.
  const session = await query<{ ma_mon: string }>(
    `SELECT ma_mon FROM lich_thi WHERE ma_lich = ? LIMIT 1`,
    [maLich],
  );
  const maMon = session[0]?.ma_mon ?? "";

  // Một truy vấn cho cả ca, không phải một truy vấn mỗi sinh viên.
  const statuses = await query<StatusRow>(
    `SELECT t.ma_sv, t.ma_mon, t.trang_thai, t.ly_do, t.nguon, t.cap_nhat_luc
       FROM trang_thai_thi t
       JOIN dang_ky_thi dk ON dk.ma_sv = t.ma_sv
      WHERE dk.ma_lich = ?
        AND (t.ma_mon IS NULL OR t.ma_mon = ?)`,
    [maLich, maMon],
    "master",
  );
  const mapped = statuses.map(mapStatus);

  return rows.map((r) => {
    const eff = effectiveStatus(mapped, r.ma_sv, maMon);
    return {
      maSv: r.ma_sv,
      hoTen: r.ho_ten,
      lop: r.lop,
      khoa: r.khoa,
      soMay: Number(r.so_may),
      diem: r.diem === null || r.diem === undefined ? null : Number(r.diem),
      trangThai: eff?.trangThai ?? null,
      lyDo: eff?.lyDo ?? null,
    };
  });
}

/* ==================================================================== */
/* Ghi trạng thái                                                       */
/* ==================================================================== */

export interface StatusInput {
  maSv: string;
  maMon: string | null;
  trangThai: ExamStatus;
  lyDo: string | null;
}

/**
 * Đặt trạng thái cho một sinh viên. Ghi đè nếu đã có dòng cùng phạm vi.
 *
 * Dùng ON DUPLICATE KEY UPDATE dựa trên uq_tt_sv_mon: (ma_sv, ma_mon_key),
 * nên "cấm toàn bộ" và "cấm môn X" là hai dòng độc lập, không đè nhau.
 */
export async function upsertStatus(
  input: StatusInput,
  nguon: StudentExamStatus["nguon"] = "THU_CONG",
): Promise<void> {
  await execute(
    `INSERT INTO trang_thai_thi (ma_sv, ma_mon, trang_thai, ly_do, nguon)
     VALUES (?, ?, ?, ?, ?)
     ON DUPLICATE KEY UPDATE
       trang_thai = VALUES(trang_thai),
       ly_do     = VALUES(ly_do),
       nguon     = VALUES(nguon)`,
    [input.maSv, input.maMon, input.trangThai, input.lyDo, nguon],
  );
}

/** Bỏ đánh dấu: sinh viên trở lại bình thường. */
export async function clearStatus(maSv: string, maMon: string | null): Promise<void> {
  await execute(
    `DELETE FROM trang_thai_thi
      WHERE ma_sv = ? AND ma_mon_key = ?`,
    [maSv, maMon ?? "*"],
  );
}

/* ==================================================================== */
/* Import CSV                                                           */
/* ==================================================================== */

/**
 * Đọc và đối chiếu file CSV với DB, KHÔNG ghi gì cả.
 *
 * Tách hẳn bước xem trước khỏi bước ghi: người dùng phải thấy được "file này
 * có 12 mã không tồn tại" trước khi bấm nút làm thay đổi dữ liệu thật.
 */
export async function previewImport(fileName: string, text: string): Promise<ImportPreview> {
  const parsed = parseCsv(text);

  const missing = missingColumns(parsed.headers);
  if (missing.length) {
    return {
      tenFile: fileName,
      tongDong: 0,
      hopLe: 0,
      khop: 0,
      khongTonTai: 0,
      trungLap: 0,
      errors: [
        {
          dong: 1,
          maSv: "",
          lyDo: `File thiếu cột bắt buộc: ${missing.join(", ")}. Cần có cột ma_sv và trang_thai.`,
        },
      ],
      rows: [],
    };
  }

  const drafts = toDraftRows(parsed);
  if (!drafts.length) {
    return {
      tenFile: fileName,
      tongDong: 0,
      hopLe: 0,
      khop: 0,
      khongTonTai: 0,
      trungLap: 0,
      errors: [{ dong: 1, maSv: "", lyDo: "File không có dòng dữ liệu nào." }],
      rows: [],
    };
  }

  // Tra một lượt toàn bộ mã sinh viên trong file.
  const codes = Array.from(new Set(drafts.map((d) => d.maSv).filter(Boolean)));
  const known = new Map<string, { hoTen: string; lop: string }>();
  if (codes.length) {
    const placeholders = codes.map(() => "?").join(",");
    const rows = await query<{ ma_sv: string; ho_ten: string; lop: string }>(
      `SELECT ma_sv, ho_ten, lop FROM sinh_vien WHERE ma_sv IN (${placeholders})`,
      codes,
    );
    for (const r of rows) known.set(r.ma_sv, { hoTen: r.ho_ten, lop: r.lop });
  }

  // Và toàn bộ mã học phần, để bắt lỗi gõ sai mã môn ngay ở bước xem trước.
  // Nếu bỏ qua bước này, dòng sai sẽ nổ ở FOREIGN KEY giữa lúc ghi và người
  // dùng chỉ thấy một câu lỗi SQL khó hiểu.
  const monCodes = Array.from(
    new Set(drafts.map((d) => d.maMon).filter((m): m is string => Boolean(m))),
  );
  const knownSubjects = new Set<string>();
  if (monCodes.length) {
    const placeholders = monCodes.map(() => "?").join(",");
    const rows = await query<{ ma_mon: string }>(
      `SELECT ma_mon FROM mon_thi WHERE ma_mon IN (${placeholders})`,
      monCodes,
    );
    for (const r of rows) knownSubjects.add(r.ma_mon);
  }

  const seen = new Set<string>();
  const rows: ImportPreviewRow[] = [];
  const errors: ImportPreview["errors"] = [];
  let trungLap = 0;

  for (const d of drafts) {
    const key = `${d.maSv}::${d.maMon ?? "*"}`;
    let loi = d.loi;

    if (!loi && seen.has(key)) {
      trungLap += 1;
      loi = "Trùng mã trong cùng file (đã có dòng trước đó)";
    }
    if (!loi && !known.has(d.maSv)) {
      loi = "Mã sinh viên không có trong hệ thống";
    }
    if (!loi && d.maMon && !knownSubjects.has(d.maMon)) {
      loi = `Mã học phần "${d.maMon}" không có trong danh mục môn thi`;
    }
    if (!loi) seen.add(key);

    const sv = known.get(d.maSv);
    rows.push({
      dong: d.dong,
      maSv: d.maSv,
      hoTen: sv?.hoTen ?? null,
      lop: sv?.lop ?? null,
      maMon: d.maMon,
      trangThai: d.trangThai,
      lyDo: d.lyDo,
      hopLe: !loi,
      loi,
    });

    if (loi) errors.push({ dong: d.dong, maSv: d.maSv, lyDo: loi });
  }

  const hopLe = rows.filter((r) => r.hopLe);
  return {
    tenFile: fileName,
    tongDong: rows.length,
    hopLe: hopLe.length,
    khop: hopLe.length,
    khongTonTai: rows.filter((r) => r.loi === "Mã sinh viên không có trong hệ thống").length,
    trungLap,
    errors,
    rows,
  };
}

export interface ImportCommitResult {
  maDot: number;
  tongDong: number;
  soThanhCong: number;
  soLoi: number;
  errors: ImportPreview["errors"];
}

/**
 * Ghi các dòng hợp lệ vào DB và lưu một dòng nhật ký.
 *
 * Chỉ ghi dòng hợp lệ; dòng lỗi được trả về nguyên văn để người dùng sửa file
 * và nạp lại. Không ghi nửa vời: nếu một dòng làm lỗi thì cả lượt import
 * dừng và báo, vì danh sách cấm thi mà nạp thiếu còn tệ hơn nạp lại.
 */
export async function commitImport(
  fileName: string,
  text: string,
  nguoiImport: string | null,
): Promise<ImportCommitResult> {
  const preview = await previewImport(fileName, text);
  const valid = preview.rows.filter((r) => r.hopLe);

  const log = await execute(
    `INSERT INTO dot_import_cam_thi (ten_file, tong_dong, so_thanh_cong, so_loi, nguoi_import)
     VALUES (?, ?, 0, ?, ?)`,
    [fileName, preview.tongDong, preview.errors.length, nguoiImport],
  );
  const maDot = log.insertId;

  let ok = 0;
  const failures: ImportPreview["errors"] = [];

  for (const r of valid) {
    try {
      await upsertStatus(
        {
          maSv: r.maSv,
          maMon: r.maMon,
          trangThai: r.trangThai,
          lyDo: r.lyDo,
        },
        "IMPORT_CSV",
      );
      ok += 1;
    } catch (err) {
      failures.push({ dong: r.dong, maSv: r.maSv, lyDo: (err as Error).message });
    }
  }

  await execute(
    `UPDATE dot_import_cam_thi
        SET so_thanh_cong = ?, so_loi = ?
      WHERE ma_dot = ?`,
    [ok, preview.errors.length + failures.length, maDot],
  );

  return {
    maDot,
    tongDong: preview.tongDong,
    soThanhCong: ok,
    soLoi: preview.errors.length + failures.length,
    errors: [...preview.errors, ...failures],
  };
}

/* ==================================================================== */
/* Truy vấn sinh viên                                                   */
/* ==================================================================== */

export interface StudentQuery {
  /** Tìm trong mã sinh viên, họ tên, lớp, và mã/tên học phần */
  keyword?: string;
  maMon?: string;
  lop?: string;
  trangThai?: ExamStatus | "BINH_THUONG";
  limit?: number;
}

export interface StudentQueryRow {
  maSv: string;
  hoTen: string;
  lop: string;
  khoa: string;
  email: string;
  soMonDangKy: number;
  trangThai: ExamStatus | null;
  lyDo: string | null;
  monBiAnhHuong: string[];
}

/**
 * Tra cứu sinh viên theo mã, tên, lớp, học phần và trạng thái.
 *
 * Lọc theo trạng thái làm ở SQL vì nó là điều kiện chính của màn hình
 * "danh sách chưa nộp học phí / bị cấm thi". Các từ khoá còn lại dùng LIKE,
 * đủ nhanh với quy mô vài nghìn sinh viên.
 */
export async function searchStudents(q: StudentQuery): Promise<StudentQueryRow[]> {
  const where: string[] = [];
  const params: unknown[] = [];

  const kw = q.keyword?.trim();
  if (kw) {
    where.push(
      `(sv.ma_sv LIKE ? OR sv.ho_ten LIKE ? OR sv.lop LIKE ?
        OR EXISTS (
          SELECT 1 FROM dang_ky_thi d2
            JOIN lich_thi l2 ON l2.ma_lich = d2.ma_lich
            JOIN mon_thi m2  ON m2.ma_mon  = l2.ma_mon
           WHERE d2.ma_sv = sv.ma_sv
             AND (m2.ma_mon LIKE ? OR m2.ten_mon LIKE ?)
        ))`,
    );
    const like = `%${kw}%`;
    params.push(like, like, like, like, like);
  }

  if (q.lop?.trim()) {
    where.push("sv.lop = ?");
    params.push(q.lop.trim());
  }

  if (q.maMon?.trim()) {
    where.push(
      `EXISTS (
         SELECT 1 FROM dang_ky_thi d3
           JOIN lich_thi l3 ON l3.ma_lich = d3.ma_lich
          WHERE d3.ma_sv = sv.ma_sv AND l3.ma_mon = ?
       )`,
    );
    params.push(q.maMon.trim());
  }

  // Trạng thái: lọc sau khi đã gộp, vì "bình thường" nghĩa là KHÔNG có dòng nào.
  if (q.trangThai === "BINH_THUONG") {
    where.push("NOT EXISTS (SELECT 1 FROM trang_thai_thi t WHERE t.ma_sv = sv.ma_sv)");
  } else if (q.trangThai) {
    where.push(
      `EXISTS (SELECT 1 FROM trang_thai_thi t WHERE t.ma_sv = sv.ma_sv AND t.trang_thai = ?)`,
    );
    params.push(q.trangThai);
  }

  const limit = Math.min(Math.max(q.limit ?? 200, 1), 1000);

  const rows = await query<{
    ma_sv: string;
    ho_ten: string;
    lop: string;
    khoa: string;
    email: string;
    so_mon: number;
  }>(
    `SELECT sv.ma_sv, sv.ho_ten, sv.lop, sv.khoa, sv.email,
            (SELECT COUNT(DISTINCT l.ma_mon)
               FROM dang_ky_thi d
               JOIN lich_thi l ON l.ma_lich = d.ma_lich
              WHERE d.ma_sv = sv.ma_sv) AS so_mon
       FROM sinh_vien sv
      ${where.length ? `WHERE ${where.join(" AND ")}` : ""}
      ORDER BY sv.ma_sv
      LIMIT ${limit}`,
    params,
    // Truy vấn này chạm trang_thai_thi, nên phải đọc ở master cho khớp với
    // dữ liệu vừa ghi.
    "master",
  );

  if (!rows.length) return [];

  // Nạp trạng thái cho đúng những sinh viên vừa tìm được.
  const codes = rows.map((r) => r.ma_sv);
  const placeholders = codes.map(() => "?").join(",");
  const statuses = await query<StatusRow>(
    `SELECT ma_sv, ma_mon, trang_thai, ly_do, nguon, cap_nhat_luc
       FROM trang_thai_thi
      WHERE ma_sv IN (${placeholders})`,
    codes,
    "master",
  );
  const mapped = statuses.map(mapStatus);

  const byStudent = new Map<string, StudentExamStatus[]>();
  for (const s of mapped) {
    const list = byStudent.get(s.maSv) ?? [];
    list.push(s);
    byStudent.set(s.maSv, list);
  }

  return rows.map((r) => {
    const list = byStudent.get(r.ma_sv) ?? [];
    const hard = list.find((s) => s.trangThai === "CAM_THI") ?? list[0] ?? null;
    return {
      maSv: r.ma_sv,
      hoTen: r.ho_ten,
      lop: r.lop,
      khoa: r.khoa,
      email: r.email,
      soMonDangKy: Number(r.so_mon),
      trangThai: hard?.trangThai ?? null,
      lyDo: hard?.lyDo ?? null,
      monBiAnhHuong: list.filter((s) => s.maMon).map((s) => s.maMon as string),
    };
  });
}

/** Danh sách lớp, để đổ vào ô chọn. */
export async function fetchClasses(): Promise<string[]> {
  const rows = await query<{ lop: string }>(
    `SELECT DISTINCT lop FROM sinh_vien ORDER BY lop`,
  );
  return rows.map((r) => r.lop);
}

/** Lịch sử các lần import, mới nhất trước. */
export async function fetchImportLog(limit = 20) {
  return query<{
    ma_dot: number;
    ten_file: string;
    tong_dong: number;
    so_thanh_cong: number;
    so_loi: number;
    nguoi_import: string | null;
    tao_luc: string;
  }>(
    `SELECT ma_dot, ten_file, tong_dong, so_thanh_cong, so_loi, nguoi_import, tao_luc
       FROM dot_import_cam_thi
      ORDER BY ma_dot DESC
      LIMIT ${Math.min(Math.max(limit, 1), 100)}`,
    [],
    "master",
  );
}
