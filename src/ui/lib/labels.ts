/* ============================================================================
 * Nhãn hiển thị cho giáo vụ.
 *
 * Nguyên tắc: mọi chữ trên màn hình phải đọc được bằng ngôn ngữ nghiệp vụ.
 * Ký hiệu của mô hình (|C|, n[c], f[c,r], α, β, γ, Z1, Z2, OPTIMAL) chỉ được
 * xuất hiện ở phần phụ, dạng chú thích nhỏ, cho người muốn đối chiếu.
 * ========================================================================== */

export type Tone = "success" | "info" | "warning" | "danger" | "muted" | "neutral";

/* -------------------------------------------------------------------------- */
/* Trạng thái một lần xếp lịch                                                */
/* -------------------------------------------------------------------------- */

export const STATUS_LABEL: Record<
  string,
  { text: string; plain: string; tone: Tone }
> = {
  OPTIMAL: {
    text: "Đã xếp xong",
    plain: "Phương án tốt nhất tìm được với dữ liệu hiện tại.",
    tone: "success",
  },
  FEASIBLE: {
    text: "Đã xếp xong",
    plain: "Dừng vì hết thời gian chờ, không phải lỗi.",
    tone: "info",
  },
  INFEASIBLE: {
    text: "Không xếp được",
    plain: "Không có cách xếp nào thoả toàn bộ điều kiện. Cần xem lại dữ liệu.",
    tone: "danger",
  },
};

export function statusOf(status: string) {
  return (
    STATUS_LABEL[status] ?? {
      text: "Chưa rõ",
      plain: "Không có trạng thái cho lần chạy này.",
      tone: "info" as Tone,
    }
  );
}

/* -------------------------------------------------------------------------- */
/* Phòng máy                                                                  */
/* -------------------------------------------------------------------------- */

export const ROOM_STATUS_LABEL: Record<string, string> = {
  Working: "Đang dùng được",
  Maintenance: "Đang bảo trì",
};

export function roomStatusLabel(tinhTrang: string) {
  return ROOM_STATUS_LABEL[tinhTrang] ?? tinhTrang;
}

/* -------------------------------------------------------------------------- */
/* Ca thi                                                                     */
/* -------------------------------------------------------------------------- */

export function caLabel(caThi: number) {
  return `Ca ${caThi}`;
}

export function caWithTime(caThi: number, gioBd: string, gioKt: string) {
  return `Ca ${caThi} · ${gioBd}–${gioKt}`;
}

/* -------------------------------------------------------------------------- */
/* Hình thức thi                                                              */
/* -------------------------------------------------------------------------- */

export const HINH_THUC_PLAIN: Record<string, string> = {
  "On-screen": "Thi trên máy",
  "Computer-based test": "Trắc nghiệm trên máy",
  Practical: "Thực hành",
};

export function hinhThucPlain(hinhThuc: string) {
  return HINH_THUC_PLAIN[hinhThuc] ?? hinhThuc;
}

/* -------------------------------------------------------------------------- */
/* Phần mềm                                                                   */
/* -------------------------------------------------------------------------- */

/** Môn không yêu cầu phần mềm nào: phòng nào cũng nhận được. */
export function softwarePlain(phanMem: string[]) {
  return phanMem.length ? phanMem.join(", ") : "Không cần phần mềm riêng";
}

/* -------------------------------------------------------------------------- */
/* Câu tóm tắt kết quả bằng lời                                               */
/* -------------------------------------------------------------------------- */

export interface ResultSummaryInput {
  totalSubjects: number;
  scheduledSubjects: number;
  unscheduledSubjects: number;
  sessions: number;
  roomsOpened: number;
  days: number;
  studentsPlaced: number;
  totalStudents: number;
}

/**
 * Một câu tiếng Việt mô tả lần xếp lịch vừa rồi, để giáo vụ đọc là hiểu ngay
 * chuyện gì đã xảy ra mà không phải tra bảng số.
 */
export function summarizeResult(r: ResultSummaryInput): string {
  if (r.unscheduledSubjects > 0) {
    return `Đã xếp ${r.scheduledSubjects}/${r.totalSubjects} học phần vào ${r.days} ngày thi, dùng ${r.roomsOpened} phòng. Còn ${r.unscheduledSubjects} học phần chưa xếp được.`;
  }
  return `Đã xếp đủ ${r.totalSubjects} học phần vào ${r.days} ngày thi, dùng ${r.roomsOpened} phòng, tổng ${r.sessions} ca thi.`;
}

/* -------------------------------------------------------------------------- */
/* Gợi ý xử lý khi có học phần không xếp được                                 */
/* -------------------------------------------------------------------------- */

/**
 * Đoán nguyên nhân theo dữ liệu đầu vào, trả về câu gợi ý hành động cụ thể.
 * Đây là suy luận từ dữ liệu, không phải kết luận của bộ xếp lịch.
 */
export function unscheduledHint(input: {
  siSo: number;
  soPhongDuPhanMem: number;
  tongChoDuPhanMem: number;
  coPhongNaoDuPhanMem: boolean;
}): string {
  if (!input.coPhongNaoDuPhanMem) {
    return "Không phòng nào đang dùng được cài đủ phần mềm học phần này yêu cầu. Cần cài thêm phần mềm, hoặc đưa phòng đang bảo trì vào dùng.";
  }
  if (input.tongChoDuPhanMem < input.siSo) {
    return `Có ${input.soPhongDuPhanMem} phòng đủ phần mềm với tổng ${input.tongChoDuPhanMem} chỗ, sĩ số là ${input.siSo}. Cần thêm phòng hoặc chia thành nhiều đợt thi.`;
  }
  return "Đủ phòng và đủ chỗ, nhưng các học phần khác đã chiếm hết ca phù hợp. Thử tăng thời gian chờ, hoặc thêm ca thi trong ngày.";
}

/* -------------------------------------------------------------------------- */
/* Trạng thái dự thi                                                          */
/* -------------------------------------------------------------------------- */

export const EXAM_STATUS_LABEL: Record<
  string,
  { text: string; short: string; plain: string; tone: Tone }
> = {
  CHUA_NOP_HOC_PHI: {
    text: "Chưa nộp học phí",
    short: "Chưa nộp HP",
    plain: "Nộp học phí xong thì được dự thi.",
    tone: "warning",
  },
  CAM_THI: {
    text: "Cấm thi",
    short: "Cấm thi",
    plain: "Không được dự thi (kỷ luật, đánh trượt môn).",
    tone: "danger",
  },
};

export function examStatusOf(trangThai: string | null | undefined) {
  if (!trangThai) return null;
  return EXAM_STATUS_LABEL[trangThai] ?? null;
}

/** Lớp nền của một dòng trong bảng: vàng cho tạm hoãn, đỏ cho cấm hẳn. */
export function rowToneClass(trangThai: string | null | undefined): string {
  if (trangThai === "CAM_THI") return "bg-rose-50/80 hover:bg-rose-50";
  if (trangThai === "CHUA_NOP_HOC_PHI") return "bg-amber-50/70 hover:bg-amber-50";
  return "";
}

