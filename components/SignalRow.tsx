import Link from "next/link";
import type { Signal } from "@/lib/signals/types";
import { formatChange, formatScore, formatValue } from "@/lib/utils/format";

type SignalRowProps = {
  readonly signal: Signal;
  readonly rank: number;
};

export function SignalRow({ signal, rank }: SignalRowProps) {
  const topImpacts = signal.impacts.slice(0, 3);
  return (
    <Link
      href={`/asset/${signal.asset.symbol}`}
      className="grid gap-4 rounded-[8px] border border-[var(--color-border)] bg-[color:rgba(255,255,255,0.025)] p-4 transition hover:border-[color:rgba(113,112,255,0.45)] hover:bg-[color:rgba(255,255,255,0.045)] md:grid-cols-[56px_1.2fr_1fr_112px]"
    >
      <div className="font-mono text-[12px] text-[var(--color-faint)]">
        {String(rank).padStart(2, "0")}
      </div>
      <div className="space-y-2">
        <div className="text-[12px] font-medium uppercase tracking-[0.08em] text-[var(--color-faint)]">
          {signal.asset.group.replaceAll("_", " ")}
        </div>
        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
          <span className="text-[22px] font-semibold tracking-[-0.02em]">
            {signal.asset.symbol}
          </span>
          <span className="font-mono text-[14px] text-[var(--color-muted)]">
            {formatValue(signal.event.magnitude)}
          </span>
          <span className="font-mono text-[13px] text-[var(--color-muted)]">
            {formatChange(signal.event.direction)}
          </span>
        </div>
        <p className="max-w-[58ch] text-[14px] leading-6 text-[var(--color-muted)]">
          {signal.explanation.fact}
        </p>
      </div>
      <div className="space-y-2">
        <div className="text-[12px] font-medium uppercase tracking-[0.08em] text-[var(--color-faint)]">
          Impact
        </div>
        <div className="space-y-1">
          {topImpacts.map((impact) => (
            <div
              className="flex items-center justify-between gap-3 text-[13px]"
              key={`${signal.id}-${impact.assetId}`}
            >
              <span className="text-[var(--color-muted)]">{impact.symbol}</span>
              <span className="font-mono text-[var(--color-text)]">
                {impact.direction}
              </span>
            </div>
          ))}
        </div>
      </div>
      <div className="space-y-2 md:text-right">
        <div className="text-[12px] font-medium uppercase tracking-[0.08em] text-[var(--color-faint)]">
          Confidence
        </div>
        <div className="font-mono text-[28px] tracking-[-0.04em]">
          {formatScore(signal.score.total)}
        </div>
        <div className="font-mono text-[12px] text-[var(--color-faint)]">
          {(signal.score.confidence * 100).toFixed(0)}%
        </div>
      </div>
    </Link>
  );
}

