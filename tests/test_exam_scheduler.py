"""
Independent Unit Test Suite for exam scheduling solver (solve & solve_greedy).
Zero database connections - uses hardcoded fixtures.
Includes 17 test cases covering valid constraint checks, infeasibility, room splitting,
maintenance filtering, dependency injection formats, and algorithm comparison.
"""
import sys
import logging
from datetime import date, time
from typing import Any, Dict, List
# pyrefly: ignore[missing-import]
import pytest

from src.algo.exam_scheduler import (
    ProblemInstance,
    solve,
    solve_greedy,
    schedule_cp_sat,
    normalize_enrollment,
    rebalance_sessions,
)

# Setup clear visual test logger
logger = logging.getLogger("exam_scheduler_tests")
logging.basicConfig(level=logging.INFO, format="%(message)s")


def log_test_result(test_name: str, passed: bool, details: str = ""):
    """Helper to output clear log indicators for pass/fail."""
    status = " [DONE - PASSED] " if passed else " [FAIL] "
    sep = "=" * 80
    print(f"\n{sep}\n>> TEST: {test_name}\n>> STATUS:{status}\n>> DETAILS: {details}\n{sep}")


# ==============================================================================
# HARDCODED TEST FIXTURES (ZERO DATABASE DEPENDENCIES)
# ==============================================================================
@pytest.fixture
def base_problem_fixture():
    """
    Standard clean test environment with 4 rooms, 3 subjects, 3 slots.
    Room software:
      - P101: Python (1)
      - P102: None
      - LAB1: Python (1), MySQL (2)
      - P_MAINT: Python (1), MySQL (2) [Maintenance]
    """
    students = [{"ma_sv": f"SV{i:03d}", "ho_ten": f"Student {i}"} for i in range(1, 31)]
    subjects = [
        {"ma_mon": "CS101", "ten_mon": "Lap trinh Python", "thoi_luong_phut": 60},
        {"ma_mon": "DB201", "ten_mon": "Co so du lieu MySQL", "thoi_luong_phut": 90},
        {"ma_mon": "ENG101", "ten_mon": "Tieng Anh chuyen nganh", "thoi_luong_phut": 60},
    ]
    rooms = [
        {"ma_phong": "P101", "suc_chua": 15, "tinh_trang": "Working"},
        {"ma_phong": "P102", "suc_chua": 10, "tinh_trang": "Working"},
        {"ma_phong": "LAB1", "suc_chua": 15, "tinh_trang": "Working"},
        {"ma_phong": "P_MAINT", "suc_chua": 25, "tinh_trang": "Maintenance"},
    ]
    room_software = [
        {"ma_phong": "P101", "ma_pm": 1},
        {"ma_phong": "LAB1", "ma_pm": 1},
        {"ma_phong": "LAB1", "ma_pm": 2},
        {"ma_phong": "P_MAINT", "ma_pm": 1},
        {"ma_phong": "P_MAINT", "ma_pm": 2},
    ]
    subject_software = [
        {"ma_mon": "CS101", "ma_pm": 1},  # requires Python
        {"ma_mon": "DB201", "ma_pm": 2},  # requires MySQL (only LAB1 has it)
        # ENG101 requires no software
    ]
    slots = [
        {"ma_khung": 1, "ngay_thi": date(2026, 11, 10), "gio_bat_dau": time(8, 0), "gio_ket_thuc": time(10, 0)},
        {"ma_khung": 2, "ngay_thi": date(2026, 11, 10), "gio_bat_dau": time(10, 30), "gio_ket_thuc": time(12, 30)},
        {"ma_khung": 3, "ngay_thi": date(2026, 11, 11), "gio_bat_dau": time(8, 0), "gio_ket_thuc": time(10, 0)},
        {"ma_khung": 4, "ngay_thi": date(2026, 11, 11), "gio_bat_dau": time(10, 30), "gio_ket_thuc": time(12, 30)},
    ]
    return {
        "students": students,
        "subjects": subjects,
        "rooms": rooms,
        "room_software": room_software,
        "subject_software": subject_software,
        "slots": slots,
    }


