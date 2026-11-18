import { NextResponse } from "next/server";
import { fetchRoster } from "@/lib/status";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/**
 * Danh sách sinh viên của một ca thi, kèm trạng thái dự thi.
 *
 * Sinh viên bị cấm thi vẫn nằm trong danh sách: phòng thi cần đủ người để
 * đối chiếu giấy tờ, trạng thái chỉ để tô màu và ghi chú.
 */
export async function GET(
  _request: Request,
  { params }: { params: Promise<{ maLich: string }> },
) {
  const { maLich: raw } = await params;
  const maLich = Number(raw);

  if (!Number.isInteger(maLich) || maLich <= 0) {
    return NextResponse.json({ error: "Mã ca thi không hợp lệ." }, { status: 400 });
  }

  try {
    const roster = await fetchRoster(maLich);
    return NextResponse.json({
      maLich,
      roster,
      total: roster.length,
      biCamThi: roster.filter((r) => r.trangThai === "CAM_THI").length,
      chuaNopHocPhi: roster.filter((r) => r.trangThai === "CHUA_NOP_HOC_PHI").length,
    });
  } catch (err) {
    return NextResponse.json(
      { error: "Không đọc được danh sách sinh viên của ca thi.", detail: (err as Error).message },
      { status: 503 },
    );
  }
}
