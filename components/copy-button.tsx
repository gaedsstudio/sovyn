"use client";

import { useState } from "react";

export function CopyButton({ value }: Readonly<{ value: string }>) {
  const [copied, setCopied] = useState(false);

  async function copyValue() {
    await navigator.clipboard.writeText(value);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1600);
  }

  return (
    <button className="button" type="button" onClick={copyValue}>
      {copied ? "Copied" : "Copy"}
    </button>
  );
}