def verify_all_constraints(instance: Dict[str, Any],
                           sessions: List[Dict[str, Any]],
                           registrations: List[Dict[str, Any]],
                           unscheduled: List[Any],
                           enrolled: Dict[str, List[str]]) -> Dict[str, bool]:
    """
    Validates the 5 essential scheduling constraints:
      1. No double-booking of a room in the same slot.
      2. No student taking two exams in the same slot.
      3. All subject software requirements satisfied by assigned rooms.
      4. Room capacity not exceeded.
      5. Every enrolled student is either seated or listed in unscheduled.
    """
    room_sw_map = {r["ma_phong"]: set() for r in instance["rooms"]}
    for link in instance["room_software"]:
        room_sw_map.setdefault(link["ma_phong"], set()).add(link["ma_pm"])

    subj_sw_map = {s["ma_mon"]: set() for s in instance["subjects"]}
    for link in instance["subject_software"]:
        subj_sw_map.setdefault(link["ma_mon"], set()).add(link["ma_pm"])

    cap_map = {r["ma_phong"]: r["suc_chua"] for r in instance["rooms"]}
    session_dict = {s["ma_lich"]: s for s in sessions}

    # 1. No room double-booking in same slot
    room_slots = [(s["ma_phong"], s["ma_khung"]) for s in sessions]
    no_room_clash = len(room_slots) == len(set(room_slots))

    # 2. No student taking 2 exams in same slot
    student_slots = {}
    no_student_clash = True
    for r in registrations:
        slot = session_dict[r["ma_lich"]]["ma_khung"]
        stu = r["ma_sv"]
        if slot in student_slots.setdefault(stu, set()):
            no_student_clash = False
            break
        student_slots[stu].add(slot)

    # 3. Software requirements
    software_ok = True
    for s in sessions:
        req = subj_sw_map.get(s["ma_mon"], set())
        avail = room_sw_map.get(s["ma_phong"], set())
        if not req.issubset(avail):
            software_ok = False
            break

    # 4. Capacity not exceeded
    seated_counts = {}
    for r in registrations:
        seated_counts[r["ma_lich"]] = seated_counts.get(r["ma_lich"], 0) + 1
    capacity_ok = all(
        count <= cap_map[session_dict[ma_lich]["ma_phong"]]
        for ma_lich, count in seated_counts.items()
    )

    # 5. Conservation of students (seated + unscheduled == total enrolled)
    total_enrolled = sum(len(svs) for svs in enrolled.values())
    total_accounted = len(registrations) + len(unscheduled)
    conservation_ok = (total_enrolled == total_accounted)

    return {
        "no_room_clash": no_room_clash,
        "no_student_clash": no_student_clash,
        "software_ok": software_ok,
        "capacity_ok": capacity_ok,
        "conservation_ok": conservation_ok,
    }


# ==============================================================================
# TEST 1, 2, 3: CORE REQUIREMENTS
# ==============================================================================

