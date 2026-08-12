import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Stock Intelligence",
  description: "Nền tảng phân tích & dự đoán chứng khoán HOSE",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="vi">
      <body className="min-h-screen bg-neutral-950 text-neutral-100 antialiased">
        <header className="border-b border-neutral-800">
          <div className="mx-auto flex max-w-6xl items-center gap-6 px-6 py-4">
            <Link href="/" className="font-mono text-sm font-bold tracking-wide text-neutral-100">
              STOCK INTELLIGENCE
            </Link>
            <nav className="flex gap-4 text-sm text-neutral-400">
              <Link href="/" className="hover:text-neutral-100">
                Tổng quan
              </Link>
              <Link href="/watchlist" className="hover:text-neutral-100">
                Watchlist
              </Link>
              <Link href="/portfolio" className="hover:text-neutral-100">
                Danh mục ảo
              </Link>
              <Link href="/huong-dan" className="hover:text-neutral-100">
                Hướng dẫn
              </Link>
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
