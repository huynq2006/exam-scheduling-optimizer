"use client";

import { useCallback, useEffect, useState } from "react";
import type { RosterEntry, StudentExamStatus } from "./types";

/* ==================================================================== */
/* Đọc danh sách sinh viên của một ca thi                               */
/* ==================================================================== */

export interface RosterPayload {
  maLich: number;
  roster: RosterEntry[];
  total: number;
  biCamThi: number;
  chuaNopHocPhi: number;
}

interface RosterState {
  data: RosterPayload | null;
  loading: boolean;
  error: string | null;
  reload: () => void;
}

/**
 * Danh sách dự thi của một ca. `maLich = null` thì không gọi gì cả, để mở
 * trang lịch thi không bắn một loạt request rỗng.
 */
export function useRoster(maLich: number | null): RosterState {
  const [data, setData] = useState<RosterPayload | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [nonce, setNonce] = useState(0);

  useEffect(() => {
    if (maLich === null) {
      setData(null);
      setLoading(false);
      setError(null);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    fetch(`/api/session/${maLich}/roster`, { cache: "no-store" })
      .then(async (res) => {
        const body = await res.json();
        if (!res.ok) throw new Error(body?.detail ?? body?.error ?? `Lỗi ${res.status}`);
        return body as RosterPayload;
      })
      .then((body) => {
        if (!cancelled) setData(body);
      })
      .catch((err: Error) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [maLich, nonce]);

  return { data, loading, error, reload: () => setNonce((n) => n + 1) };
}

/* ==================================================================== */
/* Đọc toàn bộ trạng thái (để tô màu ở màn hình lịch thi)               */
/* ==================================================================== */

interface AllStatusState {
  statuses: StudentExamStatus[];
  loading: boolean;
  error: string | null;
  reload: () => void;
}

export function useAllStatuses(): AllStatusState {
  const [statuses, setStatuses] = useState<StudentExamStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [nonce, setNonce] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetch("/api/exam-status", { cache: "no-store" })
      .then(async (res) => {
        const body = await res.json();
        if (!res.ok) throw new Error(body?.detail ?? body?.error ?? `Lỗi ${res.status}`);
        return body as { statuses: StudentExamStatus[] };
      })
      .then((body) => {
        if (!cancelled) setStatuses(body.statuses ?? []);
      })
      .catch((err: Error) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [nonce]);

  return { statuses, loading, error, reload: () => setNonce((n) => n + 1) };
}

/* ==================================================================== */
/* Ghi trạng thái                                                       */
/* ==================================================================== */

interface MutationState {
  busy: boolean;
  error: string | null;
  setError: (v: string | null) => void;
  /** Đặt trạng thái; trả về true nếu lưu được. */
  setStatus: (input: {
    maSv: string;
    maMon?: string | null;
    trangThai: "CHUA_NOP_HOC_PHI" | "CAM_THI";
    lyDo?: string | null;
  }) => Promise<boolean>;
  /** Bỏ đánh dấu. */
  clearStatus: (maSv: string, maMon?: string | null) => Promise<boolean>;
}

export function useStatusMutations(onChanged?: () => void): MutationState {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const setStatus = useCallback<MutationState["setStatus"]>(
    async (input) => {
      setBusy(true);
      setError(null);
      try {
        const res = await fetch("/api/exam-status", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(input),
        });
        const body = await res.json();
        if (!res.ok) throw new Error(body?.detail ?? body?.error ?? `Lỗi ${res.status}`);
        onChanged?.();
        return true;
      } catch (err) {
        setError((err as Error).message);
        return false;
      } finally {
        setBusy(false);
      }
    },
    [onChanged],
  );

  const clearStatus = useCallback<MutationState["clearStatus"]>(
    async (maSv, maMon) => {
      setBusy(true);
      setError(null);
      try {
        const qs = new URLSearchParams({ maSv });
        if (maMon) qs.set("maMon", maMon);
        const res = await fetch(`/api/exam-status?${qs.toString()}`, { method: "DELETE" });
        const body = await res.json();
        if (!res.ok) throw new Error(body?.detail ?? body?.error ?? `Lỗi ${res.status}`);
        onChanged?.();
        return true;
      } catch (err) {
        setError((err as Error).message);
        return false;
      } finally {
        setBusy(false);
      }
    },
    [onChanged],
  );

  return { busy, error, setError, setStatus, clearStatus };
}
