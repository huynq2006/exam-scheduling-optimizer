"use client";

import { cn } from "@/lib/utils";
import type { ReactNode } from "react";

/* ------------------------------------------------------------------ */
/* Badge                                                               */
/* ------------------------------------------------------------------ */

type Tone = "neutral" | "success" | "warning" | "info" | "danger" | "muted";

const TONE_CLASS: Record<Tone, string> = {
  neutral: "bg-ink-100 text-ink-700 ring-ink-200",
  success: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  warning: "bg-amber-50 text-amber-700 ring-amber-200",
  info: "bg-accent-50 text-accent-700 ring-accent-200",
  danger: "bg-rose-50 text-rose-700 ring-rose-200",
  muted: "bg-ink-50 text-ink-500 ring-ink-200",
};

export function Badge({
  children,
  tone = "neutral",
  className,
}: {
  children: ReactNode;
  tone?: Tone;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset",
        TONE_CLASS[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}

export function Dot({ tone = "neutral" }: { tone?: Tone }) {
  const color: Record<Tone, string> = {
    neutral: "bg-ink-400",
    success: "bg-emerald-500",
    warning: "bg-amber-500",
    info: "bg-accent-500",
    danger: "bg-rose-500",
    muted: "bg-ink-300",
  };
  return <span className={cn("h-1.5 w-1.5 rounded-full", color[tone])} />;
}

/* ------------------------------------------------------------------ */
/* Card                                                                */
/* ------------------------------------------------------------------ */

export function Card({
  children,
  className,
  padded = true,
}: {
  children: ReactNode;
  className?: string;
  padded?: boolean;
}) {
  return (
    <section className={cn("surface", padded && "p-5", className)}>{children}</section>
  );
}

export function CardHeader({
  title,
  desc,
  action,
  className,
}: {
  title: ReactNode;
  desc?: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-wrap items-start justify-between gap-3", className)}>
      <div className="min-w-0">
        <h2 className="text-[15px] font-semibold tracking-tight text-ink-900">{title}</h2>
        {desc ? <p className="mt-1 text-[13px] leading-relaxed text-ink-500">{desc}</p> : null}
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Button                                                              */
/* ------------------------------------------------------------------ */

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";

const BUTTON_CLASS: Record<ButtonVariant, string> = {
  primary:
    "bg-accent-600 text-white hover:bg-accent-700 active:bg-accent-800 shadow-sm disabled:bg-ink-300",
  secondary:
    "bg-white text-ink-700 ring-1 ring-inset ring-ink-200 hover:bg-ink-50 disabled:text-ink-400",
  ghost: "text-ink-600 hover:bg-ink-100 hover:text-ink-900 disabled:text-ink-300",
  danger:
    "bg-white text-rose-600 ring-1 ring-inset ring-rose-200 hover:bg-rose-50 disabled:text-ink-400",
};

export function Button({
  children,
  variant = "secondary",
  className,
  size = "md",
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  size?: "sm" | "md";
}) {
  return (
    <button
      {...props}
      className={cn(
        "focus-ring inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-colors disabled:cursor-not-allowed",
        size === "sm" ? "px-3 py-1.5 text-[13px]" : "px-4 py-2 text-sm",
        BUTTON_CLASS[variant],
        className,
      )}
    >
      {children}
    </button>
  );
}

/* ------------------------------------------------------------------ */
/* Stat                                                                */
/* ------------------------------------------------------------------ */

export function Stat({
  label,
  value,
  hint,
  icon,
  tone = "neutral",
}: {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  icon?: ReactNode;
  tone?: Tone;
}) {
  const iconClass: Record<Tone, string> = {
    neutral: "bg-ink-100 text-ink-600",
    success: "bg-emerald-50 text-emerald-600",
    warning: "bg-amber-50 text-amber-600",
    info: "bg-accent-50 text-accent-600",
    danger: "bg-rose-50 text-rose-600",
    muted: "bg-ink-50 text-ink-400",
  };
  return (
    <div className="surface p-4">
      <div className="flex items-start justify-between gap-3">
        <p className="text-[12.5px] font-medium text-ink-500">{label}</p>
        {icon ? (
          <span className={cn("grid h-7 w-7 place-items-center rounded-lg", iconClass[tone])}>
            {icon}
          </span>
        ) : null}
      </div>
      <p className="mt-2 text-[22px] font-semibold leading-none tracking-tight text-ink-900">
        {value}
      </p>
      {hint ? <p className="mt-2 text-[12px] text-ink-400">{hint}</p> : null}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Page header                                                         */
/* ------------------------------------------------------------------ */

export function PageHeader({
  eyebrow,
  title,
  desc,
  action,
}: {
  eyebrow?: string;
  title: string;
  desc?: string;
  action?: ReactNode;
}) {
  return (
    <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        {eyebrow ? (
          <p className="mb-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-ink-400">
            {eyebrow}
          </p>
        ) : null}
        <h1 className="text-[26px] font-semibold leading-tight tracking-tight text-ink-900">
          {title}
        </h1>
        {desc ? <p className="mt-1.5 max-w-2xl text-[13.5px] leading-relaxed text-ink-500">{desc}</p> : null}
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </header>
  );
}

/* ------------------------------------------------------------------ */
/* Table                                                               */
/* ------------------------------------------------------------------ */

export function Table({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={cn("overflow-x-auto", className)}>
      <table className="table-base">{children}</table>
    </div>
  );
}

export function EmptyState({
  title,
  desc,
  icon,
}: {
  title: string;
  desc?: string;
  icon?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 px-6 py-14 text-center">
      {icon ? <div className="mb-1 text-ink-300">{icon}</div> : null}
      <p className="text-sm font-medium text-ink-700">{title}</p>
      {desc ? <p className="max-w-sm text-[13px] text-ink-400">{desc}</p> : null}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Field                                                               */
/* ------------------------------------------------------------------ */

export function Field({
  label,
  hint,
  children,
  className,
}: {
  label: string;
  hint?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <label className={cn("block", className)}>
      <span className="mb-1.5 block text-[12.5px] font-medium text-ink-600">{label}</span>
      {children}
      {hint ? <span className="mt-1 block text-[11.5px] text-ink-400">{hint}</span> : null}
    </label>
  );
}

export const inputClass =
  "focus-ring w-full rounded-lg border border-ink-200 bg-white px-3 py-2 text-sm text-ink-800 placeholder:text-ink-400";

export const selectClass = cn(inputClass, "appearance-none pr-8");

export function Progress({ value, tone = "info" }: { value: number; tone?: Tone }) {
  const bar: Record<Tone, string> = {
    neutral: "bg-ink-400",
    success: "bg-emerald-500",
    warning: "bg-amber-500",
    info: "bg-accent-500",
    danger: "bg-rose-500",
    muted: "bg-ink-300",
  };
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-ink-100">
      <div
        className={cn("h-full rounded-full transition-all", bar[tone])}
        style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
      />
    </div>
  );
}
