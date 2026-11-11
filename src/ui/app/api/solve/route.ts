import { spawn } from "node:child_process";
import path from "node:path";
import { NextResponse } from "next/server";
import { fetchDataset } from "@/lib/repository";
import type { SolverParams } from "@/lib/types";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const PROJECT_ROOT = path.resolve(process.cwd(), "..", "..");
const CLI = path.join(PROJECT_ROOT, "src", "algo", "solve_cli.py");

/** Python có ortools: ưu tiên biến môi trường, rồi venv của src/ui_streamlit, rồi python hệ thống. */
function pythonCandidates(): string[] {
  const out: string[] = [];
  if (process.env.EXAM_SCHEDULER_PYTHON) out.push(process.env.EXAM_SCHEDULER_PYTHON);
  out.push(path.join(PROJECT_ROOT, "src", "ui_streamlit", ".venv", "Scripts", "python.exe"));
  out.push(path.join(PROJECT_ROOT, "src", "ui_streamlit", ".venv", "bin", "python"));
  out.push("python");
  return out;
}

function runSolver(python: string, payload: string): Promise<{ code: number; stdout: string; stderr: string }> {
  return new Promise((resolve, reject) => {
    const child = spawn(python, [CLI], { cwd: PROJECT_ROOT, windowsHide: true });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (d) => (stdout += d.toString()));
    child.stderr.on("data", (d) => (stderr += d.toString()));
    child.on("error", reject);
    child.on("close", (code) => resolve({ code: code ?? -1, stdout, stderr }));
    child.stdin.write(payload);
    child.stdin.end();
  });
}

export async function POST(request: Request) {
  let params: SolverParams;
  try {
    params = (await request.json()) as SolverParams;
  } catch {
    return NextResponse.json({ error: "Tham số gửi lên không phải JSON hợp lệ." }, { status: 400 });
  }

  // Đầu vào lấy từ MySQL, không còn dùng hằng số trong bundle.
  let dataset;
  try {
    dataset = await fetchDataset();
  } catch (err) {
    return NextResponse.json(
      {
        error: "Không đọc được dữ liệu đầu vào từ MySQL.",
        detail: (err as Error).message,
      },
      { status: 503 },
    );
  }

  if (!dataset.subjects.length || !dataset.rooms.length || !dataset.slots.length) {
    return NextResponse.json(
      {
        error:
          "Dữ liệu trong DB chưa đủ để xếp lịch (cần học phần, phòng máy và khung giờ). " +
          "Chạy scripts/generate_data.py để sinh dữ liệu.",
      },
      { status: 409 },
    );
  }

  const payload = JSON.stringify({
    subjects: dataset.subjects,
    rooms: dataset.rooms,
    slots: dataset.slots,
    students: dataset.students.map((s) => ({ ma_sv: s.maSv })),
    enrollment: dataset.enrollment,
    params,
    randomScores: true,
  });

  const errors: string[] = [];
  for (const python of pythonCandidates()) {
    try {
      const result = await runSolver(python, payload);
      if (result.code === 0 && result.stdout.trim()) {
        return NextResponse.json({ ...JSON.parse(result.stdout), python });
      }
      errors.push(`${python}: exit ${result.code} ${result.stderr.trim().slice(0, 400)}`);
    } catch (err) {
      errors.push(`${python}: ${(err as Error).message}`);
    }
  }

  return NextResponse.json(
    {
      error:
        "Không chạy được bộ giải CP-SAT. Cần Python có gói ortools. " +
        "Cài bằng: src/ui_streamlit/.venv/Scripts/python.exe -m pip install ortools, " +
        "hoặc đặt biến môi trường EXAM_SCHEDULER_PYTHON trỏ tới python có ortools.",
      detail: errors,
    },
    { status: 503 },
  );
}
