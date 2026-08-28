import type { Metadata } from "next";
import Link from "next/link";
import type { ReactNode } from "react";
import "./globals.css";

export const metadata: Metadata = {
  title: "SOVYN Signal",
  description: "Understand what moved and why.",
};

const navItems = [
  { href: "/today", label: "Today" },
  { href: "/asset/NVDA", label: "Assets" },
  { href: "/watchlist", label: "Watchlist" },
  { href: "/ask", label: "Ask" },
] as const;

export default function RootLayout({ children }: { readonly children: ReactNode }) {
  return (
    <html lang="en">
      <body className="font-sans antialiased">
        <div className="min-h-[100dvh]">
          <header className="sticky top-0 z-20 border-b border-[var(--color-border)] bg-[color:rgba(8,9,10,0.92)] backdrop-blur">
            <nav className="mx-auto flex h-16 max-w-[1280px] items-center justify-between px-4 md:px-8">
              <Link href="/today" className="flex items-baseline gap-3">
                <span className="text-[15px] font-semibold tracking-[-0.01em] text-[var(--color-text)]">
                  SOVYN
                </span>
                <span className="hidden text-[12px] font-medium text-[var(--color-faint)] sm:inline">
                  Signal
                </span>
              </Link>
              <div className="flex items-center gap-1">
                {navItems.map((item) => (
                  <Link
                    href={item.href}
                    key={item.href}
                    className="rounded-[6px] px-3 py-2 text-[13px] font-medium text-[var(--color-muted)] transition hover:bg-[color:rgba(255,255,255,0.04)] hover:text-[var(--color-text)] active:translate-y-px"
                  >
                    {item.label}
                  </Link>
                ))}
              </div>
            </nav>
          </header>
          <main className="mx-auto max-w-[1280px] px-4 py-8 md:px-8">{children}</main>
        </div>
      </body>
    </html>
  );
}

