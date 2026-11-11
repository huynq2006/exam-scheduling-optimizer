"use client";

import { useMemo, useState } from "react";
import { CheckCircle2, XCircle, MonitorX } from "lucide-react";
import { useDataset } from "@/lib/dataset";
import type { Enrollment, Room, Slot, Student, Subject } from "@/lib/types";
import { cn, formatDate, isCompatible, slotMinutes, weekdayOf } from "@/lib/utils";
import { hinhThucPlain, roomStatusLabel, softwarePlain } from "@/lib/labels";
import {
  Badge,
  Button,
  Card,
  CardHeader,
  EmptyState,
  Field,
  PageHeader,
  Table,
  inputClass,
  selectClass,
} from "@/components/ui";

const TABS = [
  { id: "subjects", label: "Học phần" },
  { id: "rooms", label: "Phòng máy" },
  { id: "slots", label: "Ngày & ca thi" },
  { id: "enrollment", label: "Đăng ký của sinh viên" },
  { id: "compat", label: "Phòng nào thi được môn nào" },
] as const;

type TabId = (typeof TABS)[number]["id"];

export default function InputsPage() {
  const [tab, setTab] = useState<TabId>("subjects");
  const { subjects: SUBJECTS, rooms: ROOMS, slots: SLOTS, students: STUDENTS, enrollment: ENROLLMENT, loading, error, reload } = useDataset();

  const workingRooms = ROOMS.filter((r) => r.tinhTrang === "Working");
  const examDays = new Set(SLOTS.map((s) => s.ngayThi)).size;

  if (loading) {
    return (
      <>
        <PageHeader eyebrow="Chuẩn bị" title="Dữ liệu dùng để xếp lịch" desc="Đang tải dữ liệu từ cơ sở dữ liệu…" />
        <Card>
          <p className="py-10 text-center text-[13px] text-ink-500">Đang đọc dữ liệu từ MySQL…</p>
        </Card>
      </>
    );
  }

  if (error) {
    return (
      <>
        <PageHeader eyebrow="Chuẩn bị" title="Dữ liệu dùng để xếp lịch" desc="Không đọc được dữ liệu." />
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

  return (
    <>
      <PageHeader
        eyebrow="Chuẩn bị"
        title="Dữ liệu dùng để xếp lịch"
        desc="Trước khi xếp lịch, kiểm tra bốn thứ ở đây: học phần nào phải thi, phòng nào dùng được, ngày nào thi, và sinh viên đăng ký môn gì. Sai ở bước này thì lịch ra cũng sai."
      />

      <div className="mb-4 grid gap-3 sm:grid-cols-4">
        {[
          { label: "Học phần cần thi", value: `${SUBJECTS.length}`, hint: "mỗi học phần một ca" },
          { label: "Phòng dùng được", value: `${workingRooms.length}`, hint: `trên ${ROOMS.length} phòng` },
          { label: "Ngày thi", value: `${examDays}`, hint: "4 ca mỗi ngày" },
          { label: "Lượt đăng ký môn", value: `${ENROLLMENT.length}`, hint: `${STUDENTS.length} sinh viên` },
        ].map((s) => (
          <div key={s.label} className="surface p-3.5">
            <p className="text-[11.5px] text-ink-500">{s.label}</p>
            <p className="mt-1 text-[19px] font-semibold tabular-nums text-ink-900">{s.value}</p>
            <p className="mt-0.5 text-[11px] text-ink-400">{s.hint}</p>
          </div>
        ))}
      </div>

      <div className="mb-4 flex gap-1 overflow-x-auto rounded-lg bg-ink-100 p-1">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={cn(
              "focus-ring whitespace-nowrap rounded-md px-3.5 py-1.5 text-[13px] font-medium transition-colors",
              tab === t.id ? "bg-white text-ink-900 shadow-card" : "text-ink-500 hover:text-ink-800",
            )}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "subjects" ? <SubjectsTab subjects={SUBJECTS} /> : null}
      {tab === "rooms" ? <RoomsTab rooms={ROOMS} /> : null}
      {tab === "slots" ? <SlotsTab slots={SLOTS} subjects={SUBJECTS} /> : null}
      {tab === "enrollment" ? (
        <EnrollmentTab
          subjects={SUBJECTS}
          rooms={ROOMS}
          students={STUDENTS}
          enrollment={ENROLLMENT}
        />
      ) : null}
      {tab === "compat" ? <CompatTab subjects={SUBJECTS} rooms={ROOMS} /> : null}
    </>
  );
}

function SubjectsTab({ subjects: SUBJECTS }: { subjects: Subject[] }) {
  return (
    <Card padded={false}>
      <div className="p-5 pb-4">
        <CardHeader
          title={`${SUBJECTS.length} học phần phải thi`}
          desc="Cột thời lượng cho biết mỗi học phần thi bao nhiêu phút. Học phần dài hơn ca thi thì không xếp vào ca đó được."
        />
      </div>
      <Table>
        <thead>
          <tr>
            <th>Mã</th>
            <th>Học phần</th>
            <th className="text-center">Tín chỉ</th>
            <th className="text-center">Thời lượng thi</th>
            <th>Hình thức thi</th>
            <th>Phần mềm bắt buộc</th>
          </tr>
        </thead>
        <tbody>
          {SUBJECTS.map((s) => (
            <tr key={s.maMon}>
              <td className="font-mono text-[12.5px] text-ink-500">{s.maMon}</td>
              <td className="font-medium text-ink-800">{s.tenMon}</td>
              <td className="text-center tabular-nums">{s.soTinChi}</td>
              <td className="text-center tabular-nums">{s.thoiLuongPhut} phút</td>
              <td className="whitespace-nowrap text-[12.5px]">{hinhThucPlain(s.hinhThuc)}</td>
              <td>
                {s.phanMem.length ? (
                  <div className="flex flex-wrap gap-1">
                    {s.phanMem.map((pm) => (
                      <span
                        key={pm}
                        className="rounded bg-ink-100 px-1.5 py-0.5 text-[11px] text-ink-600"
                      >
                        {pm}
                      </span>
                    ))}
                  </div>
                ) : (
                  <span className="text-[12.5px] text-ink-400">Không cần phần mềm riêng</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </Table>
    </Card>
  );
}

function RoomsTab({ rooms: ROOMS }: { rooms: Room[] }) {
  const [onlyWorking, setOnlyWorking] = useState(true);
  const rows = onlyWorking ? ROOMS.filter((r) => r.tinhTrang === "Working") : ROOMS;

  return (
    <Card padded={false}>
      <div className="flex flex-wrap items-end justify-between gap-3 p-5 pb-4">
        <CardHeader
          title={`${rows.length} phòng máy`}
          desc="Sức chứa là số chỗ ngồi tối đa. Phòng đang bảo trì sẽ không được xếp ca nào."
        />
        <label className="flex cursor-pointer items-center gap-2 text-[12.5px] text-ink-600">
          <input
            type="checkbox"
            checked={onlyWorking}
            onChange={(e) => setOnlyWorking(e.target.checked)}
            className="h-3.5 w-3.5 rounded border-ink-300 text-accent-600 focus:ring-accent-400"
          />
          Chỉ hiện phòng dùng được
        </label>
      </div>
      <Table>
        <thead>
          <tr>
            <th>Phòng</th>
            <th>Vị trí</th>
            <th className="text-center">Sức chứa</th>
            <th>Hệ điều hành</th>
            <th>Tình trạng</th>
            <th>Phần mềm đã cài</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.maPhong}>
              <td>
                <span className="font-medium text-ink-800">{r.maPhong}</span>
                <span className="ml-1.5 text-[12px] text-ink-400">{r.tenPhong}</span>
              </td>
              <td className="whitespace-nowrap text-[12.5px]">
                {r.toaNha}, tầng {r.tang}
              </td>
              <td className="text-center tabular-nums">{r.sucChua} chỗ</td>
              <td className="text-[12.5px]">{r.heDieuHanh}</td>
              <td>
                <Badge tone={r.tinhTrang === "Working" ? "success" : "warning"}>
                  {roomStatusLabel(r.tinhTrang)}
                </Badge>
              </td>
              <td>
                <div className="flex flex-wrap gap-1">
                  {r.phanMem.length ? (
                    r.phanMem.map((pm) => (
                      <span
                        key={pm}
                        className="rounded bg-ink-100 px-1.5 py-0.5 text-[11px] text-ink-600"
                      >
                        {pm}
                      </span>
                    ))
                  ) : (
                    <span className="text-[12.5px] text-ink-400">Chưa cài phần mềm thi</span>
                  )}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </Table>
    </Card>
  );
}

function SlotsTab({ slots: SLOTS, subjects: SUBJECTS }: { slots: Slot[]; subjects: Subject[] }) {
  return (
    <Card padded={false}>
      <div className="p-5 pb-4">
        <CardHeader
          title={`${SLOTS.length} khung giờ thi`}
          desc="Mỗi ngày có 4 ca. Cột cuối cho biết ca đó dài bao lâu và xếp được bao nhiêu học phần."
        />
      </div>
      <Table>
        <thead>
          <tr>
            <th>Ngày thi</th>
            <th className="text-center">Ca</th>
            <th>Bắt đầu</th>
            <th>Kết thúc</th>
            <th className="text-center">Độ dài ca</th>
            <th>Học phần xếp được</th>
          </tr>
        </thead>
        <tbody>
          {SLOTS.map((s) => {
            const len = slotMinutes(s.gioBd, s.gioKt);
            const fit = SUBJECTS.filter((sub) => sub.thoiLuongPhut <= len).length;
            return (
              <tr key={s.maKhung}>
                <td className="whitespace-nowrap text-[12.5px]">
                  <span className="font-medium text-ink-800">
                    {weekdayOf(s.ngayThi)}, {formatDate(s.ngayThi)}
                  </span>
                </td>
                <td className="text-center tabular-nums">{s.caThi}</td>
                <td className="tabular-nums text-[12.5px]">{s.gioBd}</td>
                <td className="tabular-nums text-[12.5px]">{s.gioKt}</td>
                <td className="text-center tabular-nums text-[12.5px]">{len} phút</td>
                <td className="text-[12.5px] text-ink-500">
                  {fit}/{SUBJECTS.length} học phần
                </td>
              </tr>
            );
          })}
        </tbody>
      </Table>
    </Card>
  );
}

function EnrollmentTab({
  subjects: SUBJECTS,
  rooms: ROOMS,
  students: STUDENTS,
  enrollment: ENROLLMENT,
}: {
  subjects: Subject[];
  rooms: Room[];
  students: Student[];
  enrollment: Enrollment[];
}) {
  const [keyword, setKeyword] = useState("");

  const perSubject = useMemo(() => {
    const map = new Map<string, number>();
    for (const row of ENROLLMENT) map.set(row.maMon, (map.get(row.maMon) ?? 0) + 1);
    return map;
  }, []);

  const rows = useMemo(() => {
    const kw = keyword.trim().toLowerCase();
    if (!kw) return [];
    // Gộp theo sinh viên: một em đăng ký nhiều môn thì chỉ hiện một dòng.
    const seen = new Set<string>();
    const out: Enrollment[] = [];
    for (const e of ENROLLMENT) {
      if (!e.maSv.toLowerCase().includes(kw)) continue;
      if (seen.has(e.maSv)) continue;
      seen.add(e.maSv);
      out.push(e);
      if (out.length >= 40) break;
    }
    return out;
  }, [keyword, ENROLLMENT]);

  return (
    <div className="space-y-4">
      <Card padded={false}>
        <div className="p-5 pb-4">
          <CardHeader
            title="Sĩ số từng học phần"
            desc="Số sinh viên đăng ký mỗi học phần. Đây là con số quyết định cần bao nhiêu chỗ ngồi. Dòng đỏ là học phần có ít chỗ thi hơn sĩ số."
          />
        </div>
        <Table>
          <thead>
            <tr>
              <th>Mã</th>
              <th>Học phần</th>
              <th className="text-center">Sĩ số</th>
              <th className="text-center">Thời lượng</th>
              <th>Phòng đủ điều kiện</th>
            </tr>
          </thead>
          <tbody>
            {SUBJECTS.map((s) => {
              const n = perSubject.get(s.maMon) ?? 0;
              const eligible = ROOMS.filter(
                (r) => r.tinhTrang === "Working" && isCompatible(s.phanMem, r.phanMem),
              );
              const seats = eligible.reduce((a, r) => a + r.sucChua, 0);
              const short = seats < n;
              return (
                <tr key={s.maMon}>
                  <td className="font-mono text-[12.5px] text-ink-500">{s.maMon}</td>
                  <td className="font-medium text-ink-800">{s.tenMon}</td>
                  <td className="text-center tabular-nums">{n}</td>
                  <td className="text-center tabular-nums">{s.thoiLuongPhut} phút</td>
                  <td>
                    <span
                      className={cn(
                        "tabular-nums text-[12.5px]",
                        short ? "font-medium text-rose-600" : "text-ink-700",
                      )}
                    >
                      {eligible.length} phòng · {seats} chỗ
                    </span>
                    {short ? (
                      <span className="ml-1.5 text-[11.5px] text-rose-600">
                        thiếu {n - seats} chỗ
                      </span>
                    ) : null}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </Table>
      </Card>

      <Card padded={false}>
        <div className="p-5 pb-4">
          <CardHeader
            title={`${STUDENTS.length} sinh viên · ${ENROLLMENT.length} lượt đăng ký`}
            desc="Mỗi sinh viên đăng ký 3–5 học phần. Tra theo mã số sinh viên để xem một em thi những môn nào."
          />
          <Field label="Tra theo mã số sinh viên" className="mt-4 max-w-sm">
            <input
              className={inputClass}
              placeholder="Ví dụ: SV20210002"
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
            />
          </Field>
        </div>
        {rows.length ? (
          <Table>
            <thead>
              <tr>
                <th>Mã số sinh viên</th>
                <th>Họ tên</th>
                <th>Lớp</th>
                <th>Học phần đã đăng ký</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => {
                const stu = STUDENTS.find((s) => s.maSv === r.maSv);
                const mon = ENROLLMENT.filter((e) => e.maSv === r.maSv).map((e) => e.maMon);
                return (
                  <tr key={r.maSv}>
                    <td className="font-mono text-[12.5px] text-ink-500">{r.maSv}</td>
                    <td className="font-medium text-ink-800">{stu?.hoTen ?? "—"}</td>
                    <td className="text-[12.5px]">{stu?.lop ?? "—"}</td>
                    <td>
                      <div className="flex flex-wrap gap-1">
                        {mon.map((m) => (
                          <span
                            key={m}
                            className="rounded bg-ink-100 px-1.5 py-0.5 text-[11px] text-ink-600"
                          >
                            {m}
                          </span>
                        ))}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </Table>
        ) : (
          <EmptyState
            title={keyword.trim() ? "Không tìm thấy sinh viên này" : "Nhập mã số sinh viên để tra cứu"}
            desc="Bảng sĩ số từng học phần ở trên đã có đủ số liệu tổng hợp."
          />
        )}
      </Card>
    </div>
  );
}

function CompatTab({ subjects: SUBJECTS, rooms: ROOMS }: { subjects: Subject[]; rooms: Room[] }) {
  const working = ROOMS.filter((r) => r.tinhTrang === "Working");
  return (
    <Card padded={false}>
      <div className="p-5 pb-4">
        <CardHeader
          title="Phòng nào thi được môn nào"
          desc="Dấu tích nghĩa là phòng đó cài đủ phần mềm mà học phần yêu cầu, nên xếp ca thi vào được. Dấu gạch là không xếp được."
        />
      </div>
      <div className="overflow-x-auto">
        <table className="table-base">
          <thead>
            <tr>
              <th className="sticky left-0 bg-white">Học phần \\ Phòng</th>
              {working.map((r) => (
                <th key={r.maPhong} className="whitespace-nowrap text-center">
                  {r.maPhong}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {SUBJECTS.map((s) => (
              <tr key={s.maMon}>
                <td className="sticky left-0 whitespace-nowrap bg-white">
                  <span className="font-medium text-ink-800">{s.tenMon}</span>
                  <span className="ml-1.5 font-mono text-[11.5px] text-ink-400">{s.maMon}</span>
                </td>
                {working.map((r) => {
                  const ok = isCompatible(s.phanMem, r.phanMem);
                  return (
                    <td key={r.maPhong} className="text-center">
                      {ok ? (
                        <CheckCircle2 className="mx-auto h-3.5 w-3.5 text-emerald-500" />
                      ) : (
                        <XCircle className="mx-auto h-3.5 w-3.5 text-ink-200" />
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex items-start gap-2 border-t border-ink-100 px-5 py-3 text-[11.5px] leading-relaxed text-ink-400">
        <MonitorX className="mt-0.5 h-3.5 w-3.5 shrink-0" />
        <span>
          Phòng đang bảo trì không xuất hiện ở bảng này vì không xếp được ca nào. Học phần không yêu
          cầu phần mềm riêng thì thi được ở mọi phòng đang dùng.
        </span>
      </div>
    </Card>
  );
}
