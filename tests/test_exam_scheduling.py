from datetime import date, time

import pytest

from scripts.generate_data import assign_proctors, generated_proctor
from src.algo.exam_scheduler import schedule_cp_sat


def _slots():
    return [
        {
            "ma_khung": 1,
            "ngay_thi": date(2026, 12, 1),
            "ca_thi": 1,
            "gio_bat_dau": time(7, 0),
            "gio_ket_thuc": time(9, 0),
        },
        {
            "ma_khung": 2,
            "ngay_thi": date(2026, 12, 1),
            "ca_thi": 2,
            "gio_bat_dau": time(9, 30),
            "gio_ket_thuc": time(11, 30),
        },
    ]


def test_generated_proctors_are_complete_records():
    proctors = generated_proctor(3)

    assert len(proctors) == 3
    assert len({proctor["ma_gt"] for proctor in proctors}) == 3
    assert all(proctor["ma_gt"].startswith("GT") for proctor in proctors)
    assert all({"ngay_sinh", "gioi_tinh", "email", "so_dien_thoai", "khoa"} <= proctor.keys()
               for proctor in proctors)


def test_proctor_assignments_cover_sessions_without_shift_conflicts():
    sessions = [
        {"ma_lich": 1, "ma_khung": 1},
        {"ma_lich": 2, "ma_khung": 2},
    ]
    proctors = [{"ma_gt": "GT1"}, {"ma_gt": "GT2"}]

    assignments = assign_proctors(sessions, _slots(), proctors)
    by_session = {}
    by_proctor = {}
    for assignment in assignments:
        by_session.setdefault(assignment["ma_lich"], []).append(assignment["ma_gt"])
        by_proctor.setdefault(assignment["ma_gt"], []).append(assignment["ma_khung"])

    assert set(by_session) == {1, 2}
    assert all(1 <= len(assigned) <= 2 for assigned in by_session.values())
    assert all(len(set(shifts)) == len(shifts) for shifts in by_proctor.values())
    assert all(len(set(shifts)) >= 2 for shifts in by_proctor.values())


def test_proctor_assignment_rejects_a_day_with_only_one_exam_shift():
    with pytest.raises(ValueError, match="ít nhất 2 ca/ngày"):
        assign_proctors(
            [{"ma_lich": 1, "ma_khung": 1}],
            _slots(),
            [{"ma_gt": "GT1"}],
        )


def test_subject_over_room_capacity_uses_combined_eligible_capacity():
    students = [{"ma_sv": f"SV{i}", "lop": "CNTT"} for i in range(5)]
    subjects = [{"ma_mon": "M1", "thoi_luong_phut": 60}]
    rooms = [
        {"ma_phong": "P1", "suc_chua": 2, "tinh_trang": "Working"},
        {"ma_phong": "P2", "suc_chua": 2, "tinh_trang": "Working"},
    ]
    sessions, registrations, unscheduled, _ = schedule_cp_sat(
        students=students,
        subjects=subjects,
        rooms=rooms,
        room_software=[],
        subject_software=[],
        slots=_slots(),
        enrolled={"M1": [student["ma_sv"] for student in students]},
        random_scores=False,
        time_limit=5,
        workers=1,
    )

    assert not unscheduled
    assert {session["ma_khung"] for session in sessions} == {1, 2}
    assert {registration["ma_sv"] for registration in registrations} == {
        student["ma_sv"] for student in students
    }
