import type { Metadata, Viewport } from "next";
import "./globals.css";
import { AppProvider } from "@/lib/store";
import { DatasetProvider } from "@/lib/dataset";

export const metadata: Metadata = {
  title: "Xếp lịch thi · Phòng Đào tạo",
  description:
    "Hệ thống xếp lịch thi và phòng máy cho Phòng Đào tạo: kiểm tra dữ liệu, xếp lịch thi, xem và dùng lịch đã xếp.",
};

export const viewport: Viewport = {
  themeColor: "#F7F8FA",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi">
      <body>
        <DatasetProvider>
          <AppProvider>{children}</AppProvider>
        </DatasetProvider>
      </body>
    </html>
  );
}
