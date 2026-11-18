"use client";

import { useMemo, useState } from "react";
import { AlertTriangle, CheckCircle2, Search, UserCheck, Users } from "lucide-react";
import { useRoster, useStatusMutations } from "@/lib/exam-status";
import { examStatusOf, rowToneClass } from "@/lib/labels";
import { cn } from "@/lib/utils";
import type { ExamStatus, RosterEntry } from "@/lib/types";
import { Badge, Button, EmptyState, Field, Table, inputClass, selectClass } from "./ui";
import { Drawer, StatusPill } from "./status-ui";

type Filter = "all" | "CAM_THI" | "CHUA_NOP_HOC_PHI" | "BINH_THUONG";

const FILTERS: Array<{ id: Filter; label: string }> = [
  { id: "all", label: "Tất cả" },
  { id: "CAM_THI", label: "Cấm thi" },
  { id: "CHUA_NOP_HOC_PHI", label: "Chưa nộp học phí" },
  { id: "BINH_THUONG", label: "Bình thường" },
];

export interface RosterTarget {
  maLich: number;
  tenMon: string;
  maMon: string;
  ngayThi: string;
  caThi: number;
  gioBd: string;
  gioKt: string;
  maPhong: string;
  toaNha: string;
  tang: number;
  sucChua: number;
}

/**
 * Bảng danh sách sinh viên của một ca thi.
 *
 * Nguyên tắc nghiệp vụ: cấm thi là ĐÁNH DẤU, không phải xoá. Sinh viên bị
 * cấm vẫn hiện trong danh sách, chỉ khác màu và có ghi chú — giám thị cần
 * đủ danh sách để đối chiếu, và sinh viên nộp học phí xong thì chỉ cần bỏ
 * đánh dấu, không phải xếp lại ca.
 */
