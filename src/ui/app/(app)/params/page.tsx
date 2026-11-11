"use client";

import { useState } from "react";
import { Check, RotateCcw, Save } from "lucide-react";
import { useApp } from "@/lib/store";
import type { SolverParams } from "@/lib/types";
import { Button, Card, CardHeader, Field, PageHeader, inputClass } from "@/components/ui";

const PRESETS: {
  id: string;
  title: string;
  desc: string;
  effect: string;
  params: SolverParams;
}[] = [
  {
    id: "tiet_kiem_phong",
    title: "Tiết kiệm phòng máy",
    desc: "Dồn ca vào ít phòng nhất có thể để đỡ tốn điện và nhân sự trông thi.",
    effect: "Có thể phải tách một học phần ra nhiều phòng.",
    params: { alpha: 5, beta: 3, gamma: 1, skipPenalty: 1000, timeLimit: 20, seed: 42, workers: 8 },
  },
  {
    id: "gian_lich",
    title: "Giãn lịch cho sinh viên",
    desc: "Tránh để sinh viên thi nhiều ca trong cùng một ngày.",
    effect: "Cần nhiều ngày thi hơn, đổi lại sinh viên đỡ mệt.",
    params: { alpha: 1, beta: 12, gamma: 1, skipPenalty: 1000, timeLimit: 30, seed: 42, workers: 8 },
  },
  {
    id: "khong_tach",
    title: "Mỗi môn gọn một phòng",
    desc: "Không tách một học phần sang nhiều phòng, dễ thông báo cho sinh viên.",
    effect: "Học phần đông có thể không xếp được nếu thiếu phòng lớn.",
    params: { alpha: 1, beta: 3, gamma: 20, skipPenalty: 1000, timeLimit: 30, seed: 42, workers: 8 },
  },
];

export default function ParamsPage() {
  const { params, saveParams } = useApp();
  const [draft, setDraft] = useState<SolverParams>(params);
  const [saved, setSaved] = useState(false);

  const dirty = JSON.stringify(draft) !== JSON.stringify(params);

  function update<K extends keyof SolverParams>(key: K, value: SolverParams[K]) {
    setDraft((prev) => ({ ...prev, [key]: value }));
    setSaved(false);
  }

  return (
    <>
      <PageHeader
        eyebrow="Cài đặt"
        title="Cấu hình ưu tiên xếp lịch"
        desc="Khi có nhiều cách xếp cùng hợp lệ, các mức ưu tiên dưới đây quyết định hệ thống chọn cách nào. Đổi chúng là đổi lịch ra, không phải đổi độ chính xác."
      />

      <div className="mb-4">
        <p className="mb-2 text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-400">
          Chọn nhanh theo mục tiêu
        </p>
        <div className="grid gap-3 sm:grid-cols-3">
          {PRESETS.map((preset) => {
            const active = JSON.stringify(preset.params) === JSON.stringify(draft);
            return (
              <button
                key={preset.id}
                onClick={() => {
                  setDraft(preset.params);
                  setSaved(false);
                }}
                className={
                  active
                    ? "focus-ring rounded-xl border border-accent-400 bg-accent-50/60 p-4 text-left ring-1 ring-accent-300"
                    : "focus-ring rounded-xl border border-ink-200 bg-white p-4 text-left transition-all hover:border-ink-300 hover:bg-ink-50/60"
                }
              >
                <div className="flex items-start justify-between gap-2">
                  <p className="text-[13px] font-semibold text-ink-900">{preset.title}</p>
                  {active ? (
                    <span className="grid h-4 w-4 shrink-0 place-items-center rounded-full bg-accent-600 text-white">
                      <Check className="h-2.5 w-2.5" strokeWidth={3} />
                    </span>
                  ) : null}
                </div>
                <p className="mt-1 text-[12px] leading-relaxed text-ink-500">{preset.desc}</p>
                <p className="mt-1.5 text-[11.5px] leading-relaxed text-amber-700">{preset.effect}</p>
              </button>
            );
          })}
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader
            title="Mức ưu tiên"
            desc="Số càng lớn thì hệ thống càng tránh điều đó. Để 0 nghĩa là không quan tâm."
          />
          <div className="mt-4 space-y-4">
            <Field
              label="Hạn chế mở thêm phòng"
              hint="Ảnh hưởng mạnh: nhân với số khung giờ. Cao thì dồn ca vào ít phòng."
            >
              <input
                type="number"
                step={0.5}
                min={0}
                className={inputClass}
                value={draft.alpha}
                onChange={(e) => update("alpha", Number(e.target.value))}
              />
            </Field>
            <Field
              label="Hạn chế dồn nhiều ca trong một ngày"
              hint="Cao thì lịch thi giãn ra cho sinh viên đỡ mệt."
            >
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
              hint="Cần cao hơn mức mở phòng thì mới thật sự có tác dụng. Nếu thấp hơn, tách phòng không bị phạt thêm."
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
              hint="Nhân với sĩ số, nên học phần đông bị phạt nặng hơn. Để rất cao để tránh bỏ môn."
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
        </Card>

        <Card>
          <CardHeader
            title="Thời gian và hiệu năng"
            desc="Không ảnh hưởng chất lượng lịch, chỉ ảnh hưởng thời gian chờ."
          />
          <div className="mt-4 space-y-4">
            <Field label="Thời gian chờ tối đa (giây)" hint="Càng lâu càng có cơ hội tìm lịch gọn hơn.">
              <input
                type="number"
                min={1}
                max={600}
                className={inputClass}
                value={draft.timeLimit}
                onChange={(e) => update("timeLimit", Number(e.target.value))}
              />
            </Field>
            <Field label="Số luồng máy tính" hint="Để mặc định nếu không rõ.">
              <input
                type="number"
                min={1}
                max={32}
                className={inputClass}
                value={draft.workers}
                onChange={(e) => update("workers", Number(e.target.value))}
              />
            </Field>
            <Field
              label="Mã lần chạy"
              hint="Cùng mã và cùng dữ liệu thì ra cùng một lịch. Đổi mã để thử phương án khác."
            >
              <input
                type="number"
                className={inputClass}
                value={draft.seed}
                onChange={(e) => update("seed", Number(e.target.value))}
              />
            </Field>
          </div>

          <div className="mt-5 flex items-center gap-2 border-t border-ink-100 pt-4">
            <Button
              variant="primary"
              disabled={!dirty}
              onClick={() => {
                saveParams(draft);
                setSaved(true);
              }}
            >
              <Save className="h-4 w-4" />
              Lưu cấu hình
            </Button>
            <Button
              variant="ghost"
              onClick={() => {
                setDraft(params);
                setSaved(false);
              }}
            >
              <RotateCcw className="h-3.5 w-3.5" />
              Hoàn tác
            </Button>
            {saved ? (
              <span className="ml-auto inline-flex items-center gap-1.5 text-[12px] font-medium text-emerald-600">
                <Check className="h-3.5 w-3.5" />
                Đã lưu
              </span>
            ) : dirty ? (
              <span className="ml-auto text-[12px] text-amber-600">Có thay đổi chưa lưu</span>
            ) : null}
          </div>
        </Card>
      </div>
    </>
  );
}
