import type { PackageRecord, PublisherRecord } from "./types";

export const publishers = [
  {
    id: "gaedsstudio",
    slug: "gaedsstudio",
    displayName: "Gaeds Studio",
    github: "https://github.com/gaedsstudio",
    website: "https://sovyn.org",
    verified: true,
    verifiedAt: "2026-08-29T00:00:00.000Z",
    verificationLevel: "release",
  },
] as const satisfies readonly PublisherRecord[];

export const packages = [
  {
    slug: "sovyn-core",
    name: "SOVYN Core",
    description:
      "Open-source terminal agent runtime with local-first tools, permissions, and reusable workflows.",
    publisher: "gaedsstudio",
    status: "verified",
    version: "0.1.0a1",
    license: "MIT",
    tags: ["agent", "terminal", "local-first", "workflow", "ollama"],
    source: {
      repository: "https://github.com/gaedsstudio/sovyn",
      commit: "2bf6d3e02393c9bef8013b0432dd17c5c45cbabc",
      releaseTag: "v0.1.0a1",
    },
    permissions: {
      summary: ["READ", "WRITE", "SHELL", "NETWORK optional"],
      filesystem: {
        read: ["workspace/**"],
        write: ["workspace/** after approval"],
      },
      shell: ["user-approved commands"],
      network: ["provider APIs when configured", "explicit http.get approvals"],
    },
    platforms: ["Windows", "macOS", "Linux"],
    installCommand: "git clone https://github.com/gaedsstudio/sovyn.git",
    readme:
      "SOVYN Core is the first-party runtime. It runs in the terminal, uses local or compatible models, requests permissions before sensitive tools, and records successful work as editable workflows.",
    securityNotes: [
      "Verified means publisher, source, release, manifest, and permissions were reviewed.",
      "Verified does not mean guaranteed safe or permanently endorsed.",
      "Users should inspect source and permissions before running workflows.",
    ],
  },
] as const satisfies readonly PackageRecord[];