export function RosterDrawer({
  target,
  onClose,
}: {
  target: RosterTarget | null;
  onClose: () => void;
}) {
  const maLich = target?.maLich ?? null;
  const { data, loading, error, reload } = useRoster(maLich);
  const { busy, error: mutateError, setStatus, clearStatus } = useStatusMutations(reload);

  const [filter, setFilter] = useState<Filter>("all");
  const [keyword, setKeyword] = useState("");
  const [editing, setEditing] = useState<RosterEntry | null>(null);

  const roster = data?.roster ?? [];

  const counts = useMemo(
    () => ({
      all: roster.length,
      CAM_THI: roster.filter((r) => r.trangThai === "CAM_THI").length,
      CHUA_NOP_HOC_PHI: roster.filter((r) => r.trangThai === "CHUA_NOP_HOC_PHI").length,
      BINH_THUONG: roster.filter((r) => !r.trangThai).length,
    }),
    [roster],
  );

  const rows = useMemo(() => {
    const kw = keyword.trim().toLowerCase();
    return roster.filter((r) => {
      if (filter === "BINH_THUONG" && r.trangThai) return false;
      if (filter !== "all" && filter !== "BINH_THUONG" && r.trangThai !== filter) return false;
      if (!kw) return true;
      return (
        r.maSv.toLowerCase().includes(kw) ||
        r.hoTen.toLowerCase().includes(kw) ||
        r.lop.toLowerCase().includes(kw)
      );
    });
  }, [roster, filter, keyword]);

  if (!target) return null;

  async function applyStatus(
    entry: RosterEntry,
    trangThai: ExamStatus | null,
    lyDo: string | null,
  ) {
    const ok = trangThai
      ? await setStatus({
          maSv: entry.maSv,
          maMon: null,
          trangThai,
          lyDo,
        })
      : await clearStatus(entry.maSv, null);
    if (ok) setEditing(null);
  }

  return (
    <Drawer
      open
      onClose={onClose}
      width="max-w-3xl"
      title={
        <span className="flex flex-wrap items-center gap-2">
          {target.tenMon}
          <span className="font-mono text-[12px] font-normal text-ink-400">{target.maMon}</span>
        </span>
      }
      subtitle={
        <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <span>
            Ca {target.caThi} · {target.gioBd}–{target.gioKt}
          </span>
          <span className="text-ink-300">·</span>
          <span>
            Phòng {target.maPhong} ({target.toaNha}, tầng {target.tang})
          </span>
          <span className="text-ink-300">·</span>
          <span>
            {roster.length}/{target.sucChua} chỗ
          </span>
        </span>
      }
      footer={
        <div className="flex flex-wrap items-center justify-between gap-2 text-[11.5px] text-ink-500">
          <span className="tabular-nums">
            {counts.CAM_THI} cấm thi · {counts.CHUA_NOP_HOC_PHI} chưa nộp HP
          </span>
          <span className="text-ink-400">{roster.length} sinh viên</span>
        </div>
      }
    >
      <div className="border-b border-ink-100 px-5 py-3">
        <div className="flex flex-wrap items-center gap-1">
          {FILTERS.map((f) => (
            <button
              key={f.id}
              onClick={() => setFilter(f.id)}
              className={cn(
                "focus-ring rounded-md px-2.5 py-1 text-[12.5px] font-medium transition-colors",
                filter === f.id
                  ? "bg-ink-900 text-white"
                  : "text-ink-500 hover:bg-ink-100 hover:text-ink-800",
              )}
            >
              {f.label}
              <span
                className={cn(
                  "ml-1.5 tabular-nums",
                  filter === f.id ? "text-white/70" : "text-ink-400",
                )}
              >
                {counts[f.id]}
              </span>
            </button>
          ))}
        </div>

        <div className="relative mt-2.5">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-ink-300" />
          <input
            className={cn(inputClass, "pl-8 text-[13px]")}
            placeholder="Lọc trong ca này theo mã sinh viên, họ tên hoặc lớp"
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
          />
        </div>
      </div>

      {mutateError ? (
        <p className="mx-5 mt-3 rounded-lg bg-rose-50 px-3 py-2 text-[12.5px] text-rose-700 ring-1 ring-inset ring-rose-200">
          {mutateError}
        </p>
      ) : null}

      {loading ? (
        <p className="py-12 text-center text-[13px] text-ink-500">Đang đọc danh sách…</p>
      ) : error ? (
        <div className="py-10 text-center">
          <p className="text-[13px] font-medium text-rose-700">Không đọc được danh sách</p>
          <p className="mx-auto mt-1.5 max-w-md text-[12px] text-ink-500">{error}</p>
          <Button variant="secondary" size="sm" className="mt-3" onClick={reload}>
            Thử lại
          </Button>
        </div>
      ) : rows.length ? (
        <Table>
          <thead>
            <tr>
              <th className="w-14 text-center">Máy</th>
              <th>Mã SV</th>
              <th>Họ tên</th>
              <th>Lớp</th>
              <th>Trạng thái</th>
              <th className="text-right">Thao tác</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const meta = examStatusOf(r.trangThai);
              return (
                <tr key={r.maSv} className={cn("group", rowToneClass(r.trangThai))}>
                  <td className="text-center tabular-nums text-[12.5px] text-ink-500">{r.soMay}</td>
                  <td className="whitespace-nowrap font-mono text-[12px] text-ink-600">{r.maSv}</td>
                  <td className="whitespace-nowrap font-medium text-ink-800">{r.hoTen}</td>
                  <td className="whitespace-nowrap text-[12.5px] text-ink-600">{r.lop}</td>
                  <td className="whitespace-nowrap">
                    <StatusPill trangThai={r.trangThai} />
                    {r.lyDo ? (
                      <p className="mt-0.5 max-w-[220px] truncate text-[11px] text-ink-400" title={r.lyDo}>
                        {r.lyDo}
                      </p>
                    ) : null}
                  </td>
                  <td className="whitespace-nowrap text-right">
                    <button
                      onClick={() => setEditing(editing?.maSv === r.maSv ? null : r)}
                      disabled={busy}
                      className={cn(
                        "focus-ring rounded px-2 py-1 text-[12px] font-medium text-ink-500 transition-opacity hover:bg-ink-100 hover:text-ink-800",
                        editing?.maSv === r.maSv
                          ? "opacity-100"
                          : "opacity-0 group-hover:opacity-100 focus-visible:opacity-100",
                      )}
                    >
                      {meta ? "Sửa" : "Đánh dấu"}
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </Table>
      ) : (
        <EmptyState
          title="Không có sinh viên nào khớp bộ lọc"
          desc="Thử bỏ từ khoá hoặc chọn nhóm khác."
          icon={<Users className="h-6 w-6" />}
        />
      )}

      {editing ? (
        <div className="sticky bottom-0 border-t border-ink-200 bg-white p-4 shadow-pop">
          <StatusEditor
            entry={editing}
            busy={busy}
            onCancel={() => setEditing(null)}
            onApply={applyStatus}
          />
        </div>
      ) : null}
    </Drawer>
  );
}

/* ------------------------------------------------------------------ */
/* Ô sửa trạng thái                                                    */
/* ------------------------------------------------------------------ */

function StatusEditor({
  entry,
  busy,
  onCancel,
  onApply,
}: {
  entry: RosterEntry;
  busy: boolean;
  onCancel: () => void;
  onApply: (entry: RosterEntry, trangThai: ExamStatus | null, lyDo: string | null) => void;
}) {
  const [trangThai, setTrangThai] = useState<ExamStatus | "">(entry.trangThai ?? "");
  const [lyDo, setLyDo] = useState(entry.lyDo ?? "");

  return (
    <div className="rounded-lg bg-ink-50 p-3 ring-1 ring-inset ring-ink-200">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <p className="text-[12.5px] font-semibold text-ink-900">
          {entry.hoTen}
          <span className="ml-1.5 font-mono text-[11.5px] font-normal text-ink-400">
            {entry.maSv}
          </span>
        </p>
        <button
          onClick={onCancel}
          className="focus-ring text-[11.5px] text-ink-500 hover:text-ink-800"
        >
          Huỷ
        </button>
      </div>

      <div className="mt-2 grid gap-2 sm:grid-cols-[1fr_1.4fr]">
        <Field label="Trạng thái">
          <select
            className={cn(selectClass, "text-[13px]")}
            value={trangThai}
            onChange={(e) => setTrangThai(e.target.value as ExamStatus | "")}
          >
            <option value="">Bình thường</option>
            <option value="CHUA_NOP_HOC_PHI">Chưa nộp học phí (tạm thời)</option>
            <option value="CAM_THI">Cấm thi hẳn</option>
          </select>
        </Field>
        <Field label="Ghi chú / lý do">
          <input
            className={cn(inputClass, "text-[13px]")}
            value={lyDo}
            onChange={(e) => setLyDo(e.target.value)}
            placeholder="Ví dụ: nợ học phí HK1, kỷ luật thi hộ"
            maxLength={255}
          />
        </Field>
      </div>

      <div className="mt-2.5 flex items-center justify-end gap-2">
        <Button size="sm" variant="ghost" onClick={onCancel} disabled={busy}>
          Đóng
        </Button>
        <Button
          size="sm"
          variant="primary"
          disabled={busy}
          onClick={() => onApply(entry, trangThai || null, lyDo.trim() || null)}
        >
          {busy ? "Đang lưu…" : trangThai ? "Lưu trạng thái" : "Bỏ đánh dấu"}
        </Button>
      </div>

      {trangThai ? (
        <p className="mt-2 flex items-start gap-1.5 text-[11px] leading-relaxed text-ink-500">
          {trangThai === "CAM_THI" ? (
            <AlertTriangle className="mt-0.5 h-3 w-3 shrink-0 text-rose-500" />
          ) : (
            <CheckCircle2 className="mt-0.5 h-3 w-3 shrink-0 text-amber-500" />
          )}
          {examStatusOf(trangThai)?.plain}
        </p>
      ) : (
        <p className="mt-2 flex items-start gap-1.5 text-[11px] leading-relaxed text-ink-500">
          <UserCheck className="mt-0.5 h-3 w-3 shrink-0 text-emerald-500" />
          Sinh viên được dự thi bình thường.
        </p>
      )}
    </div>
  );
}
