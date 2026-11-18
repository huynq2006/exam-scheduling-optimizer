import { NextResponse } from "next/server";
import { fetchStudentExams, findStudent } from "@/lib/repository";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/**
 * Lịch thi cá nhân của một sinh viên: chỉ các ca trong phương án ĐÃ CÔNG BỐ.
 *
 * Trả kèm thông tin sinh viên để trang lịch không phải gọi hai lần.
 */
export async function GET(
  _request: Request,
  { params }: { params: Promise<{ maSv: string }> },
) {
  const { maSv: raw } = await params;
  const maSv = decodeURIComponent(raw ?? "").trim().toUpperCase();

  if (!maSv) {
    return NextResponse.json({ error: "Thiếu mã sinh viên." }, { status: 400 });
  }

  try {
    const [student, exams] = await Promise.all([findStudent(maSv), fetchStudentExams(maSv)]);

    if (!student) {
      return NextResponse.json(
        { error: "Mã sinh viên không tồn tại trong hệ thống." },
        { status: 404 },
      );
    }

    return NextResponse.json({
      student,
      exams,
      published: exams.length > 0,
      fetchedAt: new Date().toISOString(),
    });
  } catch (err) {
    return NextResponse.json(
      {
        error: "Không đọc được lịch thi từ cơ sở dữ liệu.",
        detail: (err as Error).message,
      },
      { status: 503 },
    );
  }
}
