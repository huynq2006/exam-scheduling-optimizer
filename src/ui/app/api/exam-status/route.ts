import { NextResponse } from "next/server";
import { clearStatus, fetchAllStatuses, upsertStatus } from "@/lib/status";
import type { ExamStatus } from "@/lib/types";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const VALID: ExamStatus[] = ["CHUA_NOP_HOC_PHI", "CAM_THI"];

/** Toàn bộ trạng thái đang có hiệu lực. */
export async function GET() {
  try {
    const statuses = await fetchAllStatuses();
    return NextResponse.json({ statuses });
  } catch (err) {
    return NextResponse.json(
      { error: "Không đọc được trạng thái dự thi.", detail: (err as Error).message },
      { status: 503 },
    );
  }
}

/** Đặt hoặc cập nhật trạng thái cho một sinh viên. */
export async function POST(request: Request) {
  let body: {
    maSv?: string;
    maMon?: string | null;
    trangThai?: string;
    lyDo?: string | null;
  };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Body không phải JSON hợp lệ." }, { status: 400 });
  }

  const maSv = String(body.maSv ?? "").trim().toUpperCase();
  if (!maSv) {
    return NextResponse.json({ error: "Thiếu mã sinh viên." }, { status: 400 });
  }

  const trangThai = body.trangThai as ExamStatus;
  if (!VALID.includes(trangThai)) {
    return NextResponse.json(
      { error: `Trạng thái không hợp lệ. Chỉ nhận: ${VALID.join(", ")}.` },
      { status: 400 },
    );
  }

  const maMon = body.maMon ? String(body.maMon).trim().toUpperCase() : null;
  const lyDo = body.lyDo ? String(body.lyDo).trim().slice(0, 255) : null;

  try {
    await upsertStatus({ maSv, maMon, trangThai, lyDo }, "THU_CONG");
    return NextResponse.json({ ok: true, maSv, maMon, trangThai });
  } catch (err) {
    return NextResponse.json(
      { error: "Không lưu được trạng thái.", detail: (err as Error).message },
      { status: 503 },
    );
  }
}

/** Bỏ đánh dấu, đưa sinh viên về trạng thái bình thường. */
export async function DELETE(request: Request) {
  const url = new URL(request.url);
  const maSv = (url.searchParams.get("maSv") ?? "").trim().toUpperCase();
  const maMonRaw = url.searchParams.get("maMon");
  const maMon = maMonRaw ? maMonRaw.trim().toUpperCase() : null;

  if (!maSv) {
    return NextResponse.json({ error: "Thiếu mã sinh viên." }, { status: 400 });
  }

  try {
    await clearStatus(maSv, maMon);
    return NextResponse.json({ ok: true, maSv, maMon });
  } catch (err) {
    return NextResponse.json(
      { error: "Không xoá được trạng thái.", detail: (err as Error).message },
      { status: 503 },
    );
  }
}
