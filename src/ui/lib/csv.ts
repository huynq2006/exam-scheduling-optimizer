/**
 * Đọc file CSV danh sách cấm thi.
 *
 * File thật của Phòng Đào tạo không bao giờ sạch: có BOM từ Excel, có dấu
 * chấm phẩy vì máy đặt vùng Việt Nam, có ô bọc ngoặc kép, có tiêu đề tiếng
 * Việt có dấu. Bộ đọc này xử lý đủ mấy trường hợp đó rồi mới trả lỗi.
 *
 * Không phụ thuộc thư viện ngoài: file chỉ vài nghìn dòng, tự viết thì kiểm
 * soát được từng trường hợp.
 */

import type { ExamStatus, ImportPreviewRow } from "./types";

/* ------------------------------------------------------------------ */
/* Tách ô                                                              */
/* ------------------------------------------------------------------ */

/** Đoán dấu phân cách từ dòng đầu: phẩy, chấm phẩy hay tab. */
function detectDelimiter(headerLine: string): string {
  const counts: Array<[string, number]> = [
    [",", (headerLine.match(/,/g) ?? []).length],
    [";", (headerLine.match(/;/g) ?? []).length],
    ["\t", (headerLine.match(/\t/g) ?? []).length],
  ];
  counts.sort((a, b) => b[1] - a[1]);
  return counts[0][1] > 0 ? counts[0][0] : ",";
}

/**
 * Tách một dòng thành các ô, tôn trọng ngoặc kép.
 * "" bên trong ô đã bọc nghĩa là một dấu ngoặc kép thật.
 */
function splitLine(line: string, delimiter: string): string[] {
  const out: string[] = [];
  let cell = "";
  let quoted = false;

  for (let i = 0; i < line.length; i += 1) {
    const ch = line[i];

    if (quoted) {
      if (ch === '"') {
        if (line[i + 1] === '"') {
          cell += '"';
          i += 1;
        } else {
          quoted = false;
        }
      } else {
        cell += ch;
      }
      continue;
    }

    if (ch === '"') {
      quoted = true;
      continue;
    }
    if (ch === delimiter) {
      out.push(cell);
      cell = "";
      continue;
    }
    cell += ch;
  }

  out.push(cell);
  return out.map((c) => c.trim());
}

/* ------------------------------------------------------------------ */
/* Chuẩn hoá tiêu đề và giá trị                                        */
/* ------------------------------------------------------------------ */

/** Bỏ dấu tiếng Việt + hạ chữ thường, để so tiêu đề mà không cần đúng từng dấu. */
export function normalizeKey(value: string): string {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/đ/gi, "d")
    .replace(/[^a-z0-9]+/gi, "_")
    .replace(/^_+|_+$/g, "")
    .toLowerCase();
}

const COLUMN_ALIASES: Record<"maSv" | "maMon" | "trangThai" | "lyDo", string[]> = {
  maSv: ["ma_sv", "masv", "mssv", "ma_so_sinh_vien", "ma_sinh_vien", "student_id", "ma"],
  maMon: [
    "ma_mon",
    "mamon",
    "ma_hoc_phan",
    "ma_hp",
    "mahp",
    "ma_mon_hoc",
    "subject_id",
    "mon",
  ],
  trangThai: ["trang_thai", "trangthai", "status", "tinh_trang", "loai"],
  lyDo: ["ly_do", "lydo", "reason", "ghi_chu", "ghichu", "note", "noi_dung"],
};

function findColumn(headers: string[], aliases: string[]): number {
  for (let i = 0; i < headers.length; i += 1) {
    if (aliases.includes(headers[i])) return i;
  }
  return -1;
}

const STATUS_ALIASES: Record<string, ExamStatus> = {
  // Chưa nộp học phí -> cấm thi tạm thời
  chua_nop_hoc_phi: "CHUA_NOP_HOC_PHI",
  chua_nop_hp: "CHUA_NOP_HOC_PHI",
  chuanophocphi: "CHUA_NOP_HOC_PHI",
  no_hoc_phi: "CHUA_NOP_HOC_PHI",
  hoc_phi: "CHUA_NOP_HOC_PHI",
  no_fee: "CHUA_NOP_HOC_PHI",
  unpaid: "CHUA_NOP_HOC_PHI",
  tam_hoan: "CHUA_NOP_HOC_PHI",
  // Cấm thi hẳn
  cam_thi: "CAM_THI",
  camthi: "CAM_THI",
  banned: "CAM_THI",
  ky_luat: "CAM_THI",
  danh_truot: "CAM_THI",
  truot_mon: "CAM_THI",
  cam: "CAM_THI",
};

