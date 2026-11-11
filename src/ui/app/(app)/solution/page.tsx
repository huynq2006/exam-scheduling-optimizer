"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { AlertTriangle, CalendarX2, CheckCircle2, Filter, Play, X } from "lucide-react";
import { useApp } from "@/lib/store";
import { useDataset } from "@/lib/dataset";
import { cn, formatDate, percent, weekdayOf, isCompatible } from "@/lib/utils";
import { caWithTime, roomStatusLabel, statusOf, unscheduledHint } from "@/lib/labels";
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
  const { subjects: SUBJECTS, rooms: ROOMS, slots: SLOTS, loading, error, reload } = useDataset();
  const [day, setDay] = useState("all");
  const [mon, setMon] = useState("all");

  const ROOM_BY_CODE = useMemo(() => new Map(ROOMS.map((r) => [r.maPhong, r])), [ROOMS]);
  const SLOT_BY_CODE = useMemo(() => new Map(SLOTS.map((s) => [s.maKhung, s])), [SLOTS]);
  const SUBJECT_BY_CODE = useMemo(() => new Map(SUBJECTS.map((s) => [s.maMon, s])), [SUBJECTS]);

  const rows = useMemo(() => {
    if (!result) return [];
    return result.sessions
      .map((s) => {
        const slot = SLOT_BY_CODE.get(s.maKhung);
        const room = ROOM_BY_CODE.get(s.maPhong);
        const subject = SUBJECT_BY_CODE.get(s.maMon);
        const seats = result.registrations.filter((r) => r.maLich === s.maLich).length;
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
          soSv: seats,
        };
      })
      .filter((s) => (day === "all" || s.ngayThi === day) && (mon === "all" || s.maMon === mon))
      .sort(
        (a, b) =>
          a.ngayThi.localeCompare(b.ngayThi) ||
          a.caThi - b.caThi ||
          a.maPhong.localeCompare(b.maPhong),
      );
  }, [result, day, mon, ROOM_BY_CODE, SLOT_BY_CODE, SUBJECT_BY_CODE]);

  if (loading) {
    return (
      <>
        <PageHeader eyebrow="Xếp lịch" title="Lịch thi đã xếp" desc="Đang tải dữ liệu từ cơ sở dữ liệu…" />
        <Card>
          <p className="py-10 text-center text-[13px] text-ink-500">Đang đọc dữ liệu từ MySQL…</p>
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
          desc="Trang này hiện lịch sau khi hệ thống xếp xong."
        />
        <Card>
          <EmptyState
            title="Chưa có lịch thi nào"
            desc="Bấm xếp lịch trước, lịch thi sẽ hiện ở đây."
            icon={<Play className="h-6 w-6" />}
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
        desc="Mỗi dòng là một ca thi: ngày nào, ca mấy, học phần nào, phòng nào, bao nhiêu sinh viên. Đây là lịch dùng để thông báo cho các khoa."
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
          label="Mức sử dụng chỗ ngồi"
          value={`${percent(totalSeats, totalCapacity)}%`}
          hint={`${totalSeats}/${totalCapacity} chỗ`}
          tone="info"
        />
        <Stat
          label="Học phần chưa xếp được"
          value={`${unscheduledSubjects.length}`}
          hint={
            unscheduledSubjects.length
              ? `${result.unscheduled.length} lượt sinh viên bị ảnh hưởng`
              : "Không học phần nào bị bỏ"
          }
          tone={unscheduledSubjects.length ? "warning" : "success"}
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
          <div className="flex items-center gap-2 pb-0.5">
            <span className="inline-flex items-center gap-1.5 text-[12.5px] text-ink-500">
              <Filter className="h-3.5 w-3.5" />
              {rows.length}/{result.sessions.length} ca
            </span>
            {day !== "all" || mon !== "all" ? (
              <Button
                size="sm"
                variant="ghost"
                onClick={() => {
                  setDay("all");
                  setMon("all");
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
                <th className="text-center">Chỗ còn trống</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((s) => {
                const free = s.sucChua - s.soSv;
                return (
                  <tr key={s.maLich}>
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
                    </td>
                    <td className="text-center">
                      <Badge tone={free > 0 ? "muted" : "success"}>{free}</Badge>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </Table>
        ) : (
          <EmptyState
            title="Không có ca thi nào khớp bộ lọc"
            desc="Thử chọn ngày khác hoặc bỏ lọc học phần."
            icon={<Filter className="h-6 w-6" />}
          />
        )}
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
              desc="Những học phần này không có ca thi trong lịch. Cần xử lý trước khi thông báo lịch cho sinh viên."
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
            Không học phần nào bị bỏ: toàn bộ {SUBJECTS.length} học phần đều đã có ca thi.
          </div>
        </Card>
      )}

      <Card className="mt-4">
        <div className="flex items-start gap-2.5 text-[12.5px] leading-relaxed text-ink-500">
          <CalendarX2 className="mt-0.5 h-4 w-4 shrink-0 text-ink-300" />
          <span>
            Lịch này đã thoả các điều kiện bắt buộc: mỗi phòng chỉ một ca mỗi khung giờ, mỗi sinh
            viên không thi hai môn cùng lúc, phòng được dùng đã cài đủ phần mềm mà môn thi yêu cầu.
          </span>
        </div>
      </Card>
    </>
  );
}