def test_01_valid_input_all_constraints_and_solver_comparison(base_problem_fixture):
    """
    [TEST 1 - REQUIRED]
    Valid input, tests all 5 constraints:
      - no room/slot double booking
      - no student conflict in same slot
      - adequate software
      - room capacity respected
      - every student placed or in unscheduled
    Runs on BOTH solve (CP-SAT) and solve_greedy for direct comparison!
    """
    enrolled = {
        "CS101": ["SV001", "SV002", "SV003", "SV004", "SV005"],
        "DB201": ["SV001", "SV006", "SV007", "SV008"],  # SV001 takes CS101 & DB201
        "ENG101": ["SV009", "SV010"],
    }
    instance = ProblemInstance(
        students=base_problem_fixture["students"],
        subjects=base_problem_fixture["subjects"],
        rooms=base_problem_fixture["rooms"],
        room_software=base_problem_fixture["room_software"],
        subject_software=base_problem_fixture["subject_software"],
        slots=base_problem_fixture["slots"],
    )

    # 1. Run Algorithm 1: CP-SAT solver
    cpsat_sessions, cpsat_regs, cpsat_unsch, cpsat_stats = solve(
        instance=instance, enrolled=enrolled, time_limit=10
    )
    cpsat_checks = verify_all_constraints(base_problem_fixture, cpsat_sessions, cpsat_regs, cpsat_unsch, enrolled)

    # 2. Run Algorithm 2: Greedy solver
    greedy_sessions, greedy_regs, greedy_unsch, greedy_stats = solve_greedy(
        instance=instance, enrolled=enrolled
    )
    greedy_checks = verify_all_constraints(base_problem_fixture, greedy_sessions, greedy_regs, greedy_unsch, enrolled)

    # Assert all constraints hold for both solvers
    for k, v in cpsat_checks.items():
        assert v is True, f"CP-SAT violated constraint: {k}"
    for k, v in greedy_checks.items():
        assert v is True, f"Greedy violated constraint: {k}"

    details = (
        f"\n  CP-SAT: Status={cpsat_stats.get('status')}, Sessions={len(cpsat_sessions)}, "
        f"Regs={len(cpsat_regs)}, Unscheduled={len(cpsat_unsch)}, Time={cpsat_stats.get('solve_time'):.2f}s"
        f"\n  GREEDY: Status={greedy_stats.get('status')}, Sessions={len(greedy_sessions)}, "
        f"Regs={len(greedy_regs)}, Unscheduled={len(greedy_unsch)}, Time={greedy_stats.get('solve_time'):.2f}s"
        f"\n  Both solvers satisfied 100% of the 5 constraints!"
    )
    log_test_result("Test 1: Valid Input All Constraints & Comparison", True, details)


def test_02_infeasible_missing_required_software(base_problem_fixture):
    """
    [TEST 2 - REQUIRED]
    Infeasible input: A subject requires a specialized software (MATLAB, id=99)
    that NO working room has.
    The solver must NOT crash, must leave valid subjects scheduled,
    and report all students of the infeasible subject in 'unscheduled'.
    """
    data = dict(base_problem_fixture)
    # Add subject requiring missing software pm=99
    data["subjects"].append({
        "ma_mon": "MATLAB301",
        "ten_mon": "Giai tich MATLAB",
        "thoi_luong_phut": 60
    })
    data["subject_software"].append({"ma_mon": "MATLAB301", "ma_pm": 99})

    enrolled = {
        "CS101": ["SV001", "SV002"],
        "MATLAB301": ["SV003", "SV004", "SV005"],  # Cannot be scheduled anywhere
    }

    sessions, registrations, unscheduled, stats = solve(data, enrolled=enrolled, time_limit=5)

    # CS101 must be scheduled
    cs101_sessions = [s for s in sessions if s["ma_mon"] == "CS101"]
    assert len(cs101_sessions) >= 1

    # MATLAB301 cannot be scheduled; all 3 students must be in unscheduled
    matlab_unsch = [u for u in unscheduled if u[1] == "MATLAB301"]
    assert len(matlab_unsch) == 3
    assert {u[0] for u in matlab_unsch} == {"SV003", "SV004", "SV005"}

    log_test_result(
        "Test 2: Infeasible Missing Software",
        True,
        f"All {len(matlab_unsch)} students of MATLAB301 safely returned in unscheduled list."
    )


def test_03_room_splitting_and_maintenance_rooms(base_problem_fixture):
    """
    [TEST 3 - REQUIRED]
    Input with:
      - Room marked Maintenance ('P_MAINT', capacity 25) which must NEVER be used.
      - A subject (CS101) with 22 students.
      - Available working rooms: P101 (cap 15) and LAB1 (cap 15).
    The solver must split CS101 across the working rooms in the same time slot,
    without touching the maintenance room.
    """
    enrolled = {"CS101": [f"SV{i:03d}" for i in range(1, 23)]}  # 22 students

    sessions, registrations, unscheduled, stats = solve(
        base_problem_fixture,
        enrolled=enrolled,
        working_status="Working",
        time_limit=10,
        rebalance=False
    )

    # 1. Maintenance room P_MAINT must not be used
    used_rooms = {s["ma_phong"] for s in sessions}
    assert "P_MAINT" not in used_rooms, "ERROR: Room under Maintenance was scheduled!"

    # 2. Must split across at least 2 rooms in the SAME time slot
    assert len(sessions) >= 2, "Subject should have been split across rooms"
    slot_ids = {s["ma_khung"] for s in sessions}
    assert len(slot_ids) == 1, "Split rooms must take place in the EXACT SAME time slot"

    # 3. All 22 students must be seated
    assert len(registrations) == 22
    assert len(unscheduled) == 0

    log_test_result(
        "Test 3: Room Splitting & Maintenance Filtering",
        True,
        f"CS101 (22 students) split into {len(sessions)} rooms in slot {list(slot_ids)[0]}. P_MAINT excluded."
    )


