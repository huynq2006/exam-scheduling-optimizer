"use client";

import { Fragment, useCallback, useEffect, useMemo, useState } from "react";
import { Download, Search, Users, X } from "lucide-react";
import { useDataset } from "@/lib/dataset";
import { useAllStatuses, useStatusMutations } from "@/lib/exam-status";
import { cn } from "@/lib/utils";
import { rowToneClass } from "@/lib/labels";
import type { ExamStatus } from "@/lib/types";
import { StatusPill } from "@/components/status-ui";
import {
  Badge,
  Button,
  Card,
  CardHeader,
  EmptyState,
  Field,
  PageHeader,
  Stat,
  Table,
  Tabs,
  inputClass,
  selectClass,
} from "@/components/ui";

type TabId = "all" | "no-fee" | "banned";

const TABS: Array<{ id: TabId; label: string; desc: string; status?: ExamStatus }> = [
  {
    id: "all",
    label: "Tất cả sinh viên",
    desc: "Tra theo mã sinh viên, họ tên, lớp hoặc học phần.",
  },
  {
    id: "no-fee",
    label: "Chưa nộp học phí",
    desc: "Sinh viên chưa nộp học phí.",
    status: "CHUA_NOP_HOC_PHI",
  },
  {
    id: "banned",
    label: "Bị cấm thi",
    desc: "Sinh viên bị cấm thi.",
    status: "CAM_THI",
  },
];

interface StudentRow {
  maSv: string;
  hoTen: string;
  lop: string;
  khoa: string;
  email: string;
  soMonDangKy: number;
  trangThai: ExamStatus | null;
  lyDo: string | null;
  monBiAnhHuong: string[];
}

