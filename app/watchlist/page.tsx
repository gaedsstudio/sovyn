import { WatchlistManager } from "@/components/WatchlistManager";

export default function WatchlistPage() {
  return (
    <div className="space-y-8">
      <section className="border-b border-[var(--color-border)] pb-8">
        <p className="mb-3 text-[12px] font-medium uppercase tracking-[0.08em] text-[var(--color-faint)]">
          Watchlist
        </p>
        <h1 className="text-[48px] font-semibold leading-none tracking-[-0.04em]">
          Track what matters
        </h1>
        <p className="mt-4 max-w-[64ch] text-[15px] leading-6 text-[var(--color-muted)]">
          Add equities, indexes, commodities, FX, crypto, or indicators. Today
          uses watchlist relevance when ranking signals.
        </p>
      </section>
      <WatchlistManager />
    </div>
  );
}

