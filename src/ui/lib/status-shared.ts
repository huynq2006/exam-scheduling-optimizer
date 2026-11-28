/**
 * Logic trạng thái dùng được ở CẢ client và server.
 *
 * `lib/status.ts` mở kết nối MySQL nên chỉ chạy được trên server; component
 * nào cần tính trạng thái hiệu lực phải lấy từ đây, không import nhầm file kia.
 */

import type { StudentExamStatus } from "./types";

/**
 * Trạng thái hiệu lực cho một cặp (sinh viên, học phần).
 *
 * Quy tắc: CAM_THI thắng CHUA_NOP_HOC_PHI; cùng mức thì phạm vi hẹp (theo
 * môn) thắng phạm vi rộng. Khớp đúng với view v_trang_thai_theo_ca.
 */
export function effectiveStatus(
  list: StudentExamStatus[],
  maSv: string,
  maMon: string,
): StudentExamStatus | null {
  let best: StudentExamStatus | null = null;
  let bestRank = -1;

  for (const s of list) {
    if (s.maSv !== maSv) continue;
    if (s.maMon !== null && s.maMon !== maMon) continue;

    const rank = (s.trangThai === "CAM_THI" ? 2 : 1) * 10 + (s.maMon ? 1 : 0);
    if (rank > bestRank) {
      best = s;
      bestRank = rank;
    }
  }

  return best;
}
