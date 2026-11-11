"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { ACCOUNTS, DEFAULT_PARAMS } from "./data";
import type { SolveResult, SolverParams, User } from "./types";

// v3: thêm vai trò sinh viên. Người dùng cũ (v2) chỉ có username giáo vụ nên
// phải đọc lại từ đầu thay vì cố suy ra user từ chuỗi username.
const STORAGE_KEY = "exam-scheduler-cpsat-v3";

interface PersistedState {
  user: User | null;
  params: SolverParams;
  result: SolveResult | null;
}

interface LoginResult {
  ok: boolean;
  message: string;
}

interface AppState extends PersistedState {
  hydrated: boolean;
  login: (username: string, password: string) => Promise<LoginResult>;
  logout: () => void;
  saveParams: (params: SolverParams) => void;
  runSolver: (params: SolverParams) => Promise<LoginResult>;
  clearResult: () => void;
}

const AppContext = createContext<AppState | null>(null);

function initialState(): PersistedState {
  return { user: null, params: DEFAULT_PARAMS, result: null };
}

/** Tài khoản nội bộ (giáo vụ) nằm trong bundle; sinh viên tra từ MySQL. */
function findLocalAccount(username: string) {
  const key = username.trim().toLowerCase();
  return ACCOUNTS.find((a) => a.username.toLowerCase() === key) ?? null;
}

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<PersistedState>(initialState);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw) as Partial<PersistedState>;
        setState((prev) => ({ ...prev, ...parsed }));
      }
    } catch {
      /* dữ liệu hỏng thì dùng mặc định */
    }
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch {
      /* bỏ qua khi trình duyệt chặn lưu trữ */
    }
  }, [state, hydrated]);

  const login = useCallback(async (username: string, password: string): Promise<LoginResult> => {
    const raw = username.trim();
    if (!raw) return { ok: false, message: "Vui lòng nhập tên đăng nhập hoặc mã sinh viên." };

    // 1. Tài khoản nội bộ (giáo vụ).
    const local = findLocalAccount(raw);
    if (local) {
      if (local.password !== password) return { ok: false, message: "Mật khẩu không đúng." };
      const { password: _password, ...user } = local;
      setState((prev) => ({ ...prev, user }));
      return { ok: true, message: "" };
    }

    // 2. Sinh viên: mã số sinh viên, mật khẩu trùng mã. Tra trong MySQL.
    try {
      const res = await fetch("/api/student/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ maSv: raw, password }),
      });
      const data = await res.json();

      if (!res.ok) {
        return { ok: false, message: data?.error ?? `Đăng nhập thất bại (${res.status}).` };
      }

      const s = data.student as {
        maSv: string;
        hoTen: string;
        lop: string;
        khoa: string;
        khoaHoc: number;
        email: string;
      };

      const user: User = {
        username: s.maSv,
        name: s.hoTen,
        dept: `Lớp ${s.lop} · ${s.khoa}`,
        email: s.email,
        role: "sinhvien",
        maSv: s.maSv,
        lop: s.lop,
        khoa: s.khoa,
        khoaHoc: s.khoaHoc,
      };

      setState((prev) => ({ ...prev, user }));
      return { ok: true, message: "" };
    } catch (err) {
      return {
        ok: false,
        message: `Không gọi được máy chủ: ${(err as Error).message}`,
      };
    }
  }, []);

  const logout = useCallback(() => {
    setState((prev) => ({ ...prev, user: null }));
  }, []);

  const saveParams = useCallback((params: SolverParams) => {
    setState((prev) => ({ ...prev, params }));
  }, []);

  const clearResult = useCallback(() => {
    setState((prev) => ({ ...prev, result: null }));
  }, []);

  const runSolver = useCallback(async (params: SolverParams) => {
    try {
      const res = await fetch("/api/solve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(params),
      });
      const data = await res.json();

      if (!res.ok) {
        return { ok: false, message: data?.error ?? `Bộ giải trả về lỗi ${res.status}.` };
      }

      const result: SolveResult = {
        sessions: (data.sessions ?? []).map((s: Record<string, unknown>) => ({
          maLich: Number(s.ma_lich),
          maMon: String(s.ma_mon),
          maPhong: String(s.ma_phong),
          maKhung: Number(s.ma_khung),
        })),
        registrations: (data.registrations ?? []).map((r: Record<string, unknown>) => ({
          maSv: String(r.ma_sv),
          maLich: Number(r.ma_lich),
          soMay: Number(r.so_may),
          diem: r.diem === null || r.diem === undefined ? null : Number(r.diem),
        })),
        unscheduled: (data.unscheduled ?? []).map((u: Record<string, unknown>) => ({
          maSv: String(u.maSv),
          maMon: String(u.maMon),
        })),
        stats: {
          status: data.stats?.status ?? "UNKNOWN",
          solveTime: data.stats?.solve_time ?? 0,
          objective: data.stats?.objective ?? 0,
          bestBound: data.stats?.best_bound ?? 0,
          roomsOpened: data.stats?.rooms_opened ?? 0,
          sessions: data.stats?.sessions ?? 0,
          unscheduledSubjects: data.stats?.unscheduled_subjects ?? 0,
          Z1: data.stats?.Z1 ?? 0,
          Z2: data.stats?.Z2 ?? 0,
        },
        ranAt: new Date().toISOString(),
        params,
      };

      setState((prev) => ({ ...prev, params, result }));
      return { ok: true, message: "" };
    } catch (err) {
      return { ok: false, message: `Không gọi được API bộ giải: ${(err as Error).message}` };
    }
  }, []);

  const value = useMemo<AppState>(
    () => ({
      ...state,
      hydrated,
      login,
      logout,
      saveParams,
      runSolver,
      clearResult,
    }),
    [state, hydrated, login, logout, saveParams, runSolver, clearResult],
  );

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error("useApp phải dùng bên trong AppProvider");
  return ctx;
}