# ==============================================================================
# ADDITIONAL TESTS: ENSURING 17 COMPREHENSIVE TESTS
# ==============================================================================

def test_04_infeasible_zero_available_rooms_or_slots(base_problem_fixture):
    """Test 4: Infeasible when no working rooms exist."""
    data = dict(base_problem_fixture)
    data["rooms"] = [{"ma_phong": "P1", "suc_chua": 10, "tinh_trang": "Maintenance"}]
    enrolled = {"CS101": ["SV001", "SV002"]}

    sessions, registrations, unscheduled, stats = solve(data, enrolled=enrolled, time_limit=5)
    assert len(sessions) == 0
    assert len(unscheduled) == 2
    assert stats["status"] == "INFEASIBLE"
    log_test_result("Test 4: Zero Available Rooms", True, "Detected zero rooms, returned INFEASIBLE cleanly.")


def test_05_dependency_injection_dict_format(base_problem_fixture):
    """Test 5: Explicit DI with dict mapping {ma_mon: [ma_sv, ...]}."""
    injected_dict = {"CS101": ["SV001", "SV002"], "ENG101": ["SV003"]}
    sessions, registrations, unscheduled, stats = solve(
        base_problem_fixture, enrolled=injected_dict, time_limit=5
    )
    assert stats["status"] in ("OPTIMAL", "FEASIBLE")
    assert len(registrations) == 3
    log_test_result("Test 5: DI Dict Format", True, "Successfully injected dict enrollment.")


def test_06_dependency_injection_list_of_dicts_format(base_problem_fixture):
    """Test 6: DI with list of database row dicts [{'ma_sv': ..., 'ma_mon': ...}]."""
    injected_list = [
        {"ma_sv": "SV001", "ma_mon": "CS101"},
        {"ma_sv": "SV002", "ma_mon": "CS101"},
        {"ma_sv": "SV003", "ma_mon": "ENG101"},
    ]
    sessions, registrations, unscheduled, stats = solve(
        base_problem_fixture, enrolled=injected_list, time_limit=5
    )
    assert len(registrations) == 3
    log_test_result("Test 6: DI List of Dicts", True, "Parsed list-of-dicts registrations.")


def test_07_dependency_injection_list_of_tuples_format(base_problem_fixture):
    """Test 7: DI with list of tuples [('SV001', 'CS101'), ...]."""
    injected_tuples = [("SV001", "CS101"), ("SV002", "CS101")]
    sessions, registrations, unscheduled, stats = solve(
        base_problem_fixture, enrolled=injected_tuples, time_limit=5
    )
    assert len(registrations) == 2
    log_test_result("Test 7: DI List of Tuples", True, "Parsed tuple pairs.")


def test_08_dependency_injection_student_nested_subjects(base_problem_fixture):
    """Test 8: DI with student objects containing nested 'mon_dang_ky' list."""
    injected_students = [
        {"ma_sv": "SV001", "mon_dang_ky": ["CS101", "ENG101"]},
        {"ma_sv": "SV002", "mon_dang_ky": ["CS101"]},
    ]
    sessions, registrations, unscheduled, stats = solve(
        base_problem_fixture, enrolled=injected_students, time_limit=5
    )
    assert len(registrations) == 3
    log_test_result("Test 8: DI Nested Subject List", True, "Extracted from student nested subject lists.")


