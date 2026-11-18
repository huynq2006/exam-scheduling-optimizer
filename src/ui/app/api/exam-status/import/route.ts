import { NextResponse } from "next/server";
import { commitImport, fetchImportLog, previewImport } from "@/lib/status";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/** Kích thước tối đa của một file cấm thi. Danh sách thật chỉ vài trăm KB. */
const MAX_BYTES = 5 * 1024 * 1024;

/** Lịch sử các lần nạp, để đối chiếu khi sinh viên khiếu nại. */
export async function GET() {
  try {
    const rows = await fetchImportLog();
    return NextResponse.json({ history: rows });
  } catch (err) {
    return NextResponse.json(
      { error: "Không đọc được lịch sử nạp danh sách.", detail: (err as Error).message },
      { status: 503 },
    );
  }
}

/**
 * Nạp danh sách cấm thi từ CSV.
 *
 * `mode=preview` chỉ đọc và đối chiếu, không ghi gì. `mode=commit` mới thật
 * sự ghi. Tách hai bước để người dùng thấy được dòng nào sai trước khi dữ
 * liệu thật bị thay đổi.
 */
export async function POST(request: Request) {
  let form: FormData;
  try {
    form = await request.formData();
  } catch {
    return NextResponse.json(
      { error: "Dữ liệu gửi lên phải là multipart/form-data có file CSV." },
      { status: 400 },
    );
  }

  const file = form.get("file");
  if (!(file instanceof File)) {
    return NextResponse.json({ error: "Thiếu file CSV." }, { status: 400 });
  }
  if (file.size === 0) {
    return NextResponse.json({ error: "File rỗng." }, { status: 400 });
  }
  if (file.size > MAX_BYTES) {
    return NextResponse.json(
      { error: `File quá lớn (${Math.round(file.size / 1024)} KB). Giới hạn 5 MB.` },
      { status: 413 },
    );
  }

  const mode = String(form.get("mode") ?? "preview");
  const nguoiImport = form.get("nguoiImport");

  let text: string;
  try {
    text = await file.text();
  } catch (err) {
    return NextResponse.json(
      { error: "Không đọc được nội dung file.", detail: (err as Error).message },
      { status: 400 },
    );
  }

  try {
    if (mode === "commit") {
      const result = await commitImport(
        file.name,
        text,
        typeof nguoiImport === "string" && nguoiImport.trim() ? nguoiImport.trim() : null,
      );
      return NextResponse.json({ mode: "commit", ...result });
    }

    const preview = await previewImport(file.name, text);
    return NextResponse.json({ mode: "preview", ...preview });
  } catch (err) {
    return NextResponse.json(
      {
        error: "Không xử lý được file CSV.",
        detail: (err as Error).message,
      },
      { status: 503 },
    );
  }
}
