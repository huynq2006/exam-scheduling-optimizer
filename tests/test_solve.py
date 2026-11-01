"""
test_solve.py
=============
Bộ test độc lập cho hàm solve() trong src/algo/exam_scheduler.py.

Yêu cầu:
  - Không kết nối Database.
  - Dữ liệu mock khai báo trực tiếp trong file.
  - 3 kịch bản: hợp lệ, vô nghiệm, chia phòng + bảo trì.

Chạy:
  python -m pytest tests/test_solve.py -v -s
"""

import sys
import os
from datetime import date, time

# pyrefly: ignore[missing-import]
import pytest

# Đảm bảo project root nằm trong sys.path để import được src.*
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.algo.exam_scheduler import ProblemInstance, solve


# ==============================================================================
#  MOCK DATA (dữ liệu giả, khai báo tập trung)
# ==============================================================================

# --- Phần mềm (pm=1: Python, pm=2: MySQL, pm=3: AutoCAD) ---
MOCK_ROOM_SOFTWARE = [
    {"ma_phong": "P101", "ma_pm": 1},           # Python
    {"ma_phong": "P102", "ma_pm": 1},           # Python
    {"ma_phong": "LAB1", "ma_pm": 1},           # Python
    {"ma_phong": "LAB1", "ma_pm": 2},           # MySQL
    {"ma_phong": "MAINT", "ma_pm": 1},          # Python  (phòng đang BẢO TRÌ)
    {"ma_phong": "MAINT", "ma_pm": 2},          # MySQL   (phòng đang BẢO TRÌ)
]

MOCK_SUBJECT_SOFTWARE = [
    {"ma_mon": "CS101", "ma_pm": 1},            # CS101 cần Python  -> P101, P102, LAB1
    {"ma_mon": "DB201", "ma_pm": 2},            # DB201 cần MySQL   -> chỉ LAB1
    # ENG101 không cần phần mềm              -> bất kỳ phòng nào
    {"ma_mon": "CAD501", "ma_pm": 3},           # CAD501 cần AutoCAD -> không phòng nào!
]

# --- Phòng thi ---
MOCK_ROOMS = [
    {"ma_phong": "P101",  "suc_chua": 10, "tinh_trang": "Working"},
    {"ma_phong": "P102",  "suc_chua": 10, "tinh_trang": "Working"},
    {"ma_phong": "LAB1",  "suc_chua": 10, "tinh_trang": "Working"},
    {"ma_phong": "MAINT", "suc_chua": 30, "tinh_trang": "Maintenance"},  # BẢO TRÌ
]

# --- Khung giờ ---
MOCK_SLOTS = [
    {"ma_khung": 1, "ngay_thi": date(2026, 12, 1), "gio_bat_dau": time(7, 30), "gio_ket_thuc": time(9, 30)},
    {"ma_khung": 2, "ngay_thi": date(2026, 12, 1), "gio_bat_dau": time(10, 0), "gio_ket_thuc": time(12, 0)},
    {"ma_khung": 3, "ngay_thi": date(2026, 12, 2), "gio_bat_dau": time(7, 30), "gio_ket_thuc": time(9, 30)},
    {"ma_khung": 4, "ngay_thi": date(2026, 12, 2), "gio_bat_dau": time(10, 0), "gio_ket_thuc": time(12, 0)},
]

# --- Môn thi ---
MOCK_SUBJECTS_VALID = [
    {"ma_mon": "CS101",  "ten_mon": "Lập trình Python",  "thoi_luong_phut": 90},
    {"ma_mon": "DB201",  "ten_mon": "Cơ sở dữ liệu",     "thoi_luong_phut": 90},
    {"ma_mon": "ENG101", "ten_mon": "Tiếng Anh",          "thoi_luong_phut": 90},
]

MOCK_SUBJECTS_INFEASIBLE = [
    {"ma_mon": "CS101",  "ten_mon": "Lập trình Python",  "thoi_luong_phut": 90},
    {"ma_mon": "CAD501", "ten_mon": "Đồ họa AutoCAD",    "thoi_luong_phut": 90},  # VÔ NGHIỆM
]

# --- Sinh viên ---
MOCK_STUDENTS = [{"ma_sv": f"SV{i:03d}", "ho_ten": f"Sinh vien {i}"} for i in range(1, 26)]


# ==============================================================================
#  HELPER: Kiểm tra tất cả ràng buộc cứng
# ==============================================================================