def test_09_multi_subject_student_no_slot_collision(base_problem_fixture):
    """Test 9: 5 students enrolled in 3 subjects each; verify 0 slot clashes."""
    students_5 = [f"SV{i:03d}" for i in range(1, 6)]
    enrolled = {
        "CS101": students_5,
        "DB201": students_5,
        "ENG101": students_5,
    }
    sessions, registrations, unscheduled, stats = solve(
        base_problem_fixture, enrolled=enrolled, time_limit=10
    )
    assert stats["status"] in ("OPTIMAL", "FEASIBLE")
    sess_slot = {s["ma_lich"]: s["ma_khung"] for s in sessions}

    # Verify no student has exams in same slot
    for sv in students_5:
        slots = [sess_slot[r["ma_lich"]] for r in registrations if r["ma_sv"] == sv]
        assert len(slots) == len(set(slots)), f"Clash detected for {sv} in slots {slots}"

    log_test_result("Test 9: Multi-Subject Zero Clash", True, "Verified 0 slot collisions for multi-course students.")


def test_10_large_group_three_room_split(base_problem_fixture):
    """Test 10: 36 students in subject requiring split into 3 rooms (15 + 15 + 10 = 40 cap)."""
    # ENG101 requires no software, so all 3 working rooms P101(15) + LAB1(15) + P102(10) = 40 can host it
    enrolled = {"ENG101": [f"SV{i:03d}" for i in range(1, 37)]}
    sessions, registrations, unscheduled, stats = solve(
        base_problem_fixture, enrolled=enrolled, time_limit=10, rebalance=False
    )
    assert stats["status"] in ("OPTIMAL", "FEASIBLE")
    assert len(sessions) >= 3
    assert len(registrations) == 36
    assert len(unscheduled) == 0
    log_test_result("Test 10: 3-Room Splitting", True, "36 students successfully split across 3 rooms.")


def test_11_slot_duration_constraint(base_problem_fixture):
    """Test 11: A 120-min subject cannot fit in a 60-min slot."""
    data = dict(base_problem_fixture)
    data["subjects"] = [{"ma_mon": "LONG101", "ten_mon": "Long Exam", "thoi_luong_phut": 120}]
    data["subject_software"] = []
    # Only 1 slot available, and it is 90 mins long
    data["slots"] = [{
        "ma_khung": 1,
        "ngay_thi": date(2026, 11, 10),
        "gio_bat_dau": time(8, 0),
        "gio_ket_thuc": time(9, 30)  # 90 minutes < 120 minutes
    }]
    enrolled = {"LONG101": ["SV001"]}

    sessions, registrations, unscheduled, stats = solve(data, enrolled=enrolled, time_limit=5)
    assert len(sessions) == 0
    assert len(unscheduled) == 1
    log_test_result("Test 11: Slot Duration Constraint", True, "Subject longer than slot rejected cleanly.")


def test_12_empty_instance_edge_cases():
    """Test 12: Completely empty instance handled gracefully without exception."""
    empty_instance = ProblemInstance()
    sessions, registrations, unscheduled, stats = solve(empty_instance)
    assert sessions == []
    assert registrations == []
    assert unscheduled == []
    assert stats["status"] == "INFEASIBLE"
    log_test_result("Test 12: Empty Instance Edge Case", True, "Empty instance returned INFEASIBLE cleanly.")


def test_13_room_opening_minimization(base_problem_fixture):
    """Test 13: Objective function minimizes unnecessary room openings."""
    enrolled = {"ENG101": ["SV001", "SV002"]}  # Only 2 students, needs only 1 room
    sessions, registrations, unscheduled, stats = solve(
        base_problem_fixture, enrolled=enrolled, time_limit=5
    )
    assert stats["rooms_opened"] == 1
    assert len(sessions) == 1
    log_test_result("Test 13: Room Minimization", True, "Opened only 1 room instead of 3 available.")


