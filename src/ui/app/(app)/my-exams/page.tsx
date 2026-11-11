"use client";

import { useMemo } from "react";
import { CalendarClock, CalendarX2, CheckCircle2, Clock, MapPin } from "lucide-react";
import { useApp } from "@/lib/store";
import { useStudentSchedule } from "@/lib/student";
import { formatDate, weekdayOf } from "@/lib/utils";
import { caWithTime, hinhThucPlain, softwarePlain } from "@/lib/labels";
import {
  Badge,
  Button,
  Card,
  CardHeader,
  EmptyState,
  PageHeader,
  Stat,
  Table,
} from "@/components/ui";

/** "2026-11-16" so với hôm nay, theo giờ máy người dùng. */
function daysUntil(iso: string): number {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const target = new Date(`${iso}T00:00:00`);
  return Math.round((target.getTime() - today.getTime()) / 86_400_000);
}

export default function MyExamsPage() {
  const { user } = useApp();
  const { data, loading, error, reload } = useStudentSchedule(user?.maSv);

  const exams = data?.exams ?? [];

  const { next, days, rooms } = useMemo(() => {
    const sorted = [...exams].sort(
      (a, b) => a.ngayThi.localeCompare(b.ngayThi) || a.caThi - b.caThi,
    );
    const upcoming = sorted.find((e) => daysUntil(e.ngayThi) >= 0) ?? null;
    return {
      next: upcoming,
      days: Array.from(new Set(sorted.map((e) => e.ngayThi))).sort(),
      rooms: Array.from(new Set(sorted.map((e) => e.maPhong))),
    };
  }, [exams]);

  if (loading) {
    return (
      <>
        <PageHeader eyebrow="Tra cứu" title="Lịch thi của tôi" desc="Đang tải lịch thi…" />
        <Card>
          <p className="py-10 text-center text-[13px] text-ink-500">Đang đọc dữ liệu từ MySQL…</p>
        </Card>
      </>
    );
  }

  if (error) {
    return (
      <>
        <PageHeader eyebrow="Tra cứu" title="Lịch thi của tôi" desc="Không đọc được lịch thi." />
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

  if (!exams.length) {
    return (
      <>
        <PageHeader
          eyebrow="Tra cứu"
          title="Lịch thi của tôi"
          desc={data ? `${data.student.hoTen} · Lớp ${data.student.lop}` : undefined}
        />
        <Card>
          <EmptyState
            title="Chưa có lịch thi nào được công bố"
            desc="Bạn chưa đăng ký môn thi nào, hoặc Phòng Đào tạo chưa công bố lịch thi học kỳ này. Lịch sẽ hiện ở đây ngay khi được công bố."
            icon={<CalendarX2 className="h-6 w-6" />}
          />
        </Card>
      </>
    );
  }

  const nextIn = next ? daysUntil(next.ngayThi) : null;

  return (
    <>
      <PageHeader
        eyebrow="Tra cứu"
        title="Lịch thi của tôi"
        desc={
          data
            ? `${data.student.hoTen} · ${data.student.maSv} · Lớp ${data.student.lop} · ${data.student.khoa}`
            : undefined
        }
      />

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Stat
          label="Số ca thi"
          value={`${exams.length}`}
          hint={`Trong ${days.length} ngày thi`}
          icon={<CalendarClock className="h-4 w-4" />}
          tone="info"
        />
        <Stat
          label="Ca thi gần nhất"
          value={next ? formatDate(next.ngayThi) : "—"}
          hint={
            next
              ? nextIn === 0
                ? "Hôm nay"
                : `Còn ${nextIn} ngày · ${caWithTime(next.caThi, next.gioBd, next.gioKt)}`
              : "Không còn ca nào phía trước"
          }
          icon={<Clock className="h-4 w-4" />}
          tone={nextIn !== null && nextIn <= 3 ? "warning" : "neutral"}
        />
        <Stat
          label="Phòng máy phải đến"
          value={`${rooms.length}`}
          hint={rooms.join(", ")}
          icon={<MapPin className="h-4 w-4" />}
          tone="neutral"
        />
        <Stat
          label="Trạng thái lịch"
          value="Đã công bố"
          hint="Chỉ hiển thị phương án Phòng Đào tạo đã công bố"
          icon={<CheckCircle2 className="h-4 w-4" />}
          tone="success"
        />
      </div>

      {next ? (
        <Card className="mt-4">
          <CardHeader
            title="Ca thi gần nhất"
            desc="Có mặt trước giờ bắt đầu ít nhất 15 phút, mang theo thẻ sinh viên."
            action={<Badge tone={nextIn !== null && nextIn <= 3 ? "warning" : "info"}>
              {nextIn === 0 ? "Hôm nay" : `Còn ${nextIn} ngày`}
            </Badge>}
          />
          <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-400">Học phần</p>
              <p className="mt-1 text-[14px] font-semibold text-ink-900">{next.tenMon}</p>
              <p className="font-mono text-[11.5px] text-ink-400">{next.maMon}</p>
            </div>
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-400">Thời gian</p>
              <p className="mt-1 text-[14px] font-semibold text-ink-900">
                {weekdayOf(next.ngayThi)}, {formatDate(next.ngayThi)}
              </p>
              <p className="text-[11.5px] text-ink-400">{caWithTime(next.caThi, next.gioBd, next.gioKt)}</p>
            </div>
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-400">Phòng thi</p>
              <p className="mt-1 text-[14px] font-semibold text-ink-900">{next.maPhong}</p>
              <p className="text-[11.5px] text-ink-400">
                {next.tenPhong} · {next.toaNha}, tầng {next.tang}
              </p>
            </div>
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-400">Máy số</p>
              <p className="mt-1 text-[14px] font-semibold text-ink-900">{next.soMay}</p>
              <p className="text-[11.5px] text-ink-400">{hinhThucPlain(next.hinhThuc)}</p>
            </div>
          </div>
        </Card>
      ) : null}

      <Card className="mt-4" padded={false}>
        <div className="p-5 pb-3">
          <CardHeader
            title="Toàn bộ lịch thi"
            desc="Mỗi dòng là một ca thi của bạn: ngày nào, ca mấy, môn nào, phòng nào, ngồi máy số mấy."
            action={<Badge tone="neutral">{exams.length} ca</Badge>}
          />
        </div>
        <Table>
          <thead>
            <tr>
              <th>Ngày &amp; ca thi</th>
              <th>Học phần</th>
              <th>Hình thức</th>
              <th>Phòng thi</th>
              <th className="text-center">Máy số</th>
            </tr>
          </thead>
          <tbody>
            {exams.map((e) => {
              const d = daysUntil(e.ngayThi);
              return (
                <tr key={e.maLich}>
                  <td className="whitespace-nowrap">
                    <span className="font-medium text-ink-800">
                      {weekdayOf(e.ngayThi)}, {formatDate(e.ngayThi)}
                    </span>
                    <span className="ml-1.5 text-[11.5px] text-ink-400">
                      {caWithTime(e.caThi, e.gioBd, e.gioKt)}
                    </span>
                    {d >= 0 && d <= 3 ? (
                      <Badge tone="warning" className="ml-2">
                        {d === 0 ? "Hôm nay" : `${d} ngày nữa`}
                      </Badge>
                    ) : null}
                  </td>
                  <td className="whitespace-nowrap">
                    <span className="font-medium text-ink-800">{e.tenMon}</span>
                    <span className="ml-1.5 font-mono text-[11.5px] text-ink-400">{e.maMon}</span>
                    <span className="ml-1.5 text-[11.5px] text-ink-400">· {e.soTinChi} TC</span>
                  </td>
                  <td className="whitespace-nowrap text-[12.5px] text-ink-600">
                    {hinhThucPlain(e.hinhThuc)}
                    <span className="ml-1 text-ink-400">· {e.thoiLuongPhut} phút</span>
                  </td>
                  <td className="whitespace-nowrap text-[12.5px]">
                    {e.maPhong}
                    <span className="ml-1 text-ink-400">
                      · {e.toaNha}, tầng {e.tang}
                    </span>
                  </td>
                  <td className="text-center tabular-nums">
                    <Badge tone="info">{e.soMay}</Badge>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </Table>
      </Card>

      <Card className="mt-4">
        <div className="flex items-start gap-2.5 text-[12.5px] leading-relaxed text-ink-500">
          <CalendarClock className="mt-0.5 h-4 w-4 shrink-0 text-ink-300" />
          <span>
            Nếu thấy trùng giờ hoặc sai phòng, báo ngay cho Phòng Đào tạo trước ngày thi. Lịch này
            lấy từ phương án đã công bố, nên mọi thay đổi sau đó sẽ được cập nhật lại tại đây.
          </span>
        </div>
      </Card>
    </>
  );
}