def verify_constraints(rooms, room_software, subject_software, sessions, registrations):
    """
    Kiểm tra 4 ràng buộc cứng bắt buộc:
      1. Không trùng phòng / ca: mỗi (ma_phong, ma_khung) xuất hiện đúng 1 lần.
      2. Không trùng ca sinh viên: sinh viên không thi 2 môn cùng khung giờ.
      3. Đủ phần mềm: phòng phải cài đủ phần mềm môn thi yêu cầu.
      4. Không vượt sức chứa: số sinh viên / phòng <= suc_chua.
    Trả về dict {ràng_buộc: True/False} và thông điệp lỗi nếu có.
    """
    room_sw   = {}  # {ma_phong: {ma_pm}}
    for link in room_software:
        room_sw.setdefault(link["ma_phong"], set()).add(link["ma_pm"])

    subj_sw   = {}  # {ma_mon: {ma_pm}}
    for link in subject_software:
        subj_sw.setdefault(link["ma_mon"], set()).add(link["ma_pm"])

    cap_map   = {r["ma_phong"]: r["suc_chua"] for r in rooms}
    sess_map  = {s["ma_lich"]: s for s in sessions}

    errors = []

    # ── Ràng buộc 1: không trùng phòng / ca ───────────────────────────────
    room_slots = [(s["ma_phong"], s["ma_khung"]) for s in sessions]
    c1_ok = len(room_slots) == len(set(room_slots))
    if not c1_ok:
        dupes = [x for x in room_slots if room_slots.count(x) > 1]
        errors.append(f"[C1] TRÙNG PHÒNG/CA: {set(dupes)}")

    # ── Ràng buộc 2: không trùng ca sinh viên ─────────────────────────────
    c2_ok = True
    sv_used_slots = {}
    for reg in registrations:
        slot = sess_map[reg["ma_lich"]]["ma_khung"]
        sv   = reg["ma_sv"]
        if slot in sv_used_slots.setdefault(sv, set()):
            c2_ok = False
            errors.append(f"[C2] SV {sv} thi 2 môn trong khung {slot}")
            break
        sv_used_slots[sv].add(slot)

    # ── Ràng buộc 3: đủ phần mềm ──────────────────────────────────────────
    c3_ok = True
    for s in sessions:
        req   = subj_sw.get(s["ma_mon"], set())
        avail = room_sw.get(s["ma_phong"], set())
        if not req.issubset(avail):
            c3_ok = False
            missing = req - avail
            errors.append(f"[C3] Phòng {s['ma_phong']} thiếu phần mềm {missing} cho môn {s['ma_mon']}")

    # ── Ràng buộc 4: không vượt sức chứa ─────────────────────────────────
    seated = {}
    for reg in registrations:
        seated[reg["ma_lich"]] = seated.get(reg["ma_lich"], 0) + 1
    c4_ok = True
    for ma_lich, count in seated.items():
        cap = cap_map.get(sess_map[ma_lich]["ma_phong"], 0)
        if count > cap:
            c4_ok = False
            errors.append(f"[C4] Ca {ma_lich}: {count} SV vượt sức chứa {cap}")

    return {
        "no_room_clash":    c1_ok,
        "no_student_clash": c2_ok,
        "software_ok":      c3_ok,
        "capacity_ok":      c4_ok,
    }, errors


def print_schedule(tag, sessions, registrations, unscheduled, stats):
    """In tóm tắt lịch xếp được để dễ theo dõi khi test."""
    print(f"\n{'='*60}")
    print(f"[{tag}]")
    print(f"  Solver status : {stats.get('status')}")
    print(f"  Solve time    : {stats.get('solve_time', 0):.3f}s")
    print(f"  Sessions      : {len(sessions)}")
    print(f"  Registrations : {len(registrations)}")
    print(f"  Unscheduled   : {len(unscheduled)}")
    if sessions:
        print("  --- Ca thi ---")
        for s in sorted(sessions, key=lambda x: (x["ma_khung"], x["ma_phong"])):
            n = sum(1 for r in registrations if r["ma_lich"] == s["ma_lich"])
            print(f"    Khung {s['ma_khung']} | {s['ma_phong']:6s} | {s['ma_mon']:8s} | {n} SV")
    if unscheduled:
        by_mon = {}
        for sv, mon in unscheduled:
            by_mon.setdefault(mon, []).append(sv)
        for mon, svs in by_mon.items():
            print(f"  [Unscheduled] {mon}: {len(svs)} SV")
    print(f"{'='*60}")


# ==============================================================================
#  TEST 1 – Đầu vào hợp lệ, kiểm tra ràng buộc
# ==============================================================================

