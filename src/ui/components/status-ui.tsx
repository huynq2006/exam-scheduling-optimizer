"use client";

import { useEffect } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";
import { examStatusOf } from "@/lib/labels";
import { Badge } from "./ui";

/* ------------------------------------------------------------------ */
/* Nhãn trạng thái dự thi                                              */
/* ------------------------------------------------------------------ */

export function StatusPill({
  trangThai,
  className,
  short = false,
}: {
  trangThai: string | null | undefined;
  className?: string;
  short?: boolean;
}) {
  const meta = examStatusOf(trangThai);
  if (!meta) {
    return (
      <span className={cn("text-[11.5px] text-ink-300", className)}>—</span>
    );
  }
  return (
    <Badge tone={meta.tone} className={className}>
      <span
        className={cn(
          "h-1.5 w-1.5 rounded-full",
          trangThai === "CAM_THI" ? "bg-rose-500" : "bg-amber-500",
        )}
      />
      {short ? meta.short : meta.text}
    </Badge>
  );
}

/* ------------------------------------------------------------------ */
/* Drawer trượt từ phải                                                */
/* ------------------------------------------------------------------ */

/**
 * Bảng trượt dùng cho danh sách sinh viên của một ca thi.
 *
 * Đóng bằng Escape và bằng bấm nền, vì đây là bảng tra cứu nhanh: giám thị
 * mở ra xem rồi đóng, không nên bắt họ đi tìm nút.
 */
export function Drawer({
  open,
  onClose,
  title,
  subtitle,
  children,
  footer,
  width = "max-w-2xl",
}: {
  open: boolean;
  onClose: () => void;
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  children: React.ReactNode;
  footer?: React.ReactNode;
  width?: string;
}) {
  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    // Khoá cuộn nền để bảng không bị trôi theo trang phía sau. Trang cuộn
    // trong vùng nội dung chứ không phải trong body, nên khoá cả hai.
    const root = document.documentElement;
    root.setAttribute("data-scroll-lock", "");
    return () => {
      window.removeEventListener("keydown", onKey);
      root.removeAttribute("data-scroll-lock");
    };
  }, [open, onClose]);

  if (!open) return null;

  // Render ra body: nếu để trong cây trang, một transform còn hiệu lực ở tổ
  // tiên (ví dụ .animate-rise) sẽ biến tổ tiên đó thành containing block và
  // drawer neo vào nội dung cuộn thay vì viewport — cao vống lên và tràn.
  return createPortal(
    <div className="fixed inset-0 z-50">
      <div
        className="absolute inset-0 bg-ink-900/30 backdrop-blur-[1px]"
        onClick={onClose}
        aria-hidden
      />
      <div
        role="dialog"
        aria-modal="true"
        className={cn(
          "absolute inset-y-0 right-0 flex w-full flex-col border-l border-ink-200 bg-white shadow-pop",
          width,
        )}
      >
        <div className="flex shrink-0 items-start justify-between gap-4 border-b border-ink-200 px-5 py-4">
          <div className="min-w-0">
            <h2 className="text-[15px] font-semibold tracking-tight text-ink-900">{title}</h2>
            {subtitle ? (
              <p className="mt-0.5 text-[12.5px] leading-relaxed text-ink-500">{subtitle}</p>
            ) : null}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="focus-ring shrink-0 rounded-md p-1.5 text-ink-400 transition-colors hover:bg-ink-100 hover:text-ink-700"
            aria-label="Đóng"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto">{children}</div>

        {footer ? (
          <div className="shrink-0 border-t border-ink-200 bg-ink-50/60 px-5 py-3">{footer}</div>
        ) : null}
      </div>
    </div>,
    document.body,
  );
}
