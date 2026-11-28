import { NextResponse } from "next/server";
import { findStudent } from "@/lib/repository";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/**
 * Đăng nhập sinh viên bằng mã số sinh viên.
 *
 * Quy ước: mật khẩu chính là MSSV (giống bản Streamlit cũ, để sinh viên không
 * phải nhớ thêm gì). Vì vậy route này KHÔNG phải một cơ chế xác thực thật sự —
 * nó chỉ xác nhận "mã này có trong danh sách sinh viên". Dữ liệu trả về cũng chỉ
 * gồm thông tin hiển thị được, không có số điện thoại hay điểm của người khác.
 *
 * Nếu sau này cần bảo mật thật, thay bằng mật khẩu riêng + session cookie.
 */
export async function POST(request: Request) {
  let body: { maSv?: unknown; password?: unknown };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Dữ liệu gửi lên không hợp lệ." }, { status: 400 });
  }

  const maSv = String(body.maSv ?? "").trim().toUpperCase();
  const password = String(body.password ?? "").trim();

  if (!maSv || !password) {
    return NextResponse.json(
      { error: "Vui lòng nhập đầy đủ mã sinh viên và mật khẩu." },
      { status: 400 },
    );
  }

  // Mật khẩu chính là MSSV, nên so không phân biệt hoa/thường: sinh viên gõ
  // "sv20210003" ở cả hai ô vẫn phải vào được.
  if (password.toUpperCase() !== maSv) {
    return NextResponse.json({ error: "Mật khẩu không đúng." }, { status: 401 });
  }

  try {
    const student = await findStudent(maSv);
    if (!student) {
      return NextResponse.json(
        { error: "Mã sinh viên không tồn tại trong hệ thống." },
        { status: 404 },
      );
    }
    return NextResponse.json({ student });
  } catch (err) {
    return NextResponse.json(
      {
        error: "Không tra được cơ sở dữ liệu.",
        detail: (err as Error).message,
      },
      { status: 503 },
    );
  }
}
