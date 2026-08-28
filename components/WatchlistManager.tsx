"use client";

import { useMemo, useState } from "react";
import { demoAssets } from "@/lib/market/mock-data";

const defaultSymbols = ["NVDA", "QQQ", "US10Y"];

export function WatchlistManager() {
  const [symbols, setSymbols] = useState<readonly string[]>(defaultSymbols);
  const [draft, setDraft] = useState("");
  const assetsBySymbol = useMemo(() => {
    return new Map(demoAssets.map((asset) => [asset.symbol, asset]));
  }, []);
  const addSymbol = () => {
    const normalized = draft.trim().toUpperCase();
    if (!assetsBySymbol.has(normalized) || symbols.includes(normalized)) {
      return;
    }
    setSymbols([...symbols, normalized]);
    setDraft("");
  };
  return (
    <section className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row">
        <label className="flex flex-1 flex-col gap-2 text-[13px] text-[var(--color-muted)]">
          Track symbol
          <input
            className="rounded-[6px] border border-[var(--color-border)] bg-[color:rgba(255,255,255,0.025)] px-3 py-2 text-[14px] text-[var(--color-text)]"
            onChange={(event) => {
              setDraft(event.target.value);
            }}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                addSymbol();
              }
            }}
            placeholder="NVDA, USD/KRW, US10Y"
            value={draft}
          />
        </label>
        <button
          className="self-end rounded-[6px] border border-[color:rgba(113,112,255,0.45)] bg-[var(--color-accent)] px-4 py-2 text-[14px] font-medium text-white transition active:translate-y-px"
          onClick={addSymbol}
          type="button"
        >
          Add
        </button>
      </div>
      <div className="divide-y divide-[var(--color-border)] rounded-[8px] border border-[var(--color-border)]">
        {symbols.map((symbol) => {
          const asset = assetsBySymbol.get(symbol);
          return (
            <div className="flex items-center justify-between gap-4 p-4" key={symbol}>
              <div>
                <div className="font-mono text-[14px] text-[var(--color-text)]">{symbol}</div>
                <div className="text-[13px] text-[var(--color-faint)]">
                  {asset?.name ?? "Unknown asset"}
                </div>
              </div>
              <button
                className="rounded-[6px] border border-[var(--color-border)] px-3 py-1.5 text-[13px] text-[var(--color-muted)] transition hover:text-[var(--color-text)] active:translate-y-px"
                onClick={() => {
                  setSymbols(symbols.filter((item) => item !== symbol));
                }}
                type="button"
              >
                Remove
              </button>
            </div>
          );
        })}
      </div>
    </section>
  );
}

