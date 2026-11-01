"""
CP-SAT exam scheduler - Decoupled from database (Pure Python / OR-Tools).

Model (see dac_ta_toan_hoc): x[c,r,t], y[c,t], w[r], p[g,d]
- Zero database dependencies (Pure in-memory computation, Dependency Injection).
- Input: ProblemInstance (or dict) containing students, subjects, rooms, software, and slots.
- Dependency Injection: student enrollment data can be directly passed from caller.
- Contract Output: (sessions, registrations, unscheduled, stats).
"""
import random
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

# pyrefly: ignore[missing-import]
from ortools.sat.python import cp_model


@dataclass
class ProblemInstance:
    """
    In-memory representation of an exam scheduling problem instance.
    Decoupled from database storage (suitable for Dependency Injection).
    """
    students: List[Dict[str, Any]] = field(default_factory=list)
    subjects: List[Dict[str, Any]] = field(default_factory=list)
    rooms: List[Dict[str, Any]] = field(default_factory=list)
    room_software: List[Dict[str, Any]] = field(default_factory=list)
    subject_software: List[Dict[str, Any]] = field(default_factory=list)
    slots: List[Dict[str, Any]] = field(default_factory=list)
    enrolled: Optional[Union[Dict[str, List[str]], List[Any]]] = None


def _minutes(t):
    return t.hour * 60 + t.minute  # works for datetime.time


