"use client";

import { useCallback, useMemo, useRef, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Download,
  FileSpreadsheet,
  History,
  Upload,
  XCircle,
} from "lucide-react";
import { useApp } from "@/lib/store";
import { useDataset } from "@/lib/dataset";
import { useAllStatuses } from "@/lib/exam-status";
import { cn, formatDateTime } from "@/lib/utils";
import { rowToneClass } from "@/lib/labels";
import type { ImportPreview } from "@/lib/types";
import { StatusPill } from "@/components/status-ui";
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

interface CommitResult {
  maDot: number;
  tongDong: number;
  soThanhCong: number;
  soLoi: number;
  errors: Array<{ dong: number; maSv: string; lyDo: string }>;
}

interface HistoryRow {
  ma_dot: number;
  ten_file: string;
  tong_dong: number;
  so_thanh_cong: number;
  so_loi: number;
  nguoi_import: string | null;
  tao_luc: string;
}

const TEMPLATE = `ma_sv,ma_mon,trang_thai,ly_do
SV20210001,,CAM_THI,Kỷ luật thi hộ
SV20210002,,CHUA_NOP_HOC_PHI,Nợ học phí HK1
SV20210003,INT101,CAM_THI,Đánh trượt môn
`;

export default function ImportPage() {
  const { user } = useApp();
  const { subjects } = useDataset();
  const { statuses, reload: reloadStatuses } = useAllStatuses();

  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [result, setResult] = useState<CommitResult | null>(null);
  const [busy, setBusy] = useState<"preview" | "commit" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const [history, setHistory] = useState<HistoryRow[] | null>(null);

  const loadHistory = useCallback(async () => {
    try {
      const res = await fetch("/api/exam-status/import", { cache: "no-store" });
      const body = await res.json();
      if (res.ok) setHistory(body.history ?? []);
    } catch {
      /* lịch sử chỉ là phụ, không chặn luồng chính */
    }
  }, []);

  const send = useCallback(
    async (f: File, mode: "preview" | "commit") => {
      setBusy(mode);
      setError(null);
      try {
        const form = new FormData();
        form.set("file", f);
        form.set("mode", mode);
        if (user?.name) form.set("nguoiImport", user.name);

        const res = await fetch("/api/exam-status/import", { method: "POST", body: form });
        const body = await res.json();
        if (!res.ok) throw new Error(body?.detail ?? body?.error ?? `Lỗi ${res.status}`);

        if (mode === "preview") {
          setPreview(body as ImportPreview);
          setResult(null);
        } else {
          setResult(body as CommitResult);
          setPreview(null);
          setFile(null);
          if (inputRef.current) inputRef.current.value = "";
          reloadStatuses();
          loadHistory();
        }
      } catch (err) {
        setError((err as Error).message);
      } finally {
        setBusy(null);
      }
    },
    [user?.name, reloadStatuses, loadHistory],
  );

  function onPick(f: File | null) {
    if (!f) return;
    setFile(f);
    setResult(null);
    setPreview(null);
    void send(f, "preview");
  }

  const counts = useMemo(() => {
    if (!preview) return null;
    return {
      hopLe: preview.rows.filter((r) => r.hopLe).length,
      loi: preview.rows.filter((r) => !r.hopLe).length,
    };
  }, [preview]);

  function downloadTemplate() {
    const blob = new Blob([`\uFEFF${TEMPLATE}`], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "mau-danh-sach-cam-thi.csv";
    a.click();
    URL.revokeObjectURL(url);
  }

  const activeCount = statuses.length;

  return (
    <>
      <PageHeader
        eyebrow="Chuẩn bị"
        title="Danh sách cấm thi"
        desc="Nạp danh sách sinh viên bị cấm thi từ file CSV."
        action={
          <Button variant="secondary" onClick={downloadTemplate}>
            <Download className="h-4 w-4" />
            Tải file mẫu
          </Button>
        }
      />

      <div className="grid gap-3 sm:grid-cols-3">
        <Stat
          label="Sinh viên đang bị đánh dấu"
          value={`${activeCount}`}
          hint="Cấm toàn bộ và cấm theo môn"
          tone={activeCount ? "warning" : "success"}
        />
        <Stat
          label="Cấm thi hẳn"
          value={`${statuses.filter((s) => s.trangThai === "CAM_THI").length}`}
          hint="Kỷ luật, đánh trượt môn"
          tone="danger"
        />
        <Stat
          label="Chưa nộp học phí"
          value={`${statuses.filter((s) => s.trangThai === "CHUA_NOP_HOC_PHI").length}`}
          hint="Cấm thi tạm thời"
          tone="warning"
        />
      </div>

      {/* ---------------- Nạp file ---------------- */}
      <Card className="mt-4">
        <CardHeader
          title="Nạp file CSV"
          desc="Cần có cột ma_sv và trang_thai. Cột ma_mon và ly_do không bắt buộc."
        />

        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            onPick(e.dataTransfer.files?.[0] ?? null);
          }}
          className={cn(
            "mt-4 rounded-xl border-2 border-dashed px-6 py-10 text-center transition-colors",
            dragging ? "border-accent-400 bg-accent-50/50" : "border-ink-200 bg-ink-50/40",
          )}
        >
          <FileSpreadsheet className="mx-auto h-8 w-8 text-ink-300" />
          <p className="mt-2 text-[13.5px] font-medium text-ink-700">
            Kéo file CSV vào đây, hoặc chọn file
          </p>
          <p className="mt-1 text-[12px] text-ink-400">Nhận file .csv, kể cả file xuất từ Excel.</p>
          <input
            ref={inputRef}
            type="file"
            accept=".csv,text/csv"
            className="hidden"
            onChange={(e) => onPick(e.target.files?.[0] ?? null)}
          />
          <Button
            variant="primary"
            size="sm"
            className="mt-3"
            onClick={() => inputRef.current?.click()}
            disabled={busy !== null}
          >
            <Upload className="h-3.5 w-3.5" />
            {busy === "preview" ? "Đang đọc file…" : "Chọn file CSV"}
          </Button>
          {file ? (
            <p className="mt-2 text-[12px] text-ink-500">
              Đã chọn: <span className="font-medium text-ink-700">{file.name}</span>
            </p>
          ) : null}
        </div>

        {error ? (
          <p className="mt-3 rounded-lg bg-rose-50 px-3 py-2 text-[12.5px] text-rose-700 ring-1 ring-inset ring-rose-200">
            {error}
          </p>
        ) : null}
      </Card>

      {/* ---------------- Kết quả ghi ---------------- */}
      {result ? (
        <Card className="mt-4">
          <div className="flex items-start gap-2.5">
            <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-emerald-600" />
            <div>
              <p className="text-[13.5px] font-semibold text-ink-900">
                Đã nạp xong đợt #{result.maDot}
              </p>
              <p className="mt-0.5 text-[12.5px] text-ink-600">
                {result.soThanhCong}/{result.tongDong} dòng được ghi vào cơ sở dữ liệu
                {result.soLoi ? `, ${result.soLoi} dòng bị bỏ qua.` : "."}
              </p>
            </div>
          </div>
          {result.errors.length ? (
            <div className="mt-3 rounded-lg bg-amber-50 p-3 ring-1 ring-inset ring-amber-200">
              <p className="text-[12px] font-medium text-amber-800">
                {result.errors.length} dòng không nạp được
              </p>
              <ul className="mt-1.5 space-y-0.5 text-[11.5px] text-amber-800">
                {result.errors.slice(0, 10).map((e, i) => (
                  <li key={`${e.dong}-${i}`}>
                    Dòng {e.dong}
                    {e.maSv ? ` (${e.maSv})` : ""}: {e.lyDo}
                  </li>
                ))}
                {result.errors.length > 10 ? (
                  <li>… và {result.errors.length - 10} dòng khác</li>
                ) : null}
              </ul>
            </div>
          ) : null}
        </Card>
      ) : null}

      {/* ---------------- Xem trước ---------------- */}
      {preview ? (
        <Card className="mt-4" padded={false}>
          <div className="p-5 pb-3">
            <CardHeader
              title={`Xem trước: ${preview.tenFile}`}
              desc="Kiểm tra danh sách rồi mới bấm nạp."
              action={
                <div className="flex items-center gap-2">
                  <Badge tone="success">{counts?.hopLe ?? 0} hợp lệ</Badge>
                  {counts?.loi ? <Badge tone="danger">{counts.loi} lỗi</Badge> : null}
                </div>
              }
            />
            <div className="mt-3 flex flex-wrap gap-4 text-[12px] text-ink-600">
              <span>Tổng {preview.tongDong} dòng</span>
              <span>·</span>
              <span>{preview.khop} mã khớp sinh viên trong hệ thống</span>
              {preview.khongTonTai ? (
                <>
                  <span>·</span>
                  <span className="font-medium text-rose-600">
                    {preview.khongTonTai} mã không tồn tại
                  </span>
                </>
              ) : null}
              {preview.trungLap ? (
                <>
                  <span>·</span>
                  <span className="font-medium text-amber-600">
                    {preview.trungLap} dòng trùng trong file
                  </span>
                </>
              ) : null}
            </div>
          </div>

          <Table>
            <thead>
              <tr>
                <th className="w-16 text-center">Dòng</th>
                <th>Mã SV</th>
                <th>Họ tên</th>
                <th>Lớp</th>
                <th>Học phần</th>
                <th>Trạng thái</th>
                <th>Ghi chú</th>
                <th className="text-center">Kết quả</th>
              </tr>
            </thead>
            <tbody>
              {preview.rows.map((r) => (
                <tr key={`${r.dong}-${r.maSv}`} className={rowToneClass(r.hopLe ? r.trangThai : null)}>
                  <td className="text-center tabular-nums text-[12px] text-ink-400">{r.dong}</td>
                  <td className="whitespace-nowrap font-mono text-[12px] text-ink-600">
                    {r.maSv || "—"}
                  </td>
                  <td className="whitespace-nowrap text-[12.5px]">
                    {r.hoTen ?? <span className="text-ink-300">—</span>}
                  </td>
                  <td className="whitespace-nowrap text-[12.5px] text-ink-600">{r.lop ?? "—"}</td>
                  <td className="whitespace-nowrap text-[12.5px]">
                    {r.maMon ? (
                      <span className="font-mono text-[11.5px]">{r.maMon}</span>
                    ) : (
                      <span className="text-ink-400">Toàn bộ</span>
                    )}
                  </td>
                  <td className="whitespace-nowrap">
                    <StatusPill trangThai={r.trangThai} short />
                  </td>
                  <td className="max-w-[200px] truncate text-[12px] text-ink-500" title={r.lyDo ?? ""}>
                    {r.lyDo ?? "—"}
                  </td>
                  <td className="text-center">
                    {r.hopLe ? (
                      <CheckCircle2 className="mx-auto h-4 w-4 text-emerald-500" />
                    ) : (
                      <span title={r.loi}>
                        <XCircle className="mx-auto h-4 w-4 text-rose-500" />
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>

          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-ink-200 p-4">
            <p className="flex items-start gap-1.5 text-[11.5px] leading-relaxed text-ink-500">
              <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-500" />
              {counts?.hopLe ?? 0} dòng hợp lệ sẽ được nạp. Dòng lỗi được bỏ qua.
            </p>
            <div className="flex gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setPreview(null);
                  setFile(null);
                  if (inputRef.current) inputRef.current.value = "";
                }}
                disabled={busy !== null}
              >
                Huỷ
              </Button>
              <Button
                variant="primary"
                size="sm"
                disabled={busy !== null || !counts?.hopLe}
                onClick={() => file && send(file, "commit")}
              >
                {busy === "commit" ? "Đang nạp…" : `Nạp ${counts?.hopLe ?? 0} dòng`}
              </Button>
            </div>
          </div>
        </Card>
      ) : null}

      {/* ---------------- Lịch sử ---------------- */}
      <Card className="mt-4" padded={false}>
        <div className="flex flex-wrap items-end justify-between gap-3 p-5 pb-3">
          <CardHeader
            title="Lịch sử nạp danh sách"
            desc="Các lần nạp trước, để đối chiếu khi cần."
          />
          <Button variant="secondary" size="sm" onClick={loadHistory}>
            <History className="h-3.5 w-3.5" />
            {history ? "Tải lại" : "Xem lịch sử"}
          </Button>
        </div>

        {history === null ? (
          <EmptyState
            title="Chưa tải lịch sử"
            desc="Bấm “Xem lịch sử” để xem các lần nạp trước."
            icon={<History className="h-6 w-6" />}
          />
        ) : history.length ? (
          <Table>
            <thead>
              <tr>
                <th className="w-16 text-center">Đợt</th>
                <th>File</th>
                <th className="text-center">Tổng dòng</th>
                <th className="text-center">Thành công</th>
                <th className="text-center">Lỗi</th>
                <th>Người nạp</th>
                <th>Thời điểm</th>
              </tr>
            </thead>
            <tbody>
              {history.map((h) => (
                <tr key={h.ma_dot}>
                  <td className="text-center tabular-nums text-[12px] text-ink-500">#{h.ma_dot}</td>
                  <td className="max-w-[260px] truncate text-[12.5px] font-medium text-ink-800">
                    {h.ten_file}
                  </td>
                  <td className="text-center tabular-nums text-[12.5px]">{h.tong_dong}</td>
                  <td className="text-center tabular-nums text-[12.5px] text-emerald-700">
                    {h.so_thanh_cong}
                  </td>
                  <td className="text-center tabular-nums text-[12.5px]">
                    <span className={h.so_loi ? "font-medium text-rose-600" : "text-ink-400"}>
                      {h.so_loi}
                    </span>
                  </td>
                  <td className="text-[12.5px] text-ink-600">{h.nguoi_import ?? "—"}</td>
                  <td className="whitespace-nowrap text-[12px] text-ink-500">
                    {formatDateTime(h.tao_luc)}
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        ) : (
          <EmptyState title="Chưa có lần nạp nào" desc="Đợt nạp đầu tiên sẽ hiện ở đây." />
        )}
      </Card>

      {/* ---------------- Đang đánh dấu ---------------- */}
      <Card className="mt-4" padded={false}>
        <div className="p-5 pb-3">
          <CardHeader
            title="Sinh viên đang bị đánh dấu"
            desc="Bỏ đánh dấu để sinh viên trở lại bình thường."
            action={<Badge tone="neutral">{activeCount} dòng</Badge>}
          />
        </div>
        {statuses.length ? (
          <Table>
            <thead>
              <tr>
                <th>Mã SV</th>
                <th>Học phần</th>
                <th>Trạng thái</th>
                <th>Ghi chú</th>
                <th>Nguồn</th>
                <th>Cập nhật</th>
              </tr>
            </thead>
            <tbody>
              {statuses.slice(0, 100).map((s) => (
                <tr key={`${s.maSv}-${s.maMon ?? "*"}`} className={rowToneClass(s.trangThai)}>
                  <td className="whitespace-nowrap font-mono text-[12px] text-ink-600">{s.maSv}</td>
                  <td className="whitespace-nowrap text-[12.5px]">
                    {s.maMon ? (
                      <span className="font-mono text-[11.5px]">{s.maMon}</span>
                    ) : (
                      <span className="text-ink-400">Toàn bộ</span>
                    )}
                  </td>
                  <td className="whitespace-nowrap">
                    <StatusPill trangThai={s.trangThai} short />
                  </td>
                  <td className="max-w-[240px] truncate text-[12px] text-ink-500" title={s.lyDo ?? ""}>
                    {s.lyDo ?? "—"}
                  </td>
                  <td className="whitespace-nowrap text-[11.5px] text-ink-400">
                    {s.nguon === "IMPORT_CSV" ? "Nạp CSV" : "Nhập tay"}
                  </td>
                  <td className="whitespace-nowrap text-[11.5px] text-ink-400">
                    {formatDateTime(s.capNhatLuc)}
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        ) : (
          <EmptyState
            title="Chưa có sinh viên nào bị đánh dấu"
            desc="Nạp file CSV ở trên để thêm vào danh sách."
            icon={<CheckCircle2 className="h-6 w-6" />}
          />
        )}
        {statuses.length > 100 ? (
          <p className="border-t border-ink-100 px-5 py-2.5 text-[11.5px] text-ink-400">
            Đang hiện 100/{statuses.length} dòng. Xem đầy đủ ở trang Truy vấn.
          </p>
        ) : null}
      </Card>

      <p className="mt-4 text-[11.5px] leading-relaxed text-ink-400">
        Để trống cột <span className="font-mono">ma_mon</span> là cấm toàn bộ học phần; điền mã
        môn thì chỉ cấm đúng môn đó. Danh mục hiện có {subjects.length} học phần.
      </p>
    </>
  );
}
