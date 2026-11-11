"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { LockKeyhole, User2 } from "lucide-react";
import { useApp } from "@/lib/store";
import { Button, Field, inputClass } from "@/components/ui";

export default function LoginPage() {
  const { user, hydrated, login } = useApp();
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!hydrated || !user) return;
    router.replace(user.role === "sinhvien" ? "/my-exams" : "/dashboard");
  }, [hydrated, user, router]);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (busy) return;
    setBusy(true);
    setError(null);
    const result = await login(username, password);
    setBusy(false);
    if (!result.ok) {
      setError(result.message);
      return;
    }
    // Điều hướng do useEffect ở trên đảm nhiệm, sau khi user đã vào state.
  }

  return (
    <div className="grid min-h-screen place-items-center px-4 py-10">
      <div className="w-full max-w-[380px]">
        <div className="mb-6 flex items-center gap-2.5">
          <span className="grid h-9 w-9 place-items-center rounded-lg bg-accent-600 text-[13px] font-bold text-white">LT</span>
          <div className="leading-tight">
            <p className="text-[14px] font-semibold tracking-tight text-ink-900">Xếp lịch thi</p>
            <p className="text-[11.5px] text-ink-400">Phòng Đào tạo</p>
          </div>
        </div>

        <form onSubmit={onSubmit} className="surface p-5">
          <h1 className="text-[17px] font-semibold tracking-tight text-ink-900">Đăng nhập</h1>

          <div className="mt-4 space-y-3">
            <Field label="Mã sinh viên">
              <div className="relative">
                <User2 className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-300" />
                <input
                  value={username}
                  onChange={(e) => {
                    setUsername(e.target.value);
                    setError(null);
                  }}
                  autoComplete="username"
                  autoFocus
                  placeholder="SV20210003"
                  className={`${inputClass} pl-9`}
                />
              </div>
            </Field>

            <Field label="Mật khẩu">
              <div className="relative">
                <LockKeyhole className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-300" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => {
                    setPassword(e.target.value);
                    setError(null);
                  }}
                  autoComplete="current-password"
                  placeholder="••••••"
                  className={`${inputClass} pl-9`}
                />
              </div>
            </Field>
          </div>

          {error ? (
            <p className="mt-3 rounded-lg bg-rose-50 px-3 py-2 text-[12.5px] text-rose-700 ring-1 ring-inset ring-rose-200">
              {error}
            </p>
          ) : null}

          <Button type="submit" variant="primary" className="mt-4 w-full" disabled={busy}>
            {busy ? "Đang kiểm tra…" : "Đăng nhập"}
          </Button>
        </form>
      </div>
    </div>
  );
}
