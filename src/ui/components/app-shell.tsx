"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  ChevronRight,
  Database,
  LayoutDashboard,
  LogOut,
  Menu,
  MonitorCog,
  Play,
  SlidersHorizontal,
  Table2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { statusOf } from "@/lib/labels";
import { useApp } from "@/lib/store";
import type { Role } from "@/lib/types";
import { Badge } from "./ui";

interface NavItem {
  href: string;
  label: string;
  icon: React.ComponentType<{ className?: string; strokeWidth?: number }>;
  group: string;
}

const GIAOVU_NAV: NavItem[] = [
  { href: "/dashboard", label: "Tổng quan", icon: LayoutDashboard, group: "Bắt đầu" },
  { href: "/inputs", label: "Dữ liệu xếp lịch", icon: Database, group: "Chuẩn bị" },
  { href: "/solve", label: "Xếp lịch thi", icon: Play, group: "Xếp lịch" },
  { href: "/solution", label: "Lịch thi đã xếp", icon: Table2, group: "Xếp lịch" },
  { href: "/params", label: "Cấu hình ưu tiên", icon: SlidersHorizontal, group: "Cài đặt" },
];

const SINHVIEN_NAV: NavItem[] = [
  { href: "/my-exams", label: "Lịch thi của tôi", icon: Table2, group: "Tra cứu" },
  { href: "/my-rooms", label: "Phòng máy của tôi", icon: MonitorCog, group: "Tra cứu" },
];

const NAV_BY_ROLE: Record<Role, NavItem[]> = {
  giaovu: GIAOVU_NAV,
  sinhvien: SINHVIEN_NAV,
};

/** Trang mặc định của từng vai trò. */
const HOME_BY_ROLE: Record<Role, string> = {
  giaovu: "/dashboard",
  sinhvien: "/my-exams",
};

