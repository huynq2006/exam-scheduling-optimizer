"use client";

import Link from "next/link";
import {
  ArrowUpRight,
  CalendarDays,
  CheckCircle2,
  DoorOpen,
  GraduationCap,
  Play,
  Timer,
  Users,
} from "lucide-react";
import { useApp } from "@/lib/store";
import { useDataset } from "@/lib/dataset";
import { formatDateTime, percent, weekdayOf, formatDate } from "@/lib/utils";
import { statusOf, summarizeResult } from "@/lib/labels";
import { Badge, Button, Card, CardHeader, PageHeader, Progress, Stat } from "@/components/ui";

export default function DashboardPage() {
  const { user, result } = useApp();
  const { subjects: SUBJECTS, rooms: ROOMS, slots: SLOTS, students: STUDENTS, enrollment: ENROLLMENT, loading, error, reload } = useDataset();
  if (!user) return null;

  if (loading) {
    return (
      <>
        <PageHeader eyebrow={`Xin chào, ${user.name}`} title="Xếp lịch thi học kỳ" desc="Đang tải dữ liệu từ cơ sở dữ liệu…" />
        <Card>
          <p className="py-10 text-center text-[13px] text-ink-500">Đang đọc dữ liệu từ MySQL…</p>
        </Card>
      </>
    );
  }

  if (error) {
    return (
      <>
        <PageHeader eyebrow={`Xin chào, ${user.name}`} title="Xếp lịch thi học kỳ" desc="Không đọc được dữ liệu." />
        <Card>
          <div className="py-8 text-center">
            <p className="text-[13px] font-medium text-rose-700">Không kết nối được cơ sở dữ liệu</p>
            <p className="mx-auto mt-2 max-w-lg text-[12.5px] leading-relaxed text-ink-500">{error}</p>
            <Button variant="secondary" size="sm" className="mt-4" onClick={reload}>
              Thử lại
            </Button>
          </div>
        </Card>
      </>
    );
  }

  const working = ROOMS.filter((r) => r.tinhTrang === "Working");
  const examDays = Array.from(new Set(SLOTS.map((s) => s.ngayThi))).sort();

  const seats = result?.registrations.length ?? 0;
  const capacity =
    result?.sessions.reduce(
      (a, s) => a + (ROOMS.find((r) => r.maPhong === s.maPhong)?.sucChua ?? 0),
      0,
    ) ?? 0;

  const scheduledSubjects = result
    ? new Set(result.sessions.map((s) => s.maMon)).size
    : 0;

  return (
    <>
      <PageHeader
        eyebrow={`Xin chào, ${user.name}`}
        title="Xếp lịch thi học kỳ"
        desc="Khu vực làm việc của Phòng Đào tạo: kiểm tra dữ liệu, xếp lịch thi, rồi đọc và xuất lịch cho các khoa."
        action={
          <Link href="/solve">
            <Button variant="primary">
              <Play className="h-4 w-4" />
              Xếp lịch thi
            </Button>
          </Link>
        }
      />

      {/* Việc cần làm trước khi xếp lịch — ngôn ngữ nghiệp vụ, không phải ký hiệu */}
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Stat
          label="Học phần cần thi"
          value={`${SUBJECTS.length}`}
          hint={`${STUDENTS.length} sinh viên đăng ký`}
          icon={<GraduationCap className="h-4 w-4" />}
        />
        <Stat
          label="Phòng máy dùng được"
          value={`${working.length}/${ROOMS.length}`}
          hint={
            ROOMS.length - working.length > 0
              ? `${ROOMS.length - working.length} phòng đang bảo trì, không xếp được`
              : "Tất cả phòng đều sẵn sàng"
          }
          icon={<DoorOpen className="h-4 w-4" />}
          tone={working.length === ROOMS.length ? "success" : "warning"}
        />
        <Stat
          label="Ngày thi"
          value={`${examDays.length}`}
          hint={`${formatDate(examDays[0])} – ${formatDate(examDays[examDays.length - 1])} · 4 ca/ngày`}
          icon={<CalendarDays className="h-4 w-4" />}
        />
        <Stat
          label="Lượt đăng ký môn"
          value={`${ENROLLMENT.length}`}
          hint={`Trung bình ${Math.round((ENROLLMENT.length / STUDENTS.length) * 10) / 10} môn mỗi sinh viên`}
          icon={<Users className="h-4 w-4" />}
        />
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-[1.5fr_1fr]">
        <Card>
          <CardHeader
            title="Lần xếp lịch gần nhất"
            desc={
              result
                ? "Kết quả thật của lần chạy gần nhất trong phiên làm việc này."
                : "Chưa xếp lịch lần nào trong phiên làm việc này."
            }
            action={
              result ? (
                <Badge tone={statusOf(result.stats.status).tone}>
                  {statusOf(result.stats.status).text}
                </Badge>
              ) : (
                <Badge tone="muted">Chưa xếp lịch</Badge>
              )
            }
          />

          {result ? (
            <>
              <p className="mt-4 rounded-lg bg-ink-50 px-3.5 py-3 text-[13px] leading-relaxed text-ink-700 ring-1 ring-inset ring-ink-200">
                {summarizeResult({
                  totalSubjects: SUBJECTS.length,
                  scheduledSubjects,
                  unscheduledSubjects: result.stats.unscheduledSubjects,
                  sessions: result.sessions.length,
                  roomsOpened: result.stats.roomsOpened,
                  days: examDays.length,
                  studentsPlaced: seats,
                  totalStudents: STUDENTS.length,
                })}
              </p>

              <div className="mt-4 grid gap-3 sm:grid-cols-3">
                <div className="rounded-lg border border-ink-200 px-3 py-2.5">
                  <p className="text-[11.5px] text-ink-400">Số ca thi</p>
                  <p className="mt-0.5 text-[16px] font-semibold tabular-nums text-ink-900">
                    {result.sessions.length}
                  </p>
                </div>
                <div className="rounded-lg border border-ink-200 px-3 py-2.5">
                  <p className="text-[11.5px] text-ink-400">Phòng phải mở</p>
                  <p className="mt-0.5 text-[16px] font-semibold tabular-nums text-ink-900">
                    {result.stats.roomsOpened}
                  </p>
                </div>
                <div className="rounded-lg border border-ink-200 px-3 py-2.5">
                  <p className="text-[11.5px] text-ink-400">Sinh viên đã có chỗ</p>
                  <p className="mt-0.5 text-[16px] font-semibold tabular-nums text-ink-900">
                    {seats}
                  </p>
                </div>
              </div>

              <div className="mt-4">
                <div className="mb-1.5 flex items-baseline justify-between gap-3">
                  <span className="text-[12.5px] text-ink-600">Mức sử dụng chỗ ngồi</span>
                  <span className="text-[11.5px] tabular-nums text-ink-400">
                    {seats}/{capacity} chỗ · {percent(seats, capacity)}%
                  </span>
                </div>
                <Progress
                  value={percent(seats, capacity)}
                  tone={percent(seats, capacity) > 90 ? "warning" : "info"}
                />
              </div>

              <ul className="mt-4 space-y-2 text-[12.5px] text-ink-600">
                <li className="flex items-center justify-between border-t border-ink-100 pt-2">
                  <span>Học phần chưa xếp được</span>
                  <span
                    className={
                      result.stats.unscheduledSubjects
                        ? "font-semibold tabular-nums text-amber-700"
                        : "font-medium tabular-nums text-ink-900"
                    }
                  >
                    {result.stats.unscheduledSubjects}
                  </span>
                </li>
                <li className="flex items-center justify-between">
                  <span>Thời gian hệ thống chạy</span>
                  <span className="tabular-nums font-medium text-ink-900">
                    {result.stats.solveTime.toFixed(1)} giây
                  </span>
                </li>
                <li className="flex items-center justify-between">
                  <span>Xếp lúc</span>
                  <span className="font-medium text-ink-900">{formatDateTime(result.ranAt)}</span>
                </li>
              </ul>

              <div className="mt-4 flex gap-2 border-t border-ink-100 pt-4">
                <Link href="/solution">
                  <Button variant="secondary" size="sm">
                    Xem lịch thi
                    <ArrowUpRight className="h-3.5 w-3.5" />
                  </Button>
                </Link>
                <Link href="/solve">
                  <Button variant="ghost" size="sm">
                    <Timer className="h-3.5 w-3.5" />
                    Xếp lại
                  </Button>
                </Link>
              </div>
            </>
          ) : (
            <div className="mt-6 rounded-lg border border-dashed border-ink-300 px-4 py-10 text-center">
              <p className="text-[13px] leading-relaxed text-ink-500">
                Chưa có lịch thi nào. Bấm nút bên dưới để hệ thống xếp lịch từ dữ liệu hiện tại.
              </p>
              <Link href="/solve">
                <Button variant="primary" size="sm" className="mt-3">
                  <Play className="h-3.5 w-3.5" />
                  Xếp lịch ngay
                </Button>
              </Link>
            </div>
          )}
        </Card>

        <Card>
          <CardHeader title="Các bước làm việc" desc="Làm đúng thứ tự này là xong một kỳ thi." />
          <ol className="mt-4 space-y-3">
            {[
              {
                href: "/inputs",
                label: "1. Kiểm tra dữ liệu",
                desc: "Học phần nào thi, phòng nào dùng được, ngày nào thi, sinh viên đăng ký môn gì.",
              },
              {
                href: "/solve",
                label: "2. Xếp lịch",
                desc: "Chọn thời gian chờ rồi bấm xếp. Hệ thống tự tìm cách xếp hợp lý nhất.",
              },
              {
                href: "/solution",
                label: "3. Đọc và dùng lịch",
                desc: "Xem lịch theo ngày, theo học phần; biết học phần nào chưa xếp được và vì sao.",
              },
            ].map((s) => (
              <li key={s.href}>
                <Link
                  href={s.href}
                  className="flex items-start gap-3 rounded-lg border border-ink-200 px-3 py-2.5 transition-colors hover:bg-ink-50"
                >
                  <div className="min-w-0 flex-1">
                    <p className="text-[12.5px] font-medium text-ink-900">{s.label}</p>
                    <p className="mt-0.5 text-[11.5px] leading-relaxed text-ink-500">{s.desc}</p>
                  </div>
                  <ArrowUpRight className="mt-0.5 h-3.5 w-3.5 shrink-0 text-ink-300" />
                </Link>
              </li>
            ))}
          </ol>

          <div className="mt-4 flex items-start gap-2 border-t border-ink-100 pt-3">
            <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-600" />
            <p className="text-[11.5px] leading-relaxed text-ink-500">
              Lịch hệ thống xếp ra luôn thoả các điều kiện bắt buộc: không trùng phòng, không trùng
              giờ của một sinh viên, phòng đủ phần mềm cho môn thi.
            </p>
          </div>
        </Card>
      </div>
    </>
  );
}
