import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Izbori — dashboard",
  description: "Rezultati izbora u realnom vremenu",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="sr" className="h-full">
      <body
        className="min-h-full flex flex-col"
        style={{ fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, sans-serif" }}
      >
        {children}
      </body>
    </html>
  );
}