export function parseStatus(raw: string): ExamStatus | null {
  const key = normalizeKey(raw);
  if (!key) return null;
  return STATUS_ALIASES[key] ?? null;
}

/* ------------------------------------------------------------------ */
/* Đọc file                                                            */
/* ------------------------------------------------------------------ */

export interface ParsedCsv {
  headers: string[];
  /** Dòng dữ liệu thô, kèm số dòng thật trong file (để báo lỗi đúng chỗ). */
  rows: Array<{ line: number; cells: string[] }>;
  delimiter: string;
}

/**
 * Tách file thành tiêu đề + các dòng. Dòng trống bị bỏ qua nhưng vẫn giữ
 * số dòng gốc, vì "lỗi ở dòng 47" phải là dòng 47 trong Excel của người dùng.
 */
export function parseCsv(text: string): ParsedCsv {
  // Excel trên Windows hay ghi BOM; không cắt thì tiêu đề đầu tiên thành "\ufeffma_sv".
  const clean = text.replace(/^\uFEFF/, "");
  const lines = clean.split(/\r\n|\n|\r/);

  let headerIndex = -1;
  for (let i = 0; i < lines.length; i += 1) {
    if (lines[i].trim()) {
      headerIndex = i;
      break;
    }
  }
  if (headerIndex < 0) return { headers: [], rows: [], delimiter: "," };

  const delimiter = detectDelimiter(lines[headerIndex]);
  const headers = splitLine(lines[headerIndex], delimiter).map(normalizeKey);

  const rows: ParsedCsv["rows"] = [];
  for (let i = headerIndex + 1; i < lines.length; i += 1) {
    const raw = lines[i];
    if (!raw.trim()) continue;
    rows.push({ line: i + 1, cells: splitLine(raw, delimiter) });
  }

  return { headers, rows, delimiter };
}

/* ------------------------------------------------------------------ */
/* Biến dòng thô thành dòng nghiệp vụ                                  */
/* ------------------------------------------------------------------ */

export interface DraftRow {
  dong: number;
  maSv: string;
  maMon: string | null;
  trangThai: ExamStatus;
  lyDo: string | null;
  loi?: string;
}

/**
 * Đọc từng dòng. Chỉ kiểm tra những gì kiểm tra được mà không cần DB:
 * có mã sinh viên, có trạng thái đọc được. Việc mã có tồn tại thật hay
 * không do tầng repository trả lời.
 */
export function toDraftRows(parsed: ParsedCsv): DraftRow[] {
  const iSv = findColumn(parsed.headers, COLUMN_ALIASES.maSv);
  const iMon = findColumn(parsed.headers, COLUMN_ALIASES.maMon);
  const iTt = findColumn(parsed.headers, COLUMN_ALIASES.trangThai);
  const iLyDo = findColumn(parsed.headers, COLUMN_ALIASES.lyDo);

  return parsed.rows.map(({ line, cells }) => {
    const maSv = (iSv >= 0 ? cells[iSv] ?? "" : "").trim().toUpperCase();
    const rawMon = (iMon >= 0 ? cells[iMon] ?? "" : "").trim().toUpperCase();
    const rawTt = iTt >= 0 ? cells[iTt] ?? "" : "";
    const lyDo = (iLyDo >= 0 ? cells[iLyDo] ?? "" : "").trim() || null;

    const trangThai = parseStatus(rawTt);

    let loi: string | undefined;
    if (!maSv) loi = "Thiếu mã sinh viên";
    else if (!trangThai) {
      loi = rawTt.trim()
        ? `Không hiểu trạng thái "${rawTt.trim()}"`
        : "Thiếu cột trạng thái";
    }

    return {
      dong: line,
      maSv,
      maMon: rawMon || null,
      trangThai: trangThai ?? "CAM_THI",
      lyDo,
      loi,
    };
  });
}

/** Tiêu đề bắt buộc — dùng để báo lỗi ngay khi người dùng vừa chọn file. */
export function missingColumns(headers: string[]): string[] {
  const missing: string[] = [];
  if (findColumn(headers, COLUMN_ALIASES.maSv) < 0) missing.push("ma_sv");
  if (findColumn(headers, COLUMN_ALIASES.trangThai) < 0) missing.push("trang_thai");
  return missing;
}

export type { ImportPreviewRow };