class TestValidSchedule:
    """
    Kịch bản 1 – Đầu vào hoàn toàn hợp lệ.
    Kiểm tra: không trùng phòng/ca, không trùng ca SV,
              đủ phần mềm, không vượt sức chứa, mọi SV được xếp.
    """

    # Enrollment được inject từ ngoài (không random trong solver)
    ENROLLED = {
        "CS101":  [f"SV{i:03d}" for i in range(1, 9)],   # 8 SV
        "DB201":  [f"SV{i:03d}" for i in range(1, 6)],   # 5 SV, SV001..005 cũng thi CS101
        "ENG101": [f"SV{i:03d}" for i in range(9, 14)],  # 5 SV riêng
    }
    # Tổng unique đăng ký: CS101(8) + DB201(5) + ENG101(5) = 18 ô đăng ký

    def _run(self):
        instance = ProblemInstance(
            students       = MOCK_STUDENTS,
            subjects       = MOCK_SUBJECTS_VALID,
            rooms          = MOCK_ROOMS,
            room_software  = MOCK_ROOM_SOFTWARE,
            subject_software = MOCK_SUBJECT_SOFTWARE,
            slots          = MOCK_SLOTS,
        )
        return solve(instance, enrolled=self.ENROLLED, time_limit=15, seed=0, workers=4)

    def test_1a_solver_finds_feasible_solution(self):
        """Solver phải tìm ra lời giải OPTIMAL hoặc FEASIBLE."""
        sessions, regs, unsch, stats = self._run()
        print_schedule("TEST 1a", sessions, regs, unsch, stats)

        assert stats["status"] in ("OPTIMAL", "FEASIBLE"), (
            f"Solver không tìm được lời giải: {stats['status']}"
        )
        assert len(sessions) > 0, "Phải có ít nhất 1 ca thi được xếp"
        print("\n  [DONE - PASSED] Test 1a - solver tim duoc loi giai hop le")

    def test_1b_no_room_slot_double_booking(self):
        """Mỗi cặp (phòng, khung giờ) chỉ được xuất hiện đúng 1 lần."""
        sessions, regs, unsch, stats = self._run()
        checks, errors = verify_constraints(
            MOCK_ROOMS, MOCK_ROOM_SOFTWARE, MOCK_SUBJECT_SOFTWARE,
            sessions, regs
        )
        assert checks["no_room_clash"], (
            "TRÙNG PHÒNG / CA:\n  " + "\n  ".join(errors)
        )
        print("\n  [DONE - PASSED] Test 1b - khong co phong / ca bi dat trung")

    def test_1c_no_student_exam_clash(self):
        """Không sinh viên nào bị xếp thi 2 môn trong cùng khung giờ."""
        sessions, regs, unsch, stats = self._run()
        checks, errors = verify_constraints(
            MOCK_ROOMS, MOCK_ROOM_SOFTWARE, MOCK_SUBJECT_SOFTWARE,
            sessions, regs
        )
        assert checks["no_student_clash"], (
            "XUNG ĐỘT CA THI SINH VIÊN:\n  " + "\n  ".join(errors)
        )
        print("\n  [DONE - PASSED] Test 1c - khong co xung dot ca thi cua sinh vien")

    def test_1d_software_requirements_satisfied(self):
        """Phòng thi phải cài đủ phần mềm mà môn thi yêu cầu."""
        sessions, regs, unsch, stats = self._run()
        checks, errors = verify_constraints(
            MOCK_ROOMS, MOCK_ROOM_SOFTWARE, MOCK_SUBJECT_SOFTWARE,
            sessions, regs
        )
        assert checks["software_ok"], (
            "VI PHẠM YÊU CẦU PHẦN MỀM:\n  " + "\n  ".join(errors)
        )
        print("\n  [DONE - PASSED] Test 1d - tat ca phong dap ung du phan mem")

    def test_1e_capacity_not_exceeded(self):
        """Số sinh viên trong mỗi phòng không vượt sức chứa."""
        sessions, regs, unsch, stats = self._run()
        checks, errors = verify_constraints(
            MOCK_ROOMS, MOCK_ROOM_SOFTWARE, MOCK_SUBJECT_SOFTWARE,
            sessions, regs
        )
        assert checks["capacity_ok"], (
            "VƯỢT SỨC CHỨA:\n  " + "\n  ".join(errors)
        )
        print("\n  [DONE - PASSED] Test 1e - khong co phong bi vuot suc chua")

    def test_1f_all_students_accounted_for(self):
        """Tổng sinh viên = số đăng ký trong sessions + số chưa xếp được."""
        sessions, regs, unsch, stats = self._run()
        total_enrolled = sum(len(v) for v in self.ENROLLED.values())
        assert len(regs) + len(unsch) == total_enrolled, (
            f"Mất sinh viên! enrolled={total_enrolled}, "
            f"seated={len(regs)}, unscheduled={len(unsch)}"
        )
        print(f"\n  [DONE - PASSED] Test 1f - {len(regs)} SV duoc xep, {len(unsch)} SV chua xep / {total_enrolled} tong")


