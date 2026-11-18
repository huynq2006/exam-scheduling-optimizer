"""Non-interactive runner for generate_data.generate_all().

Usage:
    python scripts/run_generate.py [n_students] [n_subjects] [n_rooms] [n_days] [seed]

Keeps the interactive main() in generate_data.py untouched; this just supplies
the arguments so the dataset can be regenerated from a script or CI.
"""
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts.generate_data import generate_all  # noqa: E402
from src.backend.db_helper import get_master_connection  # noqa: E402


def main():
    argv = sys.argv[1:]
    n_students = int(argv[0]) if len(argv) > 0 else 200
    n_subjects = int(argv[1]) if len(argv) > 1 else 16
    n_rooms = int(argv[2]) if len(argv) > 2 else 8
    n_days = int(argv[3]) if len(argv) > 3 else 5
    seed = int(argv[4]) if len(argv) > 4 else 20261111

    print(f"Generating: students={n_students} subjects={n_subjects} "
          f"rooms={n_rooms} days={n_days} seed={seed}")

    connection = get_master_connection()
    try:
        summary = generate_all(
            connection,
            n_students,
            n_subjects,
            n_rooms,
            n_days,
            seed=seed,
            algorithm="auto",
            time_limit=30,
        )
    finally:
        connection.close()

    print(f"Plan ma_pa={summary['ma_pa']} published={summary['published']}")
    print(f"Solver: {summary['solver']}")
    print(f"Students={summary['students']} Subjects={summary['subjects']} "
          f"Rooms={summary['rooms']} (maintenance={summary['rooms_maintenance']})")
    print(f"Slots={summary['slots']} Sessions={summary['sessions']} "
          f"Registrations={summary['registrations']}")
    print(f"Unscheduled={summary['unscheduled']}")


if __name__ == "__main__":
    main()
