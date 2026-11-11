import type { SolverParams, User } from "./types";

/* ------------------------------------------------------------------ */
/* Tài khoản demo                                                      */
/* Một vai trò duy nhất: giáo vụ làm toàn bộ công việc xếp lịch,       */
/* kể cả chỉnh mức ưu tiên.                                            */
/*                                                                     */
/* Lưu ý: đây là tài khoản đăng nhập, KHÔNG phải dữ liệu nghiệp vụ.    */
/* Học phần / phòng máy / khung giờ / sinh viên / đăng ký môn đọc từ   */
/* MySQL qua `lib/dataset.tsx` và `lib/repository.ts`.                 */
/* ------------------------------------------------------------------ */

export interface Account extends User {
  password: string;
}

export const ACCOUNTS: Account[] = [
  {
    username: "giaovu",
    password: "giaovu",
    name: "Nguyễn Thị Mai",
    dept: "Phòng Đào tạo",
    email: "ntmai@university.edu.vn",
    role: "giaovu",
  },
];

/* ------------------------------------------------------------------ */
/* Tham số mặc định của hàm mục tiêu và bộ giải                        */
/* ------------------------------------------------------------------ */

export const DEFAULT_PARAMS: SolverParams = {
  alpha: 1,
  beta: 3,
  gamma: 1,
  skipPenalty: 1000,
  timeLimit: 20,
  seed: 42,
  workers: 8,
};

/* ------------------------------------------------------------------ */
/* Ràng buộc cứng của mô hình, đánh số đúng như trong exam_scheduler.py */
/* ------------------------------------------------------------------ */

export const HARD_CONSTRAINTS = [
  {
    id: "C1",
    title: "Mỗi môn thi đúng một khung giờ",
    formula: "Σ_t y[c,t] + skip[c] = 1",
    desc: "Môn được xếp đúng một lần, hoặc bị bỏ và ghi nhận là chưa xếp được.",
  },
  {
    id: "C2",
    title: "Một phòng, một ca mỗi khung giờ",
    formula: "Σ_c x[c,r,t] ≤ 1",
    desc: "Không hai môn cùng chiếm một phòng trong cùng khung giờ.",
  },
  {
    id: "C3",
    title: "Tổng chỗ ngồi phủ hết sĩ số",
    formula: "Σ_r K[r]·x[c,r,t] ≥ n[c]·y[c,t]",
    desc: "Môn đông sinh viên được tách sang nhiều phòng trong cùng khung giờ.",
  },
  {
    id: "C4",
    title: "Sinh viên không trùng giờ thi",
    formula: "Σ_{c∈g} y[c,t] ≤ 1",
    desc: "Mỗi nhóm sinh viên có cùng tập môn đăng ký chỉ thi tối đa một ca mỗi khung giờ.",
  },
  {
    id: "C5",
    title: "Môn có ca khi và chỉ khi có phòng",
    formula: "Σ_r x[c,r,t] ≥ y[c,t]",
    desc: "Môn được coi là đã xếp chỉ khi thực sự có ít nhất một phòng nhận.",
  },
  {
    id: "C7",
    title: "Phòng phải được mở mới dùng được",
    formula: "x[c,r,t] ≤ w[r]",
    desc: "Mọi ca dùng phòng đều kéo theo biến mở phòng, và phòng đó bị tính chi phí.",
  },
  {
    id: "C8",
    title: "Áp lực lịch thi trong ngày",
    formula: "p[g,d] ≥ Σ y[c,t] − 1",
    desc: "Thi k ca trong một ngày bị tính k−1 lần áp lực, nhân với số sinh viên của nhóm.",
  },
  {
    id: "f[c,r]",
    title: "Tương thích phần mềm",
    formula: "need[c] ⊆ have[r]",
    desc: "Biến x[c,r,t] chỉ tồn tại khi phòng cài đủ toàn bộ phần mềm môn thi yêu cầu.",
  },
];