# ==============================================================================
#  TEST 2 – Đầu vào vô nghiệm (không thể xếp được)
# ==============================================================================

class TestInfeasibleSchedule:
    """
    Kịch bản 2 – Đầu vào có môn thi vô nghiệm.
    CAD501 yêu cầu AutoCAD (pm=3) – không phòng nào cài → không thể xếp.
    CS101 bình thường vẫn phải được xếp.
    """

    ENROLLED = {
        "CS101":  ["SV001", "SV002", "SV003"],   # hợp lệ
        "CAD501": ["SV004", "SV005", "SV006"],   # vô nghiệm
    }

    def _run(self):
        instance = ProblemInstance(
            students         = MOCK_STUDENTS,
            subjects         = MOCK_SUBJECTS_INFEASIBLE,
            rooms            = MOCK_ROOMS,
            room_software    = MOCK_ROOM_SOFTWARE,
            subject_software = MOCK_SUBJECT_SOFTWARE,
            slots            = MOCK_SLOTS,
        )
        return solve(instance, enrolled=self.ENROLLED, time_limit=10, seed=0)

    def test_2a_solver_does_not_crash(self):
        """Solver không được ném exception dù bài toán có môn vô nghiệm."""
        try:
            sessions, regs, unsch, stats = self._run()
        except Exception as exc:
            pytest.fail(f"Solver ném exception không mong muốn: {exc}")
        print_schedule("TEST 2a", sessions, regs, unsch, stats)
        print("\n  [DONE - PASSED] Test 2a - solver khong crash khi gap mon vo nghiem")

    def test_2b_infeasible_subject_students_in_unscheduled(self):
        """Tất cả SV của CAD501 (môn vô nghiệm) phải có trong danh sách unscheduled."""
        sessions, regs, unsch, stats = self._run()
        unsch_for_cad = {sv for sv, mon in unsch if mon == "CAD501"}
        expected = {"SV004", "SV005", "SV006"}
        assert expected == unsch_for_cad, (
            f"CAD501 unscheduled: kỳ vọng {expected}, nhận {unsch_for_cad}"
        )
        print(f"\n  [DONE - PASSED] Test 2b - {len(unsch_for_cad)} SV cua CAD501 deu nam trong unscheduled")

    def test_2c_feasible_subjects_still_scheduled(self):
        """CS101 vẫn phải được xếp dù CAD501 vô nghiệm."""
        sessions, regs, unsch, stats = self._run()
        cs101_sessions = [s for s in sessions if s["ma_mon"] == "CS101"]
        assert len(cs101_sessions) >= 1, (
            "CS101 hợp lệ nhưng không được xếp lịch!"
        )
        cs101_regs = {r["ma_sv"] for r in regs if
                      any(s["ma_lich"] == r["ma_lich"] and s["ma_mon"] == "CS101"
                          for s in sessions)}
        assert cs101_regs == {"SV001", "SV002", "SV003"}, (
            f"CS101 regs thiếu: {cs101_regs}"
        )
        print(f"\n  [DONE - PASSED] Test 2c - CS101 xep duoc {len(cs101_sessions)} ca, "
              f"{len(cs101_regs)} SV day du")

    def test_2d_unscheduled_students_not_in_sessions(self):
        """SV trong unscheduled KHÔNG được xuất hiện trong registrations."""
        sessions, regs, unsch, stats = self._run()
        unsch_svs = {sv for sv, _ in unsch}
        seated_svs = {r["ma_sv"] for r in regs}
        overlap = unsch_svs & seated_svs
        assert not overlap, (
            f"SV vừa unscheduled vừa seated: {overlap}"
        )
        print(f"\n  [DONE - PASSED] Test 2d - khong co SV nao vua unscheduled vua duoc xep cho")


# ==============================================================================
#  TEST 3 – Chia phòng + phòng bảo trì
# ==============================================================================

