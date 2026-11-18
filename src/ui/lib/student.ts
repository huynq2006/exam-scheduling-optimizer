"use client";

import { useEffect, useState } from "react";
import type { StudentExam } from "./types";

export interface StudentSchedulePayload {
  student: {
    maSv: string;
    hoTen: string;
    lop: string;
    khoa: string;
    khoaHoc: number;
    email: string;
    gioiTinh: string;
    ngaySinh: string;
  };
  exams: StudentExam[];
  published: boolean;
}

interface State {
  data: StudentSchedulePayload | null;
  loading: boolean;
  error: string | null;
  reload: () => void;
}

/**
 * Lịch thi cá nhân, đọc từ /api/student/[maSv]/schedule.
 *
 * Chỉ trả các ca trong phương án đã công bố, nên `exams` rỗng có thể vì hai lý do:
 * sinh viên không đăng ký môn nào, hoặc Phòng Đào tạo chưa công bố lịch.
 */
export function useStudentSchedule(maSv: string | undefined): State {
  const [data, setData] = useState<StudentSchedulePayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [nonce, setNonce] = useState(0);

  useEffect(() => {
    if (!maSv) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetch(`/api/student/${encodeURIComponent(maSv)}/schedule`, { cache: "no-store" })
      .then(async (res) => {
        const body = await res.json();
        if (!res.ok) throw new Error(body?.detail ?? body?.error ?? `Lỗi ${res.status}`);
        return body as StudentSchedulePayload;
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
  }, [maSv, nonce]);

  return { data, loading, error, reload: () => setNonce((n) => n + 1) };
}
