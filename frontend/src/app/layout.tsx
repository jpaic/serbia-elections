import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Serbia Election Dashboard",
  description: "Rezultati parlamentarnih izbora Srbije 2000–2026 po regionima i opštinama",
  icons: { icon: "/logo.svg" },
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="sr" className="h-full">
      <body className="h-full flex flex-col overflow-hidden bg-[#0b0d12] text-[#f2f3f5]">
        {children}
      </body>
    </html>
  );
}