class TestRoomSplitAndMaintenance:
    """
    Kịch bản 3 – Kết hợp hai tình huống phức tạp:
      a) Chia phòng: CS101 có 22 SV, các phòng hoạt động chỉ chứa tối đa 10 mỗi phòng
         → solver phải tự động mở 3 phòng (10+10+2) TRONG CÙNG 1 khung giờ.
      b) Phòng bảo trì: MAINT có sức chứa 30 nhưng tinh_trang='Maintenance'
         → solver tuyệt đối không được dùng.
    """

    ENROLLED = {
        "CS101": [f"SV{i:03d}" for i in range(1, 23)],  # 22 SV > max 10 / phòng
    }

    def _run(self):
        instance = ProblemInstance(
            students         = MOCK_STUDENTS,
            subjects         = [MOCK_SUBJECTS_VALID[0]],   # chỉ CS101
            rooms            = MOCK_ROOMS,
            room_software    = MOCK_ROOM_SOFTWARE,
            subject_software = MOCK_SUBJECT_SOFTWARE,
            slots            = MOCK_SLOTS,
        )
        return solve(instance, enrolled=self.ENROLLED,
                     time_limit=15, seed=0, workers=4, rebalance=False)

    def test_3a_maintenance_room_never_used(self):
        """Phòng MAINT (bảo trì) tuyệt đối không được xuất hiện trong bất kỳ ca thi nào."""
        sessions, regs, unsch, stats = self._run()
        print_schedule("TEST 3a", sessions, regs, unsch, stats)

        used = {s["ma_phong"] for s in sessions}
        assert "MAINT" not in used, (
            f"Phòng bảo trì 'MAINT' được dùng trái phép! sessions = {sessions}"
        )
        print("\n  [DONE - PASSED] Test 3a - phong MAINT khong bi su dung")

    def test_3b_subject_split_across_multiple_rooms(self):
        """CS101 có 22 SV phải được chia ra ít nhất 3 ca/phòng trong cùng 1 khung giờ."""
        sessions, regs, unsch, stats = self._run()
        cs_sessions = [s for s in sessions if s["ma_mon"] == "CS101"]

        assert len(cs_sessions) >= 3, (
            f"Kỳ vọng >= 3 ca để chứa 22 SV, nhận {len(cs_sessions)}: {cs_sessions}"
        )
        # Tất cả ca CS101 phải nằm trong cùng 1 khung giờ
        slots_used = {s["ma_khung"] for s in cs_sessions}
        assert len(slots_used) == 1, (
            f"CS101 bị xếp rải ra nhiều khung giờ khác nhau: {slots_used}"
        )
        print(f"\n  [DONE - PASSED] Test 3b - CS101 chia thanh {len(cs_sessions)} phong "
              f"trong khung gio {slots_used.pop()}")

    def test_3c_all_22_students_seated(self):
        """Toàn bộ 22 SV của CS101 phải có chỗ ngồi (không có unscheduled)."""
        sessions, regs, unsch, stats = self._run()
        assert len(regs) == 22, (
            f"Kỳ vọng 22 đăng ký, nhận {len(regs)}"
        )
        assert len(unsch) == 0, (
            f"Kỳ vọng 0 unscheduled, nhận {len(unsch)}"
        )
        print(f"\n  [DONE - PASSED] Test 3c - du 22 / 22 SV duoc xep cho")

    def test_3d_no_capacity_exceeded_after_split(self):
        """Sau khi chia phòng, mỗi phòng vẫn không vượt sức chứa 10."""
        sessions, regs, unsch, stats = self._run()
        checks, errors = verify_constraints(
            MOCK_ROOMS, MOCK_ROOM_SOFTWARE, MOCK_SUBJECT_SOFTWARE,
            sessions, regs
        )
        assert checks["capacity_ok"], (
            "VƯỢT SỨC CHỨA SAU KHI CHIA PHÒNG:\n  " + "\n  ".join(errors)
        )
        print("\n  [DONE - PASSED] Test 3d - khong co phong nao vuot suc chua 10 sau khi chia")

    def test_3e_no_student_clash_after_split(self):
        """Sau khi chia phòng, không SV nào bị trùng ca."""
        sessions, regs, unsch, stats = self._run()
        checks, errors = verify_constraints(
            MOCK_ROOMS, MOCK_ROOM_SOFTWARE, MOCK_SUBJECT_SOFTWARE,
            sessions, regs
        )
        assert checks["no_student_clash"], (
            "XUNG ĐỘT CA SAU KHI CHIA PHÒNG:\n  " + "\n  ".join(errors)
        )
        print("\n  [DONE - PASSED] Test 3e - khong co xung dot ca thi sau khi chia phong")

