import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { NextResponse } from "next/server";
import { fetchDataset } from "@/lib/repository";
import type { SolverParams } from "@/lib/types";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const PROJECT_ROOT = path.resolve(process.cwd(), "..", "..");
const CLI = path.join(PROJECT_ROOT, "src", "algo", "solve_cli.py");

/**
 * Ứng viên Python, xếp theo thứ tự ưu tiên.
 *
 * Không phải Python nào trên máy cũng cài được ortools: bản MSYS2/MinGW
 * (C:\msys64) báo tag mingw_x86_64_ucrt nên pip không có wheel nào khớp.
 * Vì vậy phải dò xem trình nào import được ortools thật, chứ không đoán
 * theo đường dẫn.
 */
function pythonCandidates(): Array<{ cmd: string; args: string[] }> {
  const out: Array<{ cmd: string; args: string[] }> = [];
  const push = (cmd: string, args: string[] = []) => {
    if (cmd && !out.some((c) => c.cmd === cmd && c.args.join(" ") === args.join(" "))) {
      out.push({ cmd, args });
    }
  };

  if (process.env.EXAM_SCHEDULER_PYTHON) push(process.env.EXAM_SCHEDULER_PYTHON);

  // Bản CPython chính thức của Windows (có wheel ortools).
  const localAppData = process.env.LOCALAPPDATA;
  if (localAppData) {
    const pyRoot = path.join(localAppData, "Programs", "Python");
    try {
      for (const dir of fs.readdirSync(pyRoot)) {
        if (!/^Python3\d+$/.test(dir)) continue;
        push(path.join(pyRoot, dir, "python.exe"));
      }
    } catch {
      /* không có thư mục này thì bỏ qua */
    }
  }

  // Trình py launcher: tự chọn bản CPython mới nhất đã cài.
  push("py", ["-3"]);

  push(path.join(PROJECT_ROOT, "src", "ui_streamlit", ".venv", "Scripts", "python.exe"));
  push(path.join(PROJECT_ROOT, "src", "ui_streamlit", ".venv", "bin", "python"));
  push("python3");
  push("python");
  return out;
}

/** Chạy một lệnh Python ngắn, trả về true nếu import được ortools. */
function hasOrtools(candidate: { cmd: string; args: string[] }): Promise<boolean> {
  return new Promise((resolve) => {
    const child = spawn(
      candidate.cmd,
      [...candidate.args, "-c", "import ortools.sat.python.cp_model"],
      { cwd: PROJECT_ROOT, windowsHide: true },
    );
    const timer = setTimeout(() => {
      child.kill();
      resolve(false);
    }, 20_000);
    child.on("error", () => {
      clearTimeout(timer);
      resolve(false);
    });
    child.on("close", (code) => {
      clearTimeout(timer);
      resolve(code === 0);
    });
  });
}

function runSolver(
  candidate: { cmd: string; args: string[] },
  payload: string,
): Promise<{ code: number; stdout: string; stderr: string }> {
  return new Promise((resolve, reject) => {
    const child = spawn(candidate.cmd, [...candidate.args, CLI], {
      cwd: PROJECT_ROOT,
      windowsHide: true,
    });
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
    students: dataset.students.map((s) => ({ ma_sv: s.maSv, lop: s.lop })),
    enrollment: dataset.enrollment,
    params,
    randomScores: true,
  });

  const errors: string[] = [];
  for (const candidate of pythonCandidates()) {
    const label = `${candidate.cmd} ${candidate.args.join(" ")}`.trim();
    if (!(await hasOrtools(candidate))) {
      errors.push(`${label}: không import được ortools`);
      continue;
    }
    try {
      const result = await runSolver(candidate, payload);
      if (result.code === 0 && result.stdout.trim()) {
        return NextResponse.json({ ...JSON.parse(result.stdout), python: label });
      }
      errors.push(`${label}: exit ${result.code} ${result.stderr.trim().slice(0, 400)}`);
    } catch (err) {
      errors.push(`${label}: ${(err as Error).message}`);
    }
  }

  return NextResponse.json(
    {
      error:
        "Không chạy được bộ giải CP-SAT: không có Python nào import được ortools. " +
        "Cài ortools cho một bản CPython chính thức của Windows " +
        "(python -m pip install ortools), hoặc đặt biến môi trường " +
        "EXAM_SCHEDULER_PYTHON trỏ tới python có ortools.",
      detail: errors,
    },
    { status: 503 },
  );
}
