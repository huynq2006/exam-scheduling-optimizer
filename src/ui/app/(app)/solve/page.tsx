"use client";

import { useState } from "react";
import Link from "next/link";
import {
  AlertCircle,
  ArrowRight,
  CalendarDays,
  DoorOpen,
  GraduationCap,
  Loader2,
  Play,
  RotateCcw,
  Users,
} from "lucide-react";
import { useApp } from "@/lib/store";
import { useDataset } from "@/lib/dataset";
import { formatDateTime } from "@/lib/utils";
import { statusOf, summarizeResult } from "@/lib/labels";
import {
  Badge,
  Button,
  Card,
  CardHeader,
  Field,
  PageHeader,
  Stat,
  inputClass,
} from "@/components/ui";

export default function SolvePage() {
  const { params, saveParams, runSolver, result, clearResult } = useApp();
  const { subjects: SUBJECTS, rooms: ROOMS, slots: SLOTS, enrollment: ENROLLMENT, loading, error: dataError, reload } = useDataset();
  const [draft, setDraft] = useState(params);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const working = ROOMS.filter((r) => r.tinhTrang === "Working");
  const examDays = new Set(SLOTS.map((s) => s.ngayThi)).size;

  function update<K extends keyof typeof draft>(key: K, value: (typeof draft)[K]) {
    setDraft((prev) => ({ ...prev, [key]: value }));
  }

  async function solve() {
    setRunning(true);
    setError(null);
    saveParams(draft);
    const outcome = await runSolver(draft);
    if (!outcome.ok) setError(outcome.message);
    setRunning(false);
  }

  const scheduledSubjects = result ? new Set(result.sessions.map((s) => s.maMon)).size : 0;

  if (loading) {
    return (
      <>
        <PageHeader eyebrow="Xếp lịch" title="Xếp lịch thi cho kỳ này" desc="Đang tải dữ liệu từ cơ sở dữ liệu…" />
        <Card>
          <p className="py-10 text-center text-[13px] text-ink-500">Đang đọc dữ liệu từ MySQL…</p>
        </Card>
      </>
    );
  }

  if (dataError) {
    return (
      <>
        <PageHeader eyebrow="Xếp lịch" title="Xếp lịch thi cho kỳ này" desc="Không đọc được dữ liệu." />
        <Card>
          <div className="py-8 text-center">
            <p className="text-[13px] font-medium text-rose-700">Không kết nối được cơ sở dữ liệu</p>
            <p className="mx-auto mt-2 max-w-lg text-[12.5px] leading-relaxed text-ink-500">{dataError}</p>
            <Button variant="secondary" size="sm" className="mt-4" onClick={reload}>
              Thử lại
            </Button>
          </div>
        </Card>
      </>
    );
  }

  return (
    <>
      <PageHeader
        eyebrow="Xếp lịch"
        title="Xếp lịch thi cho kỳ này"
        desc="Hệ thống sẽ tự sắp toàn bộ học phần vào các ngày thi và phòng máy sao cho không trùng lịch của sinh viên và không dùng sai phòng."
      />

      <div className="grid gap-4 lg:grid-cols-[1.3fr_1fr]">
        <Card>
          <CardHeader
            title="Chọn cách xếp"
            desc="Phần lớn trường hợp chỉ cần bấm nút xếp lịch. Các ô bên dưới dành cho khi cần chờ lâu hơn hoặc muốn kết quả khác đi."
          />

          <div className="mt-5 grid gap-4 sm:grid-cols-2">
            <Field
              label="Thời gian chờ tối đa"
              hint="Đơn vị: giây. Càng lâu, hệ thống càng có cơ hội tìm được lịch gọn hơn."
            >
              <input
                type="number"
                min={1}
                max={600}
                className={inputClass}
                value={draft.timeLimit}
                onChange={(e) => update("timeLimit", Number(e.target.value))}
              />
            </Field>
            <Field label="Số luồng máy tính" hint="Để mặc định nếu không rõ. Máy nhiều nhân thì tăng được.">
              <input
                type="number"
                min={1}
                max={32}
                className={inputClass}
                value={draft.workers}
                onChange={(e) => update("workers", Number(e.target.value))}
              />
            </Field>
          </div>

          <details className="mt-4 rounded-lg border border-ink-200 px-3.5 py-3">
            <summary className="cursor-pointer text-[12.5px] font-medium text-ink-700">
              Tuỳ chọn nâng cao (dành cho quản trị)
            </summary>
            <p className="mt-2 text-[11.5px] leading-relaxed text-ink-500">
              Bốn mức ưu tiên dưới đây quyết định hệ thống thích phương án nào hơn khi có nhiều cách
              xếp cùng hợp lệ. Số càng lớn thì càng tránh.
            </p>

            <div className="mt-3 grid gap-3 sm:grid-cols-2">
              <Field label="Hạn chế mở thêm phòng" hint="Cao thì dồn ca vào ít phòng, tiết kiệm điện và nhân sự.">
                <input
                  type="number"
                  step={0.5}
                  min={0}
                  className={inputClass}
                  value={draft.alpha}
                  onChange={(e) => update("alpha", Number(e.target.value))}
                />
              </Field>
              <Field label="Hạn chế dồn nhiều ca một ngày" hint="Cao thì lịch thi giãn ra cho sinh viên đỡ mệt.">
                <input
                  type="number"
                  step={0.5}
                  min={0}
                  className={inputClass}
                  value={draft.beta}
                  onChange={(e) => update("beta", Number(e.target.value))}
                />
              </Field>
              <Field
                label="Hạn chế tách môn sang nhiều phòng"
                hint="Cao thì mỗi môn gọn trong một phòng, nhưng dễ thiếu chỗ."
              >
                <input
                  type="number"
                  step={0.5}
                  min={0}
                  className={inputClass}
                  value={draft.gamma}
                  onChange={(e) => update("gamma", Number(e.target.value))}
                />
              </Field>
              <Field
                label="Mức phạt khi phải bỏ học phần"
                hint="Để rất cao để hệ thống chỉ bỏ khi thật sự không còn cách nào."
              >
                <input
                  type="number"
                  min={0}
                  className={inputClass}
                  value={draft.skipPenalty}
                  onChange={(e) => update("skipPenalty", Number(e.target.value))}
                />
              </Field>
            </div>

            <Field
              label="Mã lần chạy"
              className="mt-3"
              hint="Cùng mã và cùng dữ liệu thì cho ra cùng một lịch. Đổi mã để thử phương án khác."
            >
              <input
                type="number"
                className={inputClass}
                value={draft.seed}
                onChange={(e) => update("seed", Number(e.target.value))}
              />
            </Field>
          </details>

          <div className="mt-5 flex flex-wrap items-center gap-2 border-t border-ink-100 pt-4">
            <Button variant="primary" onClick={solve} disabled={running}>
              {running ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
              {running ? "Đang xếp lịch…" : "Xếp lịch thi"}
            </Button>
            <Button variant="ghost" onClick={() => setDraft(params)} disabled={running}>
              <RotateCcw className="h-3.5 w-3.5" />
              Khôi phục mặc định
            </Button>
            {result ? (
              <Link href="/solution" className="ml-auto">
                <Button variant="secondary" size="sm">
                  Xem lịch đã xếp
                  <ArrowRight className="h-3.5 w-3.5" />
                </Button>
              </Link>
            ) : null}
          </div>

          {error ? (
            <div className="mt-4 flex items-start gap-2.5 rounded-lg bg-rose-50 px-3.5 py-2.5 text-[12.5px] text-rose-800 ring-1 ring-inset ring-rose-200">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              <span className="flex-1 leading-relaxed">{error}</span>
            </div>
          ) : null}
        </Card>

        <Card>
          <CardHeader
            title="Dữ liệu sẽ đưa vào xếp lịch"
            desc="Đây là những gì hệ thống đang có. Sai ở đây thì lịch ra cũng sai."
          />
          <ul className="mt-4 space-y-2.5">
            {[
              {
                label: "Học phần cần xếp",
                value: `${SUBJECTS.length} học phần`,
                icon: <GraduationCap className="h-3.5 w-3.5" />,
              },
              {
                label: "Phòng máy dùng được",
                value: `${working.length} phòng`,
                icon: <DoorOpen className="h-3.5 w-3.5" />,
              },
              {
                label: "Ngày thi",
                value: `${examDays} ngày · 4 ca/ngày`,
                icon: <CalendarDays className="h-3.5 w-3.5" />,
              },
              {
                label: "Lượt đăng ký môn",
                value: `${ENROLLMENT.length} lượt`,
                icon: <Users className="h-3.5 w-3.5" />,
              },
            ].map((r) => (
              <li
                key={r.label}
                className="flex items-center justify-between rounded-lg border border-ink-200 px-3 py-2"
              >
                <span className="flex items-center gap-2 text-[12.5px] text-ink-600">
                  <span className="text-ink-400">{r.icon}</span>
                  {r.label}
                </span>
                <span className="tabular-nums text-[13px] font-semibold text-ink-900">{r.value}</span>
              </li>
            ))}
          </ul>
          <p className="mt-3 text-[11.5px] leading-relaxed text-ink-400">
            Nếu dữ liệu chưa đúng, vào mục &ldquo;Dữ liệu xếp lịch&rdquo; để xem chi tiết từng học phần
            và từng phòng.
          </p>
        </Card>
      </div>

      {result ? (
        <div className="mt-4 animate-rise">
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <Badge tone={statusOf(result.stats.status).tone}>
              {statusOf(result.stats.status).text}
            </Badge>
            <span className="text-[12.5px] text-ink-500">
              Xếp lúc {formatDateTime(result.ranAt)} · mất {result.stats.solveTime.toFixed(1)} giây
            </span>
            <Button variant="ghost" size="sm" className="ml-auto" onClick={clearResult}>
              Xoá kết quả này
            </Button>
          </div>

          <p className="mb-3 rounded-lg bg-ink-50 px-3.5 py-3 text-[13px] leading-relaxed text-ink-700 ring-1 ring-inset ring-ink-200">
            {summarizeResult({
              totalSubjects: SUBJECTS.length,
              scheduledSubjects,
              unscheduledSubjects: result.stats.unscheduledSubjects,
              sessions: result.sessions.length,
              roomsOpened: result.stats.roomsOpened,
              days: examDays,
              studentsPlaced: result.registrations.length,
              totalStudents: 0,
            })}
          </p>

          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <Stat
              label="Ca thi đã xếp"
              value={`${result.sessions.length} ca`}
              hint={`Dùng ${result.stats.roomsOpened} phòng`}
              tone="success"
            />
            <Stat
              label="Học phần đã xếp"
              value={`${scheduledSubjects}/${SUBJECTS.length}`}
              hint={
                result.stats.unscheduledSubjects
                  ? `Còn ${result.stats.unscheduledSubjects} học phần chưa xếp được`
                  : "Đủ toàn bộ học phần"
              }
              tone={result.stats.unscheduledSubjects ? "warning" : "success"}
            />
            <Stat
              label="Sinh viên đã có chỗ"
              value={`${result.registrations.length}`}
              hint={`${result.registrations.length} lượt đăng ký được xếp`}
              tone="info"
            />
            <Stat
              label="Chất lượng phương án"
              value={statusOf(result.stats.status).text}
              hint={statusOf(result.stats.status).plain}
              tone={statusOf(result.stats.status).tone}
            />
          </div>

          <details className="mt-3 rounded-lg border border-ink-200 bg-white px-3.5 py-3">
            <summary className="cursor-pointer text-[12px] font-medium text-ink-600">
              Thông số kỹ thuật của lần chạy
            </summary>
            <dl className="mt-2.5 grid gap-x-6 gap-y-1.5 text-[11.5px] sm:grid-cols-2">
              {[
                ["Trạng thái bộ giải", result.stats.status],
                ["Giá trị hàm mục tiêu", result.stats.objective.toFixed(1)],
                ["Cận dưới", result.stats.bestBound.toFixed(1)],
                ["Z1 · phòng mở", String(result.stats.Z1)],
                ["Z2 · áp lực ngày", String(result.stats.Z2)],
                ["Số ca theo bộ giải", String(result.stats.sessions)],
              ].map(([k, v]) => (
                <div key={k} className="flex justify-between gap-3">
                  <dt className="text-ink-400">{k}</dt>
                  <dd className="tabular-nums font-medium text-ink-700">{v}</dd>
                </div>
              ))}
            </dl>
          </details>
        </div>
      ) : null}
    </>
  );
}
