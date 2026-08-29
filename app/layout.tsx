import type { Metadata } from "next";
import { JetBrains_Mono, Plus_Jakarta_Sans } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const siteDescription =
  "SOVYN is an open-source, local-first agent runtime for tools, workflows and reusable automation.";

const sans = Plus_Jakarta_Sans({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

const mono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
});

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
    <html className={`${sans.variable} ${mono.variable}`} lang="en">
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
              <Link
                className="button primary nav-cta"
                href="https://github.com/gaedsstudio/sovyn"
              >
                Get Started
              </Link>
            </nav>
          </header>
          <main>{children}</main>
          <footer className="footer">
            <div className="rail split-grid">
              <div>
                <p className="footer-brand">SOVYN</p>
                <p className="muted">Open Source Agent Infrastructure</p>
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
