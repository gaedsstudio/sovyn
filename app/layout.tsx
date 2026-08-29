import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

const siteDescription =
  "SOVYN is an open-source, local-first agent runtime for tools, workflows and reusable automation.";

export const metadata: Metadata = {
  metadataBase: new URL("https://sovyn.org"),
  title: {
    default: "SOVYN - Open-source agent infrastructure",
    template: "%s - SOVYN",
  },
  description: siteDescription,
  openGraph: {
    title: "SOVYN - Open-source agent infrastructure",
    description: siteDescription,
    url: "https://sovyn.org",
    siteName: "SOVYN",
    type: "website",
  },
  robots: {
    index: true,
    follow: true,
  },
};

const navLinks = [
  { href: "/hub", label: "Hub" },
  { href: "/docs", label: "Docs" },
  { href: "https://github.com/gaedsstudio/sovyn", label: "GitHub" },
  { href: "https://discord.gg/bxCnrFFcsg", label: "Discord" },
] as const;

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <div className="site-shell">
          <header className="header">
            <nav className="rail nav" aria-label="Primary navigation">
              <Link className="brand" href="/">
                SOVYN
              </Link>
              <div className="nav-links">
                {navLinks.map((link) => (
                  <Link key={link.href} href={link.href}>
                    {link.label}
                  </Link>
                ))}
              </div>
            </nav>
          </header>
          <main>{children}</main>
          <footer className="footer">
            <div className="rail split-grid">
              <div>
                <p className="eyebrow">Open source by default</p>
                <p className="muted">
                  Join developers, testers and users building SOVYN.
                </p>
              </div>
              <div className="nav-links">
                <Link href="https://github.com/gaedsstudio/sovyn">
                  View Source
                </Link>
                <Link href="https://github.com/gaedsstudio/sovyn/issues">
                  Report Issue
                </Link>
                <Link href="https://discord.gg/bxCnrFFcsg">Discord</Link>
                <Link href="/security">Security</Link>
              </div>
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
}
