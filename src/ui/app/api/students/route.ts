import { NextResponse } from "next/server";
import { fetchClasses, searchStudents } from "@/lib/status";
import type { ExamStatus } from "@/lib/types";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const STATUS_FILTERS = ["CHUA_NOP_HOC_PHI", "CAM_THI", "BINH_THUONG"] as const;

/**
 * Truy vấn sinh viên theo mã, họ tên, lớp, học phần và trạng thái.
 *
 * Một endpoint dùng chung cho cả ba tab tra cứu: danh sách chung, chưa nộp
 * học phí, bị cấm thi. Khác nhau chỉ ở tham số `trangThai`.
 */
export async function GET(request: Request) {
  const url = new URL(request.url);
  const keyword = url.searchParams.get("q") ?? undefined;
  const maMon = url.searchParams.get("maMon") ?? undefined;
  const lop = url.searchParams.get("lop") ?? undefined;
  const rawStatus = url.searchParams.get("trangThai");
  const limitRaw = Number(url.searchParams.get("limit") ?? "200");

  let trangThai: ExamStatus | "BINH_THUONG" | undefined;
  if (rawStatus) {
    if (!STATUS_FILTERS.includes(rawStatus as (typeof STATUS_FILTERS)[number])) {
      return NextResponse.json(
        { error: `trangThai phải là một trong: ${STATUS_FILTERS.join(", ")}` },
        { status: 400 },
      );
    }
    trangThai = rawStatus as ExamStatus | "BINH_THUONG";
  }

  try {
    const [rows, classes] = await Promise.all([
      searchStudents({
        keyword,
        maMon,
        lop,
        trangThai,
        limit: Number.isFinite(limitRaw) ? limitRaw : 200,
      }),
      fetchClasses(),
    ]);

    return NextResponse.json({
      students: rows,
      classes,
      total: rows.length,
      fetchedAt: new Date().toISOString(),
    });
  } catch (err) {
    return NextResponse.json(
      { error: "Không truy vấn được danh sách sinh viên.", detail: (err as Error).message },
      { status: 503 },
    );
  }
}