export function AppShell({ children }: { children: React.ReactNode }) {
  const { user, hydrated, logout, result } = useApp();
  const pathname = usePathname();
  const router = useRouter();
  const [open, setOpen] = useState(false);

  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  const role: Role | null = user?.role ?? null;
  const items = role ? NAV_BY_ROLE[role] : [];

  // Chưa đăng nhập -> về trang đăng nhập.
  useEffect(() => {
    if (hydrated && !user) router.replace("/login");
  }, [hydrated, user, router]);

  // Đã đăng nhập nhưng mở trang của vai trò khác -> đưa về trang của mình.
  // Sinh viên không được xem dữ liệu xếp lịch, giáo vụ không cần trang tra cứu cá nhân.
  useEffect(() => {
    if (!hydrated || !role) return;
    const allowed = NAV_BY_ROLE[role].some(
      (i) => pathname === i.href || pathname.startsWith(`${i.href}/`),
    );
    if (!allowed) router.replace(HOME_BY_ROLE[role]);
  }, [hydrated, role, pathname, router]);

  if (!hydrated || !user || !role) {
    return (
      <div className="grid min-h-screen place-items-center">
        <div className="flex items-center gap-2 text-sm text-ink-400">
          <span className="h-2 w-2 animate-pulse rounded-full bg-accent-500" />
          Đang tải…
        </div>
      </div>
    );
  }

  const groups = Array.from(new Set(items.map((i) => i.group)));
  const isStudent = role === "sinhvien";

  function handleLogout() {
    logout();
    router.replace("/login");
  }

  const nav = (
    <div className="flex h-full max-h-screen flex-col">
      <div className="flex shrink-0 items-center gap-2.5 px-5 py-5">
        <span className="grid h-8 w-8 place-items-center rounded-lg bg-accent-600 text-[13px] font-bold text-white">LT</span>
        <div className="leading-tight">
          <p className="text-[13.5px] font-semibold tracking-tight text-ink-900">Xếp lịch thi</p>
          <p className="text-[11px] text-ink-400">{isStudent ? "Cổng sinh viên" : "Phòng Đào tạo"}</p>
        </div>
      </div>

      <nav className="min-h-0 flex-1 space-y-5 overflow-y-auto px-3 pb-4">
        {groups.map((group) => (
          <div key={group}>
            <p className="mb-1.5 px-2 text-[10.5px] font-semibold uppercase tracking-[0.12em] text-ink-400">
              {group}
            </p>
            <ul className="space-y-0.5">
              {items
                .filter((i) => i.group === group)
                .map((item) => {
                  const active =
                    pathname === item.href ||
                    (item.href !== "/dashboard" && pathname.startsWith(`${item.href}/`));
                  const Icon = item.icon;
                  return (
                    <li key={item.href}>
                      <Link
                        href={item.href}
                        className={cn(
                          "focus-ring group flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-[13px] font-medium transition-colors",
                          active
                            ? "bg-white text-ink-900 shadow-card ring-1 ring-ink-200"
                            : "text-ink-600 hover:bg-white/70 hover:text-ink-900",
                        )}
                      >
                        <Icon
                          className={cn("h-4 w-4", active ? "text-accent-600" : "text-ink-400")}
                          strokeWidth={1.9}
                        />
                        <span className="truncate">{item.label}</span>
                        {item.href === "/solution" && result ? (
                          <span className="ml-auto rounded-full bg-emerald-100 px-1.5 py-0.5 text-[10.5px] font-semibold text-emerald-700">
                            {result.sessions.length}
                          </span>
                        ) : null}
                      </Link>
                    </li>
                  );
                })}
            </ul>
          </div>
        ))}
      </nav>

      <div className="shrink-0 border-t border-ink-200 p-3">
        <div className="rounded-lg bg-white p-2.5 ring-1 ring-ink-200">
          <div className="flex items-center gap-2">
            <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-ink-100 text-[11px] font-semibold text-ink-600">
              {user.name.split(" ").slice(-1)[0]?.slice(0, 2).toUpperCase()}
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-[12px] font-semibold text-ink-900">{user.name}</p>
              <p className="truncate text-[10.5px] text-ink-400">{user.dept}</p>
            </div>
          </div>
          <button
            type="button"
            onClick={handleLogout}
            className="focus-ring mt-2 flex w-full items-center justify-center gap-1.5 rounded-md border border-ink-200 bg-white px-2 py-1.5 text-[11.5px] font-medium text-ink-600 transition-colors hover:bg-ink-50 hover:text-ink-900"
          >
            <LogOut className="h-3.5 w-3.5" strokeWidth={1.9} />
            Đăng xuất
          </button>
        </div>
      </div>
    </div>
  );

  const currentLabel =
    items.find(
      (i) => pathname === i.href || (i.href !== "/dashboard" && pathname.startsWith(`${i.href}/`)),
    )?.label ?? items[0]?.label ?? "";

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[248px_1fr]">
      <aside className="hidden border-r border-ink-200 bg-ink-100/60 lg:block">
        <div className="sticky top-0 h-screen overflow-hidden">{nav}</div>
      </aside>

      {open ? (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-ink-900/30" onClick={() => setOpen(false)} />
          <div className="absolute inset-y-0 left-0 w-64 border-r border-ink-200 bg-ink-100">{nav}</div>
        </div>
      ) : null}

      <div className="flex min-w-0 flex-col">
        <header className="sticky top-0 z-30 flex h-14 items-center gap-3 border-b border-ink-200 bg-ink-50/85 px-4 backdrop-blur lg:px-8">
          <button
            onClick={() => setOpen(true)}
            className="focus-ring rounded-md p-1.5 text-ink-500 hover:bg-ink-100 lg:hidden"
            aria-label="Mở menu"
          >
            <Menu className="h-5 w-5" />
          </button>

          <div className="flex min-w-0 items-center gap-2 text-[12.5px] text-ink-400">
            <span className="hidden sm:inline">Xếp lịch thi</span>
            <ChevronRight className="hidden h-3.5 w-3.5 sm:inline" />
            <span className="truncate font-medium text-ink-700">{currentLabel}</span>
          </div>

          <div className="ml-auto flex items-center gap-2">
            {isStudent ? (
              user.maSv ? <Badge tone="info">{user.maSv}</Badge> : null
            ) : result ? (
              <Badge tone={statusOf(result.stats.status).tone}>
                {statusOf(result.stats.status).text}
              </Badge>
            ) : (
              <Badge tone="muted">Chưa xếp lịch</Badge>
            )}
          </div>
        </header>

        <main className="mx-auto w-full max-w-[1180px] flex-1 px-4 py-6 lg:px-8 lg:py-8">
          <div className="animate-rise">{children}</div>
        </main>

        <footer className="border-t border-ink-200 px-4 py-4 text-[11.5px] text-ink-400 lg:px-8">
          {isStudent
            ? "Lịch thi hiển thị ở đây là phương án đã được Phòng Đào tạo công bố."
            : "Kết quả xếp lịch do hệ thống tính trực tiếp từ dữ liệu hiện tại, không phải số mô phỏng."}
        </footer>
      </div>
    </div>
  );
}