export default function QueryPage() {
  const { subjects } = useDataset();
  const { statuses, reload: reloadStatuses } = useAllStatuses();
  const { busy, error: mutateError, setStatus, clearStatus } = useStatusMutations(reloadStatuses);

  const [tab, setTab] = useState<TabId>("all");
  const [keyword, setKeyword] = useState("");
  const [maMon, setMaMon] = useState("");
  const [lop, setLop] = useState("");
  const [editing, setEditing] = useState<string | null>(null);

  const [rows, setRows] = useState<StudentRow[]>([]);
  const [classes, setClasses] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const activeTab = TABS.find((t) => t.id === tab)!;

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const qs = new URLSearchParams();
      if (keyword.trim()) qs.set("q", keyword.trim());
      if (maMon) qs.set("maMon", maMon);
      if (lop) qs.set("lop", lop);
      if (activeTab.status) qs.set("trangThai", activeTab.status);

      const res = await fetch(`/api/students?${qs.toString()}`, { cache: "no-store" });
      const body = await res.json();
      if (!res.ok) throw new Error(body?.detail ?? body?.error ?? `Lỗi ${res.status}`);
      setRows(body.students ?? []);
      setClasses(body.classes ?? []);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }, [keyword, maMon, lop, activeTab.status]);

  // Đổi tab thì tra ngay; gõ từ khoá thì chờ một nhịp cho khỏi bắn request mỗi phím.
  useEffect(() => {
    const t = setTimeout(load, keyword ? 300 : 0);
    return () => clearTimeout(t);
  }, [load, keyword]);

  const counts = useMemo(
    () => ({
      camThi: statuses.filter((s) => s.trangThai === "CAM_THI").length,
      chuaNop: statuses.filter((s) => s.trangThai === "CHUA_NOP_HOC_PHI").length,
    }),
    [statuses],
  );

  function exportCsv() {
    const header = "ma_sv,ho_ten,lop,khoa,so_mon,trang_thai,ly_do";
    const lines = rows.map((r) =>
      [
        r.maSv,
        `"${r.hoTen.replace(/"/g, '""')}"`,
        r.lop,
        `"${r.khoa.replace(/"/g, '""')}"`,
        r.soMonDangKy,
        r.trangThai ?? "BINH_THUONG",
        `"${(r.lyDo ?? "").replace(/"/g, '""')}"`,
      ].join(","),
    );
    const blob = new Blob([`\uFEFF${[header, ...lines].join("\n")}`], {
      type: "text/csv;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `truy-van-${tab}-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  async function toggleStatus(row: StudentRow, next: ExamStatus | null) {
    if (next) {
      await setStatus({ maSv: row.maSv, maMon: null, trangThai: next, lyDo: row.lyDo });
    } else {
      await clearStatus(row.maSv, null);
    }
    void load();
  }

  const hasFilter = keyword.trim() || maMon || lop;

  return (
    <>
      <PageHeader
        eyebrow="Tra cứu"
        title="Truy vấn sinh viên"
        desc="Tra sinh viên theo mã, họ tên, lớp hoặc học phần."
        action={
          <Button variant="secondary" onClick={exportCsv} disabled={!rows.length}>
            <Download className="h-4 w-4" />
            Xuất CSV
          </Button>
        }
      />

      <div className="grid gap-3 sm:grid-cols-3">
        <Stat label="Kết quả truy vấn" value={`${rows.length}`} hint={activeTab.label} />
        <Stat
          label="Cấm thi hẳn"
          value={`${counts.camThi}`}
          hint="Toàn hệ thống"
          tone={counts.camThi ? "danger" : "success"}
        />
        <Stat
          label="Chưa nộp học phí"
          value={`${counts.chuaNop}`}
          hint="Toàn hệ thống"
          tone={counts.chuaNop ? "warning" : "success"}
        />
      </div>

      <Tabs
        className="mt-4"
        value={tab}
        onChange={setTab}
        items={TABS.map((t) => ({
          id: t.id,
          label: t.label,
          count:
            t.id === "no-fee" ? counts.chuaNop : t.id === "banned" ? counts.camThi : undefined,
        }))}
      />

      <Card className="mt-3">
        <div className="grid gap-3 sm:grid-cols-[1.5fr_1fr_1fr]">
          <Field label="Từ khoá" hint="Mã sinh viên, họ tên, lớp, hoặc tên học phần">
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-ink-300" />
              <input
                className={cn(inputClass, "pl-8")}
                placeholder="Ví dụ: SV20210002, Nguyễn, INT101"
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
              />
            </div>
          </Field>
          <Field label="Học phần">
            <select className={selectClass} value={maMon} onChange={(e) => setMaMon(e.target.value)}>
              <option value="">Tất cả học phần</option>
              {subjects.map((s) => (
                <option key={s.maMon} value={s.maMon}>
                  {s.maMon} · {s.tenMon}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Lớp">
            <select className={selectClass} value={lop} onChange={(e) => setLop(e.target.value)}>
              <option value="">Tất cả lớp</option>
              {classes.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </Field>
        </div>
        {hasFilter ? (
          <div className="mt-2 flex justify-end">
            <Button
              size="sm"
              variant="ghost"
              onClick={() => {
                setKeyword("");
                setMaMon("");
                setLop("");
              }}
            >
              <X className="h-3.5 w-3.5" />
              Xoá bộ lọc
            </Button>
          </div>
        ) : null}
      </Card>

      {mutateError ? (
        <p className="mt-3 rounded-lg bg-rose-50 px-3 py-2 text-[12.5px] text-rose-700 ring-1 ring-inset ring-rose-200">
          {mutateError}
        </p>
      ) : null}

      <Card className="mt-4" padded={false}>
        <div className="p-5 pb-3">
          <CardHeader
            title={`${rows.length} sinh viên`}
            desc="Đổi trạng thái ngay trong bảng nếu cần."
            action={<Badge tone="neutral">{activeTab.label}</Badge>}
          />
        </div>

        {loading ? (
          <p className="py-12 text-center text-[13px] text-ink-500">Đang truy vấn…</p>
        ) : error ? (
          <div className="py-10 text-center">
            <p className="text-[13px] font-medium text-rose-700">Không truy vấn được</p>
            <p className="mx-auto mt-1.5 max-w-md text-[12px] text-ink-500">{error}</p>
            <Button variant="secondary" size="sm" className="mt-3" onClick={load}>
              Thử lại
            </Button>
          </div>
        ) : rows.length ? (
          <Table>
            <thead>
              <tr>
                <th>Mã SV</th>
                <th>Họ tên</th>
                <th>Lớp</th>
                <th>Khoa</th>
                <th className="text-center">Số môn</th>
                <th>Trạng thái</th>
                <th>Ghi chú</th>
                <th className="w-16 text-right" />
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <Fragment key={r.maSv}>
                  <tr className={rowToneClass(r.trangThai)}>
                    <td className="whitespace-nowrap font-mono text-[12px] text-ink-600">{r.maSv}</td>
                    <td className="whitespace-nowrap font-medium text-ink-800">{r.hoTen}</td>
                    <td className="whitespace-nowrap text-[12.5px] text-ink-600">{r.lop}</td>
                    <td className="whitespace-nowrap text-[12.5px] text-ink-500">{r.khoa}</td>
                    <td className="text-center tabular-nums text-[12.5px]">{r.soMonDangKy}</td>
                    <td className="whitespace-nowrap">
                      <StatusPill trangThai={r.trangThai} />
                    </td>
                    <td className="max-w-[220px]">
                      <span className="block truncate text-[12px] text-ink-500" title={r.lyDo ?? ""}>
                        {r.lyDo ?? "—"}
                      </span>
                      {r.monBiAnhHuong.length ? (
                        <span className="mt-0.5 block truncate text-[11px] text-ink-400">
                          Cấm môn: {r.monBiAnhHuong.join(", ")}
                        </span>
                      ) : null}
                    </td>
                    <td className="text-right">
                      <Button
                        size="sm"
                        variant="ghost"
                        disabled={busy}
                        onClick={() => setEditing(editing === r.maSv ? null : r.maSv)}
                      >
                        {editing === r.maSv ? "Đóng" : "Sửa"}
                      </Button>
                    </td>
                  </tr>
                  {editing === r.maSv ? (
                    <tr>
                      <td colSpan={8} className="bg-ink-50/70">
                        <div className="flex flex-wrap items-end gap-2">
                          <Field label="Trạng thái" className="w-52">
                            <select
                              className={cn(selectClass, "text-[13px]")}
                              defaultValue={r.trangThai ?? ""}
                              disabled={busy}
                              onChange={(e) =>
                                toggleStatus(r, (e.target.value || null) as ExamStatus | null)
                              }
                              aria-label={`Đổi trạng thái ${r.maSv}`}
                            >
                              <option value="">Bình thường</option>
                              <option value="CHUA_NOP_HOC_PHI">Chưa nộp học phí</option>
                              <option value="CAM_THI">Cấm thi</option>
                            </select>
                          </Field>
                          <p className="pb-2 text-[11.5px] text-ink-400">
                            Chọn xong là lưu ngay.
                          </p>
                        </div>
                      </td>
                    </tr>
                  ) : null}
                </Fragment>
              ))}
            </tbody>
          </Table>
        ) : (
          <EmptyState
            title={hasFilter ? "Không tìm thấy sinh viên nào" : "Chưa có dữ liệu"}
            desc={
              hasFilter
                ? "Thử bỏ bớt bộ lọc, hoặc kiểm tra lại mã sinh viên."
                : "Chưa có sinh viên nào trong nhóm này."
            }
            icon={<Users className="h-6 w-6" />}
          />
        )}
      </Card>
    </>
  );
}
