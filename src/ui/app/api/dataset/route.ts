import { NextResponse } from "next/server";
import { fetchDataset } from "@/lib/repository";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/** Trả toàn bộ dữ liệu đầu vào (học phần, phòng, khung giờ, sinh viên, đăng ký) từ MySQL. */
export async function GET() {
  try {
    const dataset = await fetchDataset();
    return NextResponse.json({
      ...dataset,
      source: "mysql",
      fetchedAt: new Date().toISOString(),
    });
  } catch (err) {
    return NextResponse.json(
      {
        error: "Không đọc được dữ liệu từ MySQL.",
        detail: (err as Error).message,
      },
      { status: 503 },
    );
  }
}
