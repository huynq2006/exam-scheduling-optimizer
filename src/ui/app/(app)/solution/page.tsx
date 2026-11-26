"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronRight,
  Filter,
  Play,
  Users,
  X,
} from "lucide-react";
import { useApp } from "@/lib/store";
import { useDataset } from "@/lib/dataset";
import { useAllStatuses } from "@/lib/exam-status";
import { cn, formatDate, percent, weekdayOf, isCompatible } from "@/lib/utils";
import { caWithTime, statusOf, unscheduledHint } from "@/lib/labels";
import { effectiveStatus } from "@/lib/status-shared";
import { RosterDrawer, type RosterTarget } from "@/components/roster-drawer";
import { StatusPill } from "@/components/status-ui";
import {
  Badge,
  Button,
  Card,
  CardHeader,
  EmptyState,
  Field,
  PageHeader,
  Progress,
  Stat,
  Table,
  selectClass,
} from "@/components/ui";

export default function SolutionPage() {
  const { result } = useApp();
  const { subjects: SUBJECTS, rooms: ROOMS, slots: SLOTS, students: STUDENTS, loading, error, reload } = useDataset();
  const { statuses, reload: reloadStatuses } = useAllStatuses();

  const [day, setDay] = useState("all");
  const [mon, setMon] = useState("all");
  const [onlyProblem, setOnlyProblem] = useState(false);
  const [open, setOpen] = useState<RosterTarget | null>(null);

  const ROOM_BY_CODE = useMemo(() => new Map(ROOMS.map((r) => [r.maPhong, r])), [ROOMS]);
  const SLOT_BY_CODE = useMemo(() => new Map(SLOTS.map((s) => [s.maKhung, s])), [SLOTS]);
  const SUBJECT_BY_CODE = useMemo(() => new Map(SUBJECTS.map((s) => [s.maMon, s])), [SUBJECTS]);
  const STUDENT_BY_CODE = useMemo(() => new Map(STUDENTS.map((s) => [s.maSv, s])), [STUDENTS]);

  /**
   * Mỗi ca thi được làm giàu thêm số sinh viên bị vướng trạng thái.
   *
   * Tính từ danh sách đăng ký của bộ giải (maLich -> maSv) chứ không gọi
   * thêm API cho từng ca: 16 ca thì 16 request là lãng phí, mà dữ liệu đã
   * có sẵn trong bộ nhớ.
   */
  const rows = useMemo(() => {
    if (!result) return [];
    return result.sessions
      .map((s) => {
        const slot = SLOT_BY_CODE.get(s.maKhung);
        const room = ROOM_BY_CODE.get(s.maPhong);
        const subject = SUBJECT_BY_CODE.get(s.maMon);
        const seats = result.registrations.filter((r) => r.maLich === s.maLich);

        let camThi = 0;
        let chuaNop = 0;
        for (const reg of seats) {
          const eff = effectiveStatus(statuses, reg.maSv, s.maMon);
          if (eff?.trangThai === "CAM_THI") camThi += 1;
          else if (eff?.trangThai === "CHUA_NOP_HOC_PHI") chuaNop += 1;
        }

        return {
          ...s,
          ngayThi: slot?.ngayThi ?? "",
          caThi: slot?.caThi ?? 0,
          gioBd: slot?.gioBd ?? "",
          gioKt: slot?.gioKt ?? "",
          tenMon: subject?.tenMon ?? s.maMon,
          sucChua: room?.sucChua ?? 0,
          toaNha: room?.toaNha ?? "",
          tang: room?.tang ?? 0,
          soSv: seats.length,
          camThi,
          chuaNop,
        };
      })
      .filter((s) => (day === "all" || s.ngayThi === day) && (mon === "all" || s.maMon === mon))
      .filter((s) => !onlyProblem || s.camThi > 0 || s.chuaNop > 0)
      .sort(
        (a, b) =>
          a.ngayThi.localeCompare(b.ngayThi) ||
          a.caThi - b.caThi ||
          a.maPhong.localeCompare(b.maPhong),
      );
  }, [result, day, mon, onlyProblem, statuses, ROOM_BY_CODE, SLOT_BY_CODE, SUBJECT_BY_CODE]);

  if (loading) {
    return (
      <>
        <PageHeader eyebrow="Xếp lịch" title="Lịch thi đã xếp" desc="Đang tải dữ liệu…" />
        <Card>
          <p className="py-10 text-center text-[13px] text-ink-500">Đang tải dữ liệu…</p>
        </Card>
      </>
    );
  }

  if (error) {
    return (
      <>
        <PageHeader eyebrow="Xếp lịch" title="Lịch thi đã xếp" desc="Không đọc được dữ liệu." />
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

  if (!result) {
    return (
      <>
        <PageHeader
          eyebrow="Xếp lịch"
          title="Lịch thi đã xếp"
          desc="Trang này hiện lịch sau khi xếp xong."
        />
        <Card>
          <EmptyState
            title="Chưa có lịch thi nào"
            desc="Bấm xếp lịch trước, lịch thi sẽ hiện ở đây."            icon={<Play className="h-6 w-6" />}
          />
          <div className="flex justify-center pb-6">
            <Link href="/solve">
              <Button variant="primary">
                <Play className="h-4 w-4" />
                Xếp lịch thi
              </Button>
            </Link>
          </div>
        </Card>
      </>
    );
  }

  const days = Array.from(
    new Set(result.sessions.map((s) => SLOT_BY_CODE.get(s.maKhung)?.ngayThi ?? "")),
  )
    .filter(Boolean)
    .sort();
  const subjectsUsed = Array.from(new Set(result.sessions.map((s) => s.maMon))).sort();

  const totalSeats = result.registrations.length;
  const totalCapacity = result.sessions.reduce(
    (a, s) => a + (ROOM_BY_CODE.get(s.maPhong)?.sucChua ?? 0),
    0,
  );

  // Tổng số lượt dự thi bị ảnh hưởng, tính trên toàn bộ lịch chứ không chỉ dòng đang lọc.
  let totalCamThi = 0;
  let totalChuaNop = 0;
  for (const s of result.sessions) {
    for (const reg of result.registrations.filter((r) => r.maLich === s.maLich)) {
      const eff = effectiveStatus(statuses, reg.maSv, s.maMon);
      if (eff?.trangThai === "CAM_THI") totalCamThi += 1;
      else if (eff?.trangThai === "CHUA_NOP_HOC_PHI") totalChuaNop += 1;
    }
  }

  const perDay = days.map((d) => {
    const daySessions = result.sessions.filter(
      (s) => SLOT_BY_CODE.get(s.maKhung)?.ngayThi === d,
    );
    const seats = daySessions.reduce(
      (a, s) => a + result.registrations.filter((r) => r.maLich === s.maLich).length,
      0,
    );
    const cap = daySessions.reduce((a, s) => a + (ROOM_BY_CODE.get(s.maPhong)?.sucChua ?? 0), 0);
    return { day: d, sessions: daySessions.length, seats, cap, load: percent(seats, cap) };
  });

  const unscheduledSubjects = Array.from(new Set(result.unscheduled.map((u) => u.maMon)));

  return (
    <>
      <PageHeader
        eyebrow="Xếp lịch"
        title="Lịch thi đã xếp"
        desc="Bấm vào một ca thi để xem danh sách sinh viên."
      />

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Stat
          label="Ca thi"
          value={`${result.sessions.length}`}
          hint={`Trong ${days.length} ngày · ${result.stats.roomsOpened} phòng được dùng`}
        />
        <Stat
          label="Sinh viên đã có chỗ thi"
          value={`${totalSeats}`}
          hint={`${result.registrations.length} lượt đăng ký môn`}
          tone="success"
        />
        <Stat
          label="Lượt thi bị cấm"
          value={`${totalCamThi}`}
          hint={totalCamThi ? "Trong toàn bộ lịch" : "Không có"}
          tone={totalCamThi ? "danger" : "success"}
        />
        <Stat
          label="Lượt chưa nộp học phí"
          value={`${totalChuaNop}`}
          hint={totalChuaNop ? "Trong toàn bộ lịch" : "Không có"}
          tone={totalChuaNop ? "warning" : "success"}
        />
      </div>

      <Card className="mt-4">
        <div className="grid gap-3 sm:grid-cols-[1fr_1fr_auto] sm:items-end">
          <Field label="Xem theo ngày">
            <select className={selectClass} value={day} onChange={(e) => setDay(e.target.value)}>
              <option value="all">Tất cả ngày</option>
              {days.map((d) => (
                <option key={d} value={d}>
                  {weekdayOf(d)}, {formatDate(d)}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Xem theo học phần">
            <select className={selectClass} value={mon} onChange={(e) => setMon(e.target.value)}>
              <option value="all">Tất cả học phần</option>
              {subjectsUsed.map((m) => (
                <option key={m} value={m}>
                  {SUBJECT_BY_CODE.get(m)?.tenMon ?? m}
                </option>
              ))}
            </select>
          </Field>
          <div className="flex flex-wrap items-center gap-2 pb-0.5">
            <label className="flex cursor-pointer items-center gap-1.5 text-[12.5px] text-ink-600">
              <input
                type="checkbox"
                checked={onlyProblem}
                onChange={(e) => setOnlyProblem(e.target.checked)}
                className="h-3.5 w-3.5 rounded border-ink-300 text-accent-600 focus:ring-accent-400"
              />
              Chỉ ca có vấn đề
            </label>
            <span className="inline-flex items-center gap-1.5 text-[12.5px] text-ink-500">
              <Filter className="h-3.5 w-3.5" />
              {rows.length}/{result.sessions.length} ca
            </span>
            {day !== "all" || mon !== "all" || onlyProblem ? (
              <Button
                size="sm"
                variant="ghost"
                onClick={() => {
                  setDay("all");
                  setMon("all");
                  setOnlyProblem(false);
                }}
              >
                <X className="h-3.5 w-3.5" />
                Bỏ lọc
              </Button>
            ) : null}
          </div>
        </div>
      </Card>

      <Card className="mt-4" padded={false}>
        {rows.length ? (
          <Table>
            <thead>
              <tr>
                <th>Ngày &amp; ca thi</th>
                <th>Học phần</th>
                <th>Phòng thi</th>
                <th className="text-right">Sĩ số</th>
                <th className="text-center">Trạng thái dự thi</th>
                <th className="w-8" />
              </tr>
            </thead>
            <tbody>
              {rows.map((s) => {
                const free = s.sucChua - s.soSv;
                const hasProblem = s.camThi > 0 || s.chuaNop > 0;
                return (
                  <tr
                    key={s.maLich}
                    onClick={() =>
                      setOpen({
                        maLich: s.maLich,
                        tenMon: s.tenMon,
                        maMon: s.maMon,
                        ngayThi: s.ngayThi,
                        caThi: s.caThi,
                        gioBd: s.gioBd,
                        gioKt: s.gioKt,
                        maPhong: s.maPhong,
                        toaNha: s.toaNha,
                        tang: s.tang,
                        sucChua: s.sucChua,
                      })
                    }
                    className={cn(
                      "cursor-pointer transition-colors",
                      s.camThi > 0
                        ? "bg-rose-50/60 hover:bg-rose-50"
                        : s.chuaNop > 0
                          ? "bg-amber-50/50 hover:bg-amber-50"
                          : "",
                    )}
                    title="Bấm để xem danh sách sinh viên"
                  >
                    <td className="whitespace-nowrap">
                      <span className="font-medium text-ink-800">
                        {weekdayOf(s.ngayThi)}, {formatDate(s.ngayThi)}
                      </span>
                      <span className="ml-1.5 text-[11.5px] text-ink-400">
                        {caWithTime(s.caThi, s.gioBd, s.gioKt)}
                      </span>
                    </td>
                    <td className="whitespace-nowrap">
                      <span className="font-medium text-ink-800">{s.tenMon}</span>
                      <span className="ml-1.5 font-mono text-[11.5px] text-ink-400">{s.maMon}</span>
                    </td>
                    <td className="whitespace-nowrap text-[12.5px]">
                      {s.maPhong}
                      <span className="ml-1 text-ink-400">
                        · {s.toaNha}, tầng {s.tang}
                      </span>
                    </td>
                    <td className="whitespace-nowrap text-right tabular-nums">
                      <span className="font-medium">{s.soSv}</span>
                      <span className="text-ink-400">/{s.sucChua}</span>
                      {free > 0 ? (
                        <span className="ml-1 text-[11px] text-ink-400">· {free} trống</span>
                      ) : null}
                    </td>
                    <td className="whitespace-nowrap">
                      <div className="flex flex-wrap items-center justify-center gap-1.5">
                        {s.camThi ? (
                          <Badge tone="danger">{s.camThi} cấm thi</Badge>
                        ) : null}
                        {s.chuaNop ? (
                          <Badge tone="warning">{s.chuaNop} chưa nộp HP</Badge>
                        ) : null}
                        {!hasProblem ? (
                          <span className="inline-flex items-center gap-1 text-[11.5px] text-emerald-600">
                            <CheckCircle2 className="h-3.5 w-3.5" />
                            Bình thường
                          </span>
                        ) : null}
                      </div>
                    </td>
                    <td className="text-right">
                      <ChevronRight className="ml-auto h-4 w-4 text-ink-300" />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </Table>
        ) : (
          <EmptyState
            title="Không có ca thi nào khớp bộ lọc"
            desc="Thử chọn ngày khác, bỏ lọc học phần, hoặc tắt “chỉ ca có vấn đề”."
            icon={<Filter className="h-6 w-6" />}
          />
        )}
      </Card>

      <Card className="mt-4">
        <div className="flex items-start gap-2.5 text-[12.5px] leading-relaxed text-ink-500">
          <Users className="mt-0.5 h-4 w-4 shrink-0 text-ink-300" />
          <span>
            Dòng{" "}
            <span className="rounded bg-rose-50 px-1 font-medium text-rose-700 ring-1 ring-inset ring-rose-200">
              đỏ
            </span>{" "}
            là cấm thi,{" "}
            <span className="rounded bg-amber-50 px-1 font-medium text-amber-700 ring-1 ring-inset ring-amber-200">
              vàng
            </span>{" "}
            là chưa nộp học phí.
          </span>
        </div>
      </Card>

      <Card className="mt-4">
        <CardHeader
          title="Mức sử dụng phòng theo từng ngày"
          desc="Ngày nào dùng nhiều chỗ ngồi thì hôm đó áp lực phòng máy cao hơn."
        />
        <div className="mt-4 space-y-3">
          {perDay.map((d) => (
            <div key={d.day}>
              <div className="mb-1.5 flex items-baseline justify-between gap-3">
                <span className="text-[12.5px] font-medium text-ink-700">
                  {weekdayOf(d.day)}, {formatDate(d.day)}
                </span>
                <span className="text-[11.5px] tabular-nums text-ink-400">
                  {d.sessions} ca · {d.seats}/{d.cap} chỗ · {d.load}%
                </span>
              </div>
              <Progress value={d.load} tone={d.load > 90 ? "warning" : "info"} />
            </div>
          ))}
        </div>
      </Card>

      {unscheduledSubjects.length ? (
        <Card className="mt-4" padded={false}>
          <div className="p-5 pb-3">
            <CardHeader
              title="Học phần chưa xếp được"
              desc="Những học phần này không có ca thi trong lịch. Cần xử lý trước khi thông báo cho sinh viên."
              action={<Badge tone="warning">{unscheduledSubjects.length} học phần</Badge>}
            />
          </div>
          <Table>
            <thead>
              <tr>
                <th>Học phần</th>
                <th className="text-center">Sĩ số</th>
                <th>Nguyên nhân có thể &amp; cách xử lý</th>
              </tr>
            </thead>
            <tbody>
              {unscheduledSubjects.map((m) => {
                const subject = SUBJECT_BY_CODE.get(m);
                const list = result.unscheduled.filter((u) => u.maMon === m);
                const eligibleRooms = ROOMS.filter(
                  (r) =>
                    r.tinhTrang === "Working" &&
                    isCompatible(subject?.phanMem ?? [], r.phanMem),
                );
                const seats = eligibleRooms.reduce((a, r) => a + r.sucChua, 0);
                return (
                  <tr key={m}>
                    <td className="whitespace-nowrap align-top">
                      <span className="font-medium text-ink-800">{subject?.tenMon ?? m}</span>
                      <span className="ml-1.5 font-mono text-[11.5px] text-ink-400">{m}</span>
                    </td>
                    <td className="text-center align-top tabular-nums">{list.length}</td>
                    <td className="text-[12.5px] leading-relaxed text-ink-600">
                      <div className="flex items-start gap-2">
                        <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-600" />
                        <span>
                          {unscheduledHint({
                            siSo: list.length,
                            soPhongDuPhanMem: eligibleRooms.length,
                            tongChoDuPhanMem: seats,
                            coPhongNaoDuPhanMem: eligibleRooms.length > 0,
                          })}
                        </span>
                      </div>
                      {list.length ? (
                        <p className="mt-1.5 text-[11.5px] text-ink-400">
                          Sinh viên bị ảnh hưởng: {list.slice(0, 5).map((u) => u.maSv).join(", ")}
                          {list.length > 5 ? ` và ${list.length - 5} em khác` : ""}
                        </p>
                      ) : null}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </Table>
        </Card>
      ) : (
        <Card className="mt-4">
          <div className="flex items-center gap-2.5 text-[12.5px] text-emerald-700">
            <CheckCircle2 className="h-4 w-4" />
            Không học phần nào bị bỏ: cả {SUBJECTS.length} học phần đều đã có ca thi.
          </div>
        </Card>
      )}

      <RosterDrawer
        target={open}
        seats={open ? result.registrations.filter((r) => r.maLich === open.maLich) : undefined}
        students={STUDENT_BY_CODE}
        statuses={statuses}
        onStatusChanged={reloadStatuses}
        onClose={() => setOpen(null)}
      />
    </>
  );
}