def _timedelta_minutes(t):
    # PyMySQL returns TIME columns as timedelta; generator uses datetime.time
    return int(t.total_seconds() // 60) if hasattr(t, "total_seconds") else _minutes(t)


def _extract_field(instance: Any, field_name: str, default: Any = None) -> Any:
    if instance is None:
        return default
    if isinstance(instance, dict):
        return instance.get(field_name, default)
    return getattr(instance, field_name, default)


def build_enrollment(students: List[Dict[str, Any]],
                     subjects: List[Dict[str, Any]],
                     min_subjects: int = 3,
                     max_subjects: int = 5) -> Dict[str, List[str]]:
    """
    Generates random enrollment for testing / synthesis.
    """
    codes = [s["ma_mon"] for s in subjects]
    enrolled = {c: [] for c in codes}
    for stu in students:
        k = min(random.randint(min_subjects, max_subjects), len(codes))
        for c in random.sample(codes, k):
            enrolled[c].append(stu["ma_sv"])
    return enrolled


def normalize_enrollment(enrolled: Optional[Union[Dict[str, List[str]], List[Any]]],
                         students: Optional[List[Dict[str, Any]]] = None,
                         subjects: Optional[List[Dict[str, Any]]] = None,
                         min_subjects: int = 3,
                         max_subjects: int = 5) -> Dict[str, List[str]]:
    """
    Normalizes student enrollment from various input formats into Dict[ma_mon -> list of ma_sv].
    Supports:
      1. Dict[str, List[str]]: {ma_mon: [ma_sv, ...]}
      2. List[Dict]: [{'ma_sv': ..., 'ma_mon': ...}, ...] or [{'ma_sv': ..., 'mon_dang_ky': [...]}, ...]
      3. List[Tuple]: [(ma_sv, ma_mon), ...]
      4. None: generated on-the-fly via build_enrollment if students and subjects are available.
    """
    if enrolled is None:
        if students is not None and subjects is not None:
            return build_enrollment(students, subjects, min_subjects, max_subjects)
        return {}

    if isinstance(enrolled, dict):
        return {str(c): list(sv_list) for c, sv_list in enrolled.items()}

    res = defaultdict(list)
    if isinstance(enrolled, (list, tuple)):
        for item in enrolled:
            if isinstance(item, dict):
                if "ma_mon" in item and "ma_sv" in item:
                    res[str(item["ma_mon"])].append(str(item["ma_sv"]))
                elif "ma_sv" in item:
                    ma_sv = str(item["ma_sv"])
                    sub_list = item.get("mon_dang_ky", item.get("mon_hoc", item.get("subjects", [])))
                    for sub in sub_list:
                        res[str(sub)].append(ma_sv)
            elif isinstance(item, (list, tuple)) and len(item) == 2:
                # (ma_sv, ma_mon)
                res[str(item[1])].append(str(item[0]))
    return dict(res)


def rebalance_sessions(sessions: List[Dict[str, Any]],
                       registrations: List[Dict[str, Any]],
                       rooms: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Rebalances student distribution across rooms when a subject is split in the same slot.
    Returns renumbered (sessions, registrations).
    """
    cap = {r["ma_phong"]: r["suc_chua"] for r in rooms}
    regs_of = defaultdict(list)
    for r in registrations:
        regs_of[r["ma_lich"]].append(r)
    groups = defaultdict(list)
    for s in sessions:
        groups[(s["ma_mon"], s["ma_khung"])].append(s)

    new_sessions, new_regs = [], []
    for key in sorted(groups, key=lambda k: min(x["ma_lich"] for x in groups[k])):
        group = sorted(groups[key], key=lambda x: (-cap.get(x["ma_phong"], 0), x["ma_lich"]))
        students = [r for s in group for r in regs_of[s["ma_lich"]]]
        caps = [cap.get(s["ma_phong"], 0) for s in group]
        n, total = len(students), sum(caps)
        if total == 0:
            continue
        quotas = [n * c // total for c in caps]
        for i in sorted(range(len(caps)), key=lambda i: -(caps[i] - quotas[i]))[:n - sum(quotas)]:
            quotas[i] += 1
        pos = 0
        for s, q in zip(group, quotas):
            if q == 0:
                continue
            ma_lich = len(new_sessions) + 1
            new_sessions.append({**s, "ma_lich": ma_lich})
            for seat, r in enumerate(students[pos:pos + q], start=1):
                new_regs.append({**r, "ma_lich": ma_lich, "so_may": seat})
            pos += q
    return new_sessions, new_regs


def solve(instance: Union[ProblemInstance, Dict[str, Any]],
          enrolled: Optional[Union[Dict[str, List[str]], List[Any]]] = None,
          min_subjects: int = 3,
          max_subjects: int = 5,
          alpha: int = 1,
          beta: int = 3,
          gamma: int = 1,
          skip_penalty: int = 1000,
          time_limit: int = 30,
          seed: int = 42,
          workers: int = 8,
          working_status: str = "Working",
          random_scores: bool = True,
          rebalance: bool = True) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Tuple[str, str]], Dict[str, Any]]:
    """
    Main entry point: Solves the exam scheduling problem from an in-memory ProblemInstance.
    Zero direct calls to Database (Pure Dependency Injection).

    Parameters:
      instance: ProblemInstance object or dict containing:
        - students: list[dict]
        - subjects: list[dict]
        - rooms: list[dict]
        - room_software: list[dict]
        - subject_software: list[dict]
        - slots: list[dict]
        - enrolled (optional): dict or list of student registrations
      enrolled (optional): student enrollment passed via DI, overrides instance.enrolled
      alpha: weight for room vacancy / idle minimization
      beta: weight for student exam pressure minimization (consecutive exams per day)
      gamma: penalty weight for splitting subjects across multiple rooms
      skip_penalty: penalty for leaving a subject unscheduled
      time_limit: maximum solver execution time in seconds
      seed: random seed for reproducibility
      workers: number of CP-SAT search threads
      working_status: room status string to filter available rooms (default 'Working')
      random_scores: whether to fill dummy score values for registrations
      rebalance: whether to balance students across rooms when split

    Returns:
      (sessions, registrations, unscheduled, stats)
      - sessions: list[dict] with {'ma_lich', 'ma_mon', 'ma_phong', 'ma_khung'}
      - registrations: list[dict] with {'ma_sv', 'ma_lich', 'so_may', 'diem'}
      - unscheduled: list of (ma_sv, ma_mon) tuples for unscheduled enrollments
      - stats: dict of solver metrics (status, solve_time, Z1, Z2, objective, etc.)
    """
    students = _extract_field(instance, "students", [])
    subjects = _extract_field(instance, "subjects", [])
    rooms = _extract_field(instance, "rooms", [])
    room_software = _extract_field(instance, "room_software", [])
    subject_software = _extract_field(instance, "subject_software", [])
    slots = _extract_field(instance, "slots", [])

    if enrolled is None:
        enrolled = _extract_field(instance, "enrolled", None)

    enrolled = normalize_enrollment(enrolled, students=students, subjects=subjects,
                                    min_subjects=min_subjects, max_subjects=max_subjects)

    C = [s["ma_mon"] for s in subjects]
    for c in C:
        if c not in enrolled:
            enrolled[c] = []

    # Fast validation for empty data
    if not C or not slots or not rooms:
        unscheduled_all = [(sv, c) for c in C for sv in enrolled.get(c, [])]
        return [], [], unscheduled_all, {
            "status": "INFEASIBLE",
            "solve_time": 0.0,
            "reason": "Missing subjects, rooms or slots in instance"
        }

    n = {c: len(enrolled[c]) for c in C}
    duration = {s["ma_mon"]: s["thoi_luong_phut"] for s in subjects}

    active = [r for r in rooms if r.get("tinh_trang", "Working") == working_status]
    if not active:
        unscheduled_all = [(sv, c) for c in C for sv in enrolled.get(c, [])]
        return [], [], unscheduled_all, {
            "status": "INFEASIBLE",
            "solve_time": 0.0,
            "reason": "No active rooms available"
        }
    R = [r["ma_phong"] for r in active]
    K = {r["ma_phong"]: r["suc_chua"] for r in active}

    T = [sl["ma_khung"] for sl in slots]
    slot_day = {sl["ma_khung"]: sl["ngay_thi"] for sl in slots}
    slot_len = {sl["ma_khung"]: _timedelta_minutes(sl["gio_ket_thuc"]) - _timedelta_minutes(sl["gio_bat_dau"])
                for sl in slots}
    days = sorted(set(slot_day.values()))

    sw_room = defaultdict(set)
    for link in room_software:
        sw_room[link["ma_phong"]].add(link["ma_pm"])
    sw_need = defaultdict(set)
    for link in subject_software:
        sw_need[link["ma_mon"]].add(link["ma_pm"])

    # f[c,r]: room has all software the subject needs
    f = {(c, r): sw_need[c] <= sw_room[r] for c in C for r in R}

    # student groups = distinct sets of enrolled subjects (weighted by how many students share them)
    subj_of = defaultdict(set)
    for c in C:
        for sv in enrolled[c]:
            subj_of[sv].add(c)
    group_count = defaultdict(int)
    for sv, cs in subj_of.items():
        group_count[frozenset(cs)] += 1
    groups = list(group_count)

    model = cp_model.CpModel()

    # variables (only for valid pairs / slots long enough for the subject)
    ok_slot = {(c, t): slot_len[t] >= duration[c] for c in C for t in T}
    y = {(c, t): model.NewBoolVar(f"y_{c}_{t}") for c in C for t in T if ok_slot[c, t]}
    x = {(c, r, t): model.NewBoolVar(f"x_{c}_{r}_{t}")
         for c in C for r in R for t in T if f[c, r] and ok_slot[c, t]}
    w = {r: model.NewBoolVar(f"w_{r}") for r in R}
    skip = {c: model.NewBoolVar(f"skip_{c}") for c in C}
    p = {(gi, d): model.NewIntVar(0, len(C), f"p_{gi}_{d}")
         for gi in range(len(groups)) for d in days}

    def X(c, r, t):
        return x.get((c, r, t), 0)

    def Y(c, t):
        return y.get((c, t), 0)

    for c in C:
        # C1: scheduled exactly once (or skipped)
        model.Add(sum(Y(c, t) for t in T) + skip[c] == 1)

    for c in C:
        for t in T:
            if (c, t) in y:
                # C5: subject at slot t <=> at least one room used at t
                rooms_used = sum(X(c, r, t) for r in R)
                model.Add(rooms_used >= y[c, t])
                for r in R:
                    if (c, r, t) in x:
                        model.Add(x[c, r, t] <= y[c, t])
                # C3 (split): total seats cover all students
                model.Add(sum(K[r] * X(c, r, t) for r in R) >= n[c] * y[c, t])

    # C2: one session per room and slot
    for r in R:
        for t in T:
            model.Add(sum(X(c, r, t) for c in C) <= 1)

    # C4: a student group never has two exams in the same slot
    for cs in groups:
        for t in T:
            model.Add(sum(Y(c, t) for c in cs) <= 1)

    # C7: room opened
    for (c, r, t), var in x.items():
        model.Add(var <= w[r])

    # C8: pressure (k exams in one day -> k-1)
    for gi, cs in enumerate(groups):
        for d in days:
            model.Add(p[gi, d] >= sum(Y(c, t) for c in cs for t in T if slot_day[t] == d) - 1)

    # Objective
    open_cost = alpha * len(T) * sum(w.values())
    split_cost = (gamma - alpha) * sum(x.values()) if x else 0
    pressure = sum(group_count[cs] * p[gi, d] for gi, cs in enumerate(groups) for d in days)
    model.Minimize(open_cost + split_cost + beta * pressure
                   + skip_penalty * sum(skip[c] * n[c] for c in C))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.random_seed = seed
    solver.parameters.num_workers = workers
    status = solver.Solve(model)
    status_name = solver.StatusName(status)

    sessions, registrations, unscheduled = [], [], []
    stats = {"status": status_name, "solve_time": solver.WallTime()}
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for c in C:
            unscheduled.extend((sv, c) for sv in enrolled[c])
        return sessions, registrations, unscheduled, stats

    # decode: seat students room by room
    chosen = defaultdict(list)  # (c, t) -> [rooms]
    for (c, r, t), var in x.items():
        if solver.Value(var):
            chosen[c, t].append(r)

    ma_lich = 0
    for (c, t), room_list in sorted(chosen.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        pending = enrolled[c][:]
        random.shuffle(pending)
        for r in sorted(room_list, key=lambda rr: -K[rr]):
            group = pending[:K[r]]
            pending = pending[K[r]:]
            if not group:
                continue
            ma_lich += 1
            sessions.append({"ma_lich": ma_lich, "ma_mon": c, "ma_phong": r, "ma_khung": t})
            for seat, sv in enumerate(group, start=1):
                score = round(min(10, max(0, random.gauss(6.8, 1.6))), 2) if random_scores else None
                registrations.append({"ma_sv": sv, "ma_lich": ma_lich, "so_may": seat, "diem": score})

    for c in C:
        if solver.Value(skip[c]):
            unscheduled.extend((sv, c) for sv in enrolled[c])

    if rebalance and sessions:
        sessions, registrations = rebalance_sessions(sessions, registrations, active)

    z1 = len(T) * sum(solver.Value(v) for v in w.values()) - len(sessions)
    z2 = sum(group_count[cs] * solver.Value(p[gi, d]) for gi, cs in enumerate(groups) for d in days)
    stats.update(Z1=z1, Z2=z2, objective=solver.ObjectiveValue(), best_bound=solver.BestObjectiveBound(),
                 rooms_opened=sum(solver.Value(v) for v in w.values()), sessions=len(sessions),
                 unscheduled_subjects=sum(solver.Value(v) for v in skip.values()))
    return sessions, registrations, unscheduled, stats


def schedule_cp_sat(students: List[Dict[str, Any]],
                    subjects: List[Dict[str, Any]],
                    rooms: List[Dict[str, Any]],
                    room_software: List[Dict[str, Any]],
                    subject_software: List[Dict[str, Any]],
                    slots: List[Dict[str, Any]],
                    enrolled: Optional[Union[Dict[str, List[str]], List[Any]]] = None,
                    min_subjects: int = 3,
                    max_subjects: int = 5,
                    alpha: int = 1,
                    beta: int = 3,
                    gamma: int = 1,
                    skip_penalty: int = 1000,
                    time_limit: int = 30,
                    seed: int = 42,
                    workers: int = 8,
                    working_status: str = "Working",
                    random_scores: bool = True) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Tuple[str, str]], Dict[str, Any]]:
    """
    Backwards-compatible API that forwards to solve().
    """
    instance = ProblemInstance(
        students=students,
        subjects=subjects,
        rooms=rooms,
        room_software=room_software,
        subject_software=subject_software,
        slots=slots,
        enrolled=enrolled
    )
    return solve(
        instance=instance,
        enrolled=enrolled,
        min_subjects=min_subjects,
        max_subjects=max_subjects,
        alpha=alpha,
        beta=beta,
        gamma=gamma,
        skip_penalty=skip_penalty,
        time_limit=time_limit,
        seed=seed,
        workers=workers,
        working_status=working_status,
        random_scores=random_scores,
        rebalance=False  # Keep raw output as callers like generate_data apply rebalance if needed
    )


def solve_greedy(instance: Union[ProblemInstance, Dict[str, Any]],
                 enrolled: Optional[Union[Dict[str, List[str]], List[Any]]] = None,
                 min_subjects: int = 3,
                 max_subjects: int = 5,
                 working_status: str = "Working",
                 random_scores: bool = True) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Tuple[str, str]], Dict[str, Any]]:
    """
    Greedy heuristic solver (pure in-memory).
    Follows identical contract and constraint specification as solve().
    """
    students = _extract_field(instance, "students", [])
    subjects = _extract_field(instance, "subjects", [])
    rooms = _extract_field(instance, "rooms", [])
    room_software = _extract_field(instance, "room_software", [])
    subject_software = _extract_field(instance, "subject_software", [])
    slots = _extract_field(instance, "slots", [])

    if enrolled is None:
        enrolled = _extract_field(instance, "enrolled", None)

    enrolled = normalize_enrollment(enrolled, students=students, subjects=subjects,
                                    min_subjects=min_subjects, max_subjects=max_subjects)

    sw_by_room = defaultdict(set)
    for link in room_software:
        sw_by_room[link["ma_phong"]].add(link["ma_pm"])
    req_by_subject = defaultdict(set)
    for link in subject_software:
        req_by_subject[link["ma_mon"]].add(link["ma_pm"])

    active_rooms = [r for r in rooms if r.get("tinh_trang", "Working") == working_status]
    subject_codes = [s["ma_mon"] for s in subjects]
    duration = {s["ma_mon"]: s.get("thoi_luong_phut", 60) for s in subjects}
    slot_len = {sl["ma_khung"]: _timedelta_minutes(sl["gio_ket_thuc"]) - _timedelta_minutes(sl["gio_bat_dau"])
                for sl in slots}

    sessions, registrations, unscheduled = [], [], []
    busy_rooms = set()
    busy_students = defaultdict(set)

    for code in subject_codes:
        pending = list(enrolled.get(code, []))
        dur = duration.get(code, 60)

        while pending:
            candidates = [
                (r, sl) for r in active_rooms
                if req_by_subject[code] <= sw_by_room[r["ma_phong"]]
                for sl in slots
                if (r["ma_phong"], sl["ma_khung"]) not in busy_rooms and slot_len.get(sl["ma_khung"], 0) >= dur
            ]
            if not candidates:
                unscheduled.extend((ma_sv, code) for ma_sv in pending)
                break

            placed = False
            for room, slot in candidates:
                free = [s for s in pending if slot["ma_khung"] not in busy_students[s]]
                if not free:
                    continue
                group = free[:room["suc_chua"]]
                ma_lich = len(sessions) + 1
                sessions.append({
                    "ma_lich": ma_lich,
                    "ma_mon": code,
                    "ma_phong": room["ma_phong"],
                    "ma_khung": slot["ma_khung"]
                })
                busy_rooms.add((room["ma_phong"], slot["ma_khung"]))
                for seat, ma_sv in enumerate(group, start=1):
                    score = round(min(10, max(0, random.gauss(6.8, 1.6))), 2) if random_scores else None
                    registrations.append({
                        "ma_sv": ma_sv,
                        "ma_lich": ma_lich,
                        "so_may": seat,
                        "diem": score
                    })
                    busy_students[ma_sv].add(slot["ma_khung"])

                grouped = set(group)
                pending = [s for s in pending if s not in grouped]
                placed = True
                break

            if not placed:
                unscheduled.extend((ma_sv, code) for ma_sv in pending)
                break

    stats = {
        "status": "FEASIBLE" if sessions else "INFEASIBLE",
        "solve_time": 0.01,
        "algorithm": "greedy",
        "rooms_opened": len({s["ma_phong"] for s in sessions}),
        "sessions": len(sessions),
        "unscheduled_students": len(unscheduled)
    }
    return sessions, registrations, unscheduled, stats
