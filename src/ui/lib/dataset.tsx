"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import type { Enrollment, Room, Slot, Student, Subject } from "./types";

/**
 * Dữ liệu đầu vào lấy từ MySQL qua /api/dataset.
 *
 * Trước đây các trang import thẳng hằng số từ `lib/data.ts` (dữ liệu bịa trong
 * bundle). Giờ chúng đọc qua context này, nên mọi con số trên giao diện là dữ
 * liệu thật trong DB.
 */

export interface Dataset {
  subjects: Subject[];
  rooms: Room[];
  slots: Slot[];
  students: Student[];
  enrollment: Enrollment[];
}

interface DatasetState extends Dataset {
  loading: boolean;
  error: string | null;
  reload: () => void;
}

const EMPTY: Dataset = {
  subjects: [],
  rooms: [],
  slots: [],
  students: [],
  enrollment: [],
};

const DatasetContext = createContext<DatasetState | null>(null);

export function DatasetProvider({ children }: { children: React.ReactNode }) {
  const [data, setData] = useState<Dataset>(EMPTY);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [nonce, setNonce] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetch("/api/dataset", { cache: "no-store" })
      .then(async (res) => {
        const body = await res.json();
        if (!res.ok) throw new Error(body?.detail ?? body?.error ?? `Lỗi ${res.status}`);
        return body as Dataset;
      })
      .then((body) => {
        if (cancelled) return;
        setData({
          subjects: body.subjects ?? [],
          rooms: body.rooms ?? [],
          slots: body.slots ?? [],
          students: body.students ?? [],
          enrollment: body.enrollment ?? [],
        });
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

  const value = useMemo<DatasetState>(
    () => ({ ...data, loading, error, reload: () => setNonce((n) => n + 1) }),
    [data, loading, error],
  );

  return <DatasetContext.Provider value={value}>{children}</DatasetContext.Provider>;
}

export function useDataset(): DatasetState {
  const ctx = useContext(DatasetContext);
  if (!ctx) throw new Error("useDataset phải dùng bên trong DatasetProvider");
  return ctx;
}
