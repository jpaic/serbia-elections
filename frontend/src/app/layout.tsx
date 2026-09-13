import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Izbori — dashboard",
  description: "Rezultati izbora u realnom vremenu",
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
