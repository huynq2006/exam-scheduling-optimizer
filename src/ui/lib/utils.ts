import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(iso: string) {
  const [y, m, d] = iso.split("-");
  return `${d}/${m}/${y}`;
}

export function formatDateTime(iso: string) {
  const dt = new Date(iso);
  if (Number.isNaN(dt.getTime())) return iso;
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(dt.getHours())}:${pad(dt.getMinutes())} ${pad(dt.getDate())}/${pad(dt.getMonth() + 1)}/${dt.getFullYear()}`;
}

export const WEEKDAY = ["Chủ nhật", "Thứ hai", "Thứ ba", "Thứ tư", "Thứ năm", "Thứ sáu", "Thứ bảy"];

export function weekdayOf(iso: string) {
  const dt = new Date(`${iso}T00:00:00`);
  return WEEKDAY[dt.getDay()];
}

export const HINH_THUC_LABEL: Record<string, string> = {
  "On-screen": "Thi trên máy",
  "Computer-based test": "Trắc nghiệm trên máy",
  Practical: "Thực hành",
};

export function percent(part: number, total: number) {
  if (!total) return 0;
  return Math.round((part / total) * 1000) / 10;
}

/** f[c,r] = phòng cài đủ toàn bộ phần mềm môn cần. */
export function isCompatible(subjectPhanMem: string[], roomPhanMem: string[]) {
  return subjectPhanMem.every((pm) => roomPhanMem.includes(pm));
}

/** Số phút của một khung giờ, dùng để kiểm tra thời lượng môn có vừa khung không. */
export function slotMinutes(gioBd: string, gioKt: string) {
  const [bh, bm] = gioBd.split(":").map(Number);
  const [kh, km] = gioKt.split(":").map(Number);
  return kh * 60 + km - (bh * 60 + bm);
}
