import type { Metadata } from "next";
import "./globals.css";
import { ThemeProvider } from "@/lib/theme";

export const metadata: Metadata = {
  title: "Serbia Election Dashboard",
  description: "Rezultati parlamentarnih izbora Srbije 2000–2026 po regionima i opštinama",
  icons: { icon: "/logo.svg" },
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="sr" className="h-full">
      <head>
        <meta name="color-scheme" content="light dark" />
      </head>
      <body className="h-full flex flex-col overflow-hidden">
        <ThemeProvider>{children}</ThemeProvider>
      </body>
    </html>
  );
}
