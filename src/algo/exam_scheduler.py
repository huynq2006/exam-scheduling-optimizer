"""
CP-SAT exam scheduler - drop-in replacement for the greedy `generated_exam_schedule`.

Model (see dac_ta_toan_hoc): x[c,r,t], y[c,t], w[r], p[g,d]
Differences from the demo xep_lich_thi.py:
  * f[c,r] is "room has every software the subject needs" (not a machine/non-machine flag)
  * a subject may be split over several rooms in the same slot (sum K_r * x >= n_c * y)
  * a student group = a distinct set of enrolled subjects (identical sets share constraints)
  * skip[c] slack makes the model always feasible; skipped subjects are reported as unscheduled

Pure Python: it does NOT touch the database. Put it in src/algo/exam_scheduler.py.
"""
import random
from collections import defaultdict

# pyrefly: ignore[missing-import]
from ortools.sat.python import cp_model


def _minutes(t):
    return t.hour * 60 + t.minute  # works for datetime.time


def _timedelta_minutes(t):
    # PyMySQL returns TIME columns as timedelta; generator uses datetime.time
    return int(t.total_seconds() // 60) if hasattr(t, "total_seconds") else _minutes(t)


def build_enrollment(students, subjects, min_subjects=3, max_subjects=5):
    """Random enrolment, same rule as the greedy generator. Replace by a DB read of dang_ky_mon."""
    codes = [s["ma_mon"] for s in subjects]
    enrolled = {c: [] for c in codes}
    for stu in students:
        k = min(random.randint(min_subjects, max_subjects), len(codes))
        for c in random.sample(codes, k):
            enrolled[c].append(stu["ma_sv"])
    return enrolled


def schedule_cp_sat(students, subjects, rooms, room_software, subject_software, slots,
                    enrolled=None, min_subjects=3, max_subjects=5,
                    alpha=1, beta=3, gamma=1, skip_penalty=1000,
                    time_limit=30, seed=42, workers=8,
                    working_status="Working", random_scores=True):
    """
    Returns (sessions, registrations, unscheduled, stats) - the first three have exactly the
    shape of the greedy scheduler, so insert_sessions / insert_registrations stay unchanged.
    """
    if enrolled is None:
        enrolled = build_enrollment(students, subjects, min_subjects, max_subjects)

    C = [s["ma_mon"] for s in subjects]
    n = {c: len(enrolled[c]) for c in C}
    duration = {s["ma_mon"]: s["thoi_luong_phut"] for s in subjects}

    active = [r for r in rooms if r["tinh_trang"] == working_status]
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

    # Objective. Z1 = |T|*sum(w) - sum(x) with splitting allowed, so sum(x) must be penalised
    # (gamma) or the solver would split subjects over more rooms just to look "less idle".
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
                continue  # room opened but not needed (cannot happen with gamma > 0, safe anyway)
            ma_lich += 1
            sessions.append({"ma_lich": ma_lich, "ma_mon": c, "ma_phong": r, "ma_khung": t})
            for seat, sv in enumerate(group, start=1):
                score = round(min(10, max(0, random.gauss(6.8, 1.6))), 2) if random_scores else None
                registrations.append({"ma_sv": sv, "ma_lich": ma_lich, "so_may": seat, "diem": score})
    for c in C:
        if solver.Value(skip[c]):
            unscheduled.extend((sv, c) for sv in enrolled[c])

    z1 = len(T) * sum(solver.Value(v) for v in w.values()) - len(sessions)
    z2 = sum(group_count[cs] * solver.Value(p[gi, d]) for gi, cs in enumerate(groups) for d in days)
    stats.update(Z1=z1, Z2=z2, objective=solver.ObjectiveValue(), best_bound=solver.BestObjectiveBound(),
                 rooms_opened=sum(solver.Value(v) for v in w.values()), sessions=len(sessions),
                 unscheduled_subjects=sum(solver.Value(v) for v in skip.values()))
    return sessions, registrations, unscheduled, stats
