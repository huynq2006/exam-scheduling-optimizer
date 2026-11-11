"""
Cầu nối JSON cho UI web: đọc một payload từ stdin, gọi schedule_cp_sat trong
exam_scheduler.py, in kết quả ra stdout dưới dạng JSON.

Không chứa logic xếp lịch. Toàn bộ mô hình nằm ở exam_scheduler.py.
"""
import json
import sys
from datetime import time as dtime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from exam_scheduler import schedule_cp_sat  # noqa: E402


def _time(value):
    """'07:30' -> datetime.time, hoặc giữ nguyên nếu đã đúng kiểu."""
    if isinstance(value, dtime):
        return value
    hour, minute = str(value).split(":")[:2]
    return dtime(int(hour), int(minute))


def main():
    payload = json.load(sys.stdin)

    subjects = [
        {"ma_mon": s["maMon"], "thoi_luong_phut": int(s["thoiLuongPhut"])}
        for s in payload["subjects"]
    ]
    rooms = [
        {"ma_phong": r["maPhong"], "suc_chua": int(r["sucChua"]), "tinh_trang": r["tinhTrang"]}
        for r in payload["rooms"]
    ]
    room_software = [
        {"ma_phong": r["maPhong"], "ma_pm": pm}
        for r in payload["rooms"]
        for pm in r.get("phanMem", [])
    ]
    subject_software = [
        {"ma_mon": s["maMon"], "ma_pm": pm}
        for s in payload["subjects"]
        for pm in s.get("phanMem", [])
    ]
    slots = [
        {
            "ma_khung": int(t["maKhung"]),
            "ngay_thi": t["ngayThi"],
            "gio_bat_dau": _time(t["gioBd"]),
            "gio_ket_thuc": _time(t["gioKt"]),
        }
        for t in payload["slots"]
    ]

    enrolled = {}
    for row in payload["enrollment"]:
        enrolled.setdefault(row["maMon"], []).append(row["maSv"])

    params = payload.get("params", {})
    sessions, registrations, unscheduled, stats = schedule_cp_sat(
        students=payload.get("students", []),
        subjects=subjects,
        rooms=rooms,
        room_software=room_software,
        subject_software=subject_software,
        slots=slots,
        enrolled=enrolled,
        alpha=float(params.get("alpha", 1)),
        beta=float(params.get("beta", 3)),
        gamma=float(params.get("gamma", 1)),
        skip_penalty=float(params.get("skipPenalty", 1000)),
        time_limit=float(params.get("timeLimit", 20)),
        seed=int(params.get("seed", 42)),
        workers=int(params.get("workers", 8)),
        random_scores=bool(payload.get("randomScores", True)),
    )

    json.dump(
        {
            "sessions": sessions,
            "registrations": registrations,
            "unscheduled": [{"maSv": sv, "maMon": c} for sv, c in unscheduled],
            "stats": stats,
        },
        sys.stdout,
        default=str,
    )


if __name__ == "__main__":
    main()
