import { SignalRow } from "@/components/SignalRow";
import { getTodaySignals } from "@/lib/signals/demo";

export default function TodayPage() {
  const signals = getTodaySignals(["NVDA", "QQQ", "US10Y"]).slice(0, 6);
  return (
    <div className="space-y-8">
      <section className="grid gap-4 border-b border-[var(--color-border)] pb-8 md:grid-cols-[1fr_360px]">
        <div>
          <p className="mb-3 text-[12px] font-medium uppercase tracking-[0.08em] text-[var(--color-faint)]">
            Today
          </p>
          <h1 className="max-w-[780px] text-[44px] font-semibold leading-[1.03] tracking-[-0.04em] md:text-[56px]">
            {signals.length} meaningful changes today
          </h1>
        </div>
        <div className="rounded-[8px] border border-[var(--color-border)] bg-[color:rgba(255,255,255,0.025)] p-4">
          <div className="font-mono text-[13px] text-[var(--color-accent)]">
            3 changes matter to your watchlist.
          </div>
          <p className="mt-3 text-[14px] leading-6 text-[var(--color-muted)]">
            Demo mode prioritizes NVDA, QQQ, and US10Y so the full Signal workflow
            is available without external credentials.
          </p>
        </div>
      </section>
      <section className="space-y-3">
        {signals.map((signal, index) => (
          <SignalRow key={signal.id} rank={index + 1} signal={signal} />
        ))}
      </section>
    </div>
  );
}