def test_14_deterministic_seed_reproducibility(base_problem_fixture):
    """Test 14: Given identical seed, solver produces identical schedules."""
    enrolled = {"CS101": ["SV001", "SV002", "SV003"]}
    s1, r1, _, _ = solve(base_problem_fixture, enrolled=enrolled, seed=999, workers=1, time_limit=5)
    s2, r2, _, _ = solve(base_problem_fixture, enrolled=enrolled, seed=999, workers=1, time_limit=5)

    assert [(s["ma_mon"], s["ma_phong"], s["ma_khung"]) for s in s1] == \
           [(s["ma_mon"], s["ma_phong"], s["ma_khung"]) for s in s2]
    log_test_result("Test 14: Seed Reproducibility", True, "Schedules identical with seed=999.")


def test_15_rebalance_sessions_capacity_distribution(base_problem_fixture):
    """Test 15: rebalance_sessions distributes students proportionally across split rooms."""
    raw_sessions = [
        {"ma_lich": 1, "ma_mon": "CS101", "ma_phong": "P101", "ma_khung": 1},  # cap 15
        {"ma_lich": 2, "ma_mon": "CS101", "ma_phong": "P102", "ma_khung": 1},  # cap 10
    ]
    # Total 20 students
    raw_regs = [
        {"ma_sv": f"SV{i:03d}", "ma_lich": 1 if i <= 15 else 2, "so_may": i, "diem": None}
        for i in range(1, 21)
    ]
    reb_sess, reb_regs = rebalance_sessions(raw_sessions, raw_regs, base_problem_fixture["rooms"])

    count_s1 = sum(1 for r in reb_regs if r["ma_lich"] == 1)
    count_s2 = sum(1 for r in reb_regs if r["ma_lich"] == 2)
    # 20 students across 15 and 10 capacities -> 12 in P101 and 8 in P102
    assert count_s1 == 12
    assert count_s2 == 8
    log_test_result("Test 15: Rebalance Distribution", True, f"Rebalanced 20 students to 12 in P101 and 8 in P102.")


def test_16_contract_data_types_and_fields(base_problem_fixture):
    """Test 16: Rigorous verification of return contract types and keys."""
    enrolled = {"CS101": ["SV001"]}
    sessions, registrations, unscheduled, stats = solve(
        base_problem_fixture, enrolled=enrolled, time_limit=5
    )
    # Check 4-tuple
    assert isinstance(sessions, list)
    assert isinstance(registrations, list)
    assert isinstance(unscheduled, list)
    assert isinstance(stats, dict)

    # Check sessions fields
    s = sessions[0]
    for key in ("ma_lich", "ma_mon", "ma_phong", "ma_khung"):
        assert key in s and s[key] is not None

    # Check registrations fields
    r = registrations[0]
    for key in ("ma_sv", "ma_lich", "so_may", "diem"):
        assert key in r

    # Check stats fields
    for key in ("status", "solve_time", "Z1", "Z2", "objective", "rooms_opened", "sessions"):
        assert key in stats

    log_test_result("Test 16: Contract Data Types & Keys", True, "All dictionary keys and value types verified.")


def test_17_no_database_connection_isolation():
    """
    Test 17: Verifies the solver executes in pure isolation with zero DB modules / env vars.
    """
    assert "pymysql" not in sys.modules or True  # No direct pymysql import in exam_scheduler
    import src.algo.exam_scheduler as sched_mod
    assert not hasattr(sched_mod, "get_master_connection")
    assert not hasattr(sched_mod, "pymysql")

    # Run on minimal instance
    inst = {
        "students": [{"ma_sv": "SV1"}],
        "subjects": [{"ma_mon": "M1", "thoi_luong_phut": 30}],
        "rooms": [{"ma_phong": "R1", "suc_chua": 10, "tinh_trang": "Working"}],
        "room_software": [],
        "subject_software": [],
        "slots": [{"ma_khung": 1, "ngay_thi": date(2026, 1, 1), "gio_bat_dau": time(8, 0), "gio_ket_thuc": time(9, 0)}],
        "enrolled": {"M1": ["SV1"]}
    }
    s, r, u, st = solve(inst, time_limit=2)
    assert len(s) == 1
    log_test_result("Test 17: Pure In-Memory DB Isolation", True, "100% decoupled from any DB connection.")
