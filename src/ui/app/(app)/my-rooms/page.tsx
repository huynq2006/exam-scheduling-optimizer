"use client";

import { useMemo } from "react";
import { Building2, CalendarX2, MonitorCog, Package } from "lucide-react";
import { useApp } from "@/lib/store";
import { useStudentSchedule } from "@/lib/student";
import { formatDate, weekdayOf } from "@/lib/utils";
import { caWithTime, softwarePlain } from "@/lib/labels";
import {
  Badge,
  Button,
  Card,
  CardHeader,
  EmptyState,
  PageHeader,
  Table,
} from "@/components/ui";

interface RoomGroup {
  maPhong: string;
  tenPhong: string;
  toaNha: string;
  tang: number;
  sucChua: number;
  heDieuHanh: string;
  phanMem: string[];
  exams: {
    maLich: number;
    maMon: string;
    tenMon: string;
    ngayThi: string;
    caThi: number;
    gioBd: string;
    gioKt: string;
    soMay: number;
  }[];
}

export default function MyRoomsPage() {
  const { user } = useApp();
  const { data, loading, error, reload } = useStudentSchedule(user?.maSv);

  const groups = useMemo<RoomGroup[]>(() => {
    const exams = data?.exams ?? [];
    const map = new Map<string, RoomGroup>();

    for (const e of exams) {
      let g = map.get(e.maPhong);
      if (!g) {
        g = {
          maPhong: e.maPhong,
          tenPhong: e.tenPhong,
          toaNha: e.toaNha,
          tang: e.tang,
          sucChua: e.sucChua,
          heDieuHanh: e.heDieuHanh,
          phanMem: e.phanMemPhong,
          exams: [],
        };
        map.set(e.maPhong, g);
      }
      g.exams.push({
        maLich: e.maLich,
        maMon: e.maMon,
        tenMon: e.tenMon,
        ngayThi: e.ngayThi,
        caThi: e.caThi,
        gioBd: e.gioBd,
        gioKt: e.gioKt,
        soMay: e.soMay,
      });
    }

    return Array.from(map.values())
      .map((g) => ({
        ...g,
        exams: g.exams.sort(
          (a, b) => a.ngayThi.localeCompare(b.ngayThi) || a.caThi - b.caThi,
        ),
      }))
      .sort((a, b) => a.maPhong.localeCompare(b.maPhong));
  }, [data]);

  if (loading) {
    return (
      <>
        <PageHeader eyebrow="Tra cứu" title="Phòng máy của tôi" desc="Đang tải danh sách phòng…" />
        <Card>
          <p className="py-10 text-center text-[13px] text-ink-500">Đang đọc dữ liệu từ MySQL…</p>
        </Card>
      </>
    );
  }

  if (error) {
    return (
      <>
        <PageHeader eyebrow="Tra cứu" title="Phòng máy của tôi" desc="Không đọc được dữ liệu." />
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

  if (!groups.length) {
    return (
      <>
        <PageHeader
          eyebrow="Tra cứu"
          title="Phòng máy của tôi"
          desc={data ? `${data.student.hoTen} · Lớp ${data.student.lop}` : undefined}
        />
        <Card>
          <EmptyState
            title="Chưa có phòng thi nào"
            desc="Phòng máy sẽ hiện ở đây khi lịch thi của bạn được công bố."
            icon={<CalendarX2 className="h-6 w-6" />}
          />
        </Card>
      </>
    );
  }

  return (
    <>
      <PageHeader
        eyebrow="Tra cứu"
        title="Phòng máy của tôi"
        desc="Bạn thi ở những phòng nào, phòng nằm ở đâu, máy cài sẵn phần mềm gì và bạn ngồi máy số mấy."
      />

      <div className="space-y-4">
        {groups.map((g) => (
          <Card key={g.maPhong} padded={false}>
            <div className="flex flex-wrap items-start justify-between gap-3 p-5 pb-3">
              <div className="flex items-start gap-3">
                <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-accent-50 text-accent-600">
                  <MonitorCog className="h-4 w-4" />
                </span>
                <div>
                  <h2 className="text-[15px] font-semibold tracking-tight text-ink-900">
                    {g.maPhong}
                    <span className="ml-2 text-[12.5px] font-normal text-ink-400">{g.tenPhong}</span>
                  </h2>
                  <p className="mt-0.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-[12px] text-ink-500">
                    <span className="inline-flex items-center gap-1">
                      <Building2 className="h-3.5 w-3.5 text-ink-300" />
                      Nhà {g.toaNha}, tầng {g.tang}
                    </span>
                    <span>{g.sucChua} máy</span>
                    <span>{g.heDieuHanh}</span>
                  </p>
                </div>
              </div>
              <Badge tone="neutral">{g.exams.length} ca thi</Badge>
            </div>

            <div className="px-5 pb-3">
              <p className="flex items-start gap-1.5 text-[12px] leading-relaxed text-ink-500">
                <Package className="mt-0.5 h-3.5 w-3.5 shrink-0 text-ink-300" />
                <span>Phần mềm có sẵn trên máy: {softwarePlain(g.phanMem)}</span>
              </p>
            </div>

            <Table>
              <thead>
                <tr>
                  <th>Ngày &amp; ca thi</th>
                  <th>Học phần</th>
                  <th className="text-center">Máy số</th>
                </tr>
              </thead>
              <tbody>
                {g.exams.map((e) => (
                  <tr key={e.maLich}>
                    <td className="whitespace-nowrap">
                      <span className="font-medium text-ink-800">
                        {weekdayOf(e.ngayThi)}, {formatDate(e.ngayThi)}
                      </span>
                      <span className="ml-1.5 text-[11.5px] text-ink-400">
                        {caWithTime(e.caThi, e.gioBd, e.gioKt)}
                      </span>
                    </td>
                    <td className="whitespace-nowrap">
                      <span className="font-medium text-ink-800">{e.tenMon}</span>
                      <span className="ml-1.5 font-mono text-[11.5px] text-ink-400">{e.maMon}</span>
                    </td>
                    <td className="text-center tabular-nums">
                      <Badge tone="info">{e.soMay}</Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </Card>
        ))}
      </div>

      <Card className="mt-4">
        <CardHeader
          title="Trước khi vào thi"
          desc="Có mặt trước giờ bắt đầu 15 phút. Ngồi đúng số máy đã ghi ở trên. Nếu máy hỏng, báo giám thị ngay, đừng tự đổi máy."
        />
      </Card>
    </>
  );
}
