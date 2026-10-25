"""
Khung code OR-Tools (CP-SAT) cho bài toán xếp lịch thi + phòng máy.
Dữ liệu cứng (hardcoded). Ánh xạ 1-1 với file dac_ta_toan_hoc.tex.

Chạy:  pip install ortools   &&   python xep_lich_thi.py
"""
from ortools.sat.python import cp_model

# ---------------------------------------------------------------- 1. DỮ LIỆU
# Tập hợp
C = ["CS101", "CS102", "DB201", "AI301", "NET210", "SE220", "ML401", "OS230"]
R = ["P101", "P102", "LabA", "LabB"]
D = ["Mon", "Tue"]
T_PER_DAY = 2                                   # 2 ca/ngày
T = [(d, k) for d in range(len(D)) for k in range(T_PER_DAY)]  # t = (ngày, ca)
G = ["K1", "K2", "K3"]                          # nhóm sinh viên

# Tham số
n = dict(zip(C, [60, 55, 40, 35, 45, 50, 30, 38]))        # n_c  số sinh viên
m = dict(zip(C, [0, 0, 1, 1, 0, 0, 1, 0]))                # m_c  thi trên máy
s = dict(zip(C, [3, 3, 2, 2, 2, 3, 2, 2]))                # s_c  cán bộ coi thi
K = dict(zip(R, [70, 60, 45, 40]))                        # K_r  sức chứa
mu = dict(zip(R, [0, 0, 1, 1]))                           # mu_r phòng máy
S = {t: 6 for t in T}                                     # S_t  CBCT tối đa
a = {(r, t): 1 for r in R for t in T}                     # a_{r,t} rảnh
a[("LabB", (0, 0))] = 0                                   # LabB bận Mon ca 1
E = {                                                     # E_g  ca thi của nhóm g
    "K1": ["CS101", "CS102", "DB201"],
    "K2": ["DB201", "AI301", "NET210", "SE220"],
    "K3": ["AI301", "ML401", "OS230", "CS101"],
}
alpha, beta = 1, 3                                        # trọng số mục tiêu

# f_{c,r} = [n_c <= K_r] * [m_c <= mu_r]
f = {(c, r): int(n[c] <= K[r] and m[c] <= mu[r]) for c in C for r in R}

# ---------------------------------------------------------------- 2. MÔ HÌNH
model = cp_model.CpModel()

# Biến quyết định (chỉ tạo khi cặp hợp lệ để giảm kích thước)
x = {(c, r, t): model.NewBoolVar(f"x_{c}_{r}_{t[0]}_{t[1]}")
     for c in C for r in R for t in T if f[c, r] and a[r, t]}
y = {(c, t): model.NewBoolVar(f"y_{c}_{t[0]}_{t[1]}") for c in C for t in T}
w = {r: model.NewBoolVar(f"w_{r}") for r in R}
p = {(g, d): model.NewIntVar(0, len(C), f"p_{g}_{d}")
     for g in G for d in range(len(D))}

def X(c, r, t):
    """x_{c,r,t}, bằng 0 nếu cặp không hợp lệ."""
    return x.get((c, r, t), 0)

# C1 mỗi ca thi xếp đúng một lần
for c in C:
    model.Add(sum(X(c, r, t) for r in R for t in T) == 1)
# C2 mỗi phòng/khung giờ tối đa một ca
for r in R:
    for t in T:
        model.Add(sum(X(c, r, t) for c in C) <= a[r, t])
# C3 sức chứa + loại phòng: đã được áp dụng khi tạo biến x (f_{c,r}=0 -> không có biến)
# C4 không xung đột sinh viên
for g in G:
    for t in T:
        model.Add(sum(X(c, r, t) for c in E[g] for r in R) <= 1)
# C5 liên kết y với x
for c in C:
    for t in T:
        model.Add(y[c, t] == sum(X(c, r, t) for r in R))
# C6 giới hạn cán bộ coi thi
for t in T:
    model.Add(sum(s[c] * y[c, t] for c in C) <= S[t])
# C7 phòng được mở
for (c, r, t), var in x.items():
    model.Add(var <= w[r])
# C8 mức dồn ép
for g in G:
    for d in range(len(D)):
        model.Add(p[g, d] >= sum(y[c, t] for c in E[g] for t in T if t[0] == d) - 1)

# Mục tiêu: min alpha*Z1 + beta*Z2
idle = sum(a[r, t] * (w[r] - sum(X(c, r, t) for c in C)) for r in R for t in T)
pressure = sum(p.values())
model.Minimize(alpha * idle + beta * pressure)

# ---------------------------------------------------------------- 3. GIẢI
solver = cp_model.CpSolver()
solver.parameters.max_time_in_seconds = 30
status = solver.Solve(model)

print("Trạng thái:", solver.StatusName(status))
if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
    print(f"Z = {solver.ObjectiveValue():.0f}  "
          f"(Z1 phòng trống = {solver.Value(idle)}, Z2 dồn ép = {solver.Value(pressure)})")
    print("\nLịch thi:")
    rows = sorted((t, r, c) for (c, r, t), v in x.items() if solver.Value(v))
    for t, r, c in rows:
        print(f"  {D[t[0]]} ca {t[1]+1} | {r:5s} | {c:6s} "
              f"({n[c]} SV, {s[c]} CBCT{', máy' if m[c] else ''})")
    print("Phòng mở:", [r for r in R if solver.Value(w[r])])
else:
    print("Không tìm được nghiệm khả thi - kiểm tra lại dữ liệu/ràng buộc.")