import { notFound } from "next/navigation";
import { WhatHappenedHere } from "@/components/WhatHappenedHere";
import { findAsset, getDemoObservations } from "@/lib/market/mock-data";
import { marketProvider } from "@/lib/market/provider";
import { getAssetSignals } from "@/lib/signals/demo";
import { formatPercent } from "@/lib/utils/format";

type AssetPageProps = {
  readonly params: Promise<{
    readonly symbol: string;
  }>;
};

export default async function AssetPage({ params }: AssetPageProps) {
  const { symbol } = await params;
  const asset = findAsset(symbol);
  if (asset === undefined) {
    notFound();
  }
  const quote = await marketProvider.getQuote(asset.symbol);
  const observations = getDemoObservations(asset.id);
  const signals = getAssetSignals(asset.symbol);
  if (quote === undefined) {
    notFound();
  }
  return (
    <div className="space-y-8">
      <section className="grid gap-4 border-b border-[var(--color-border)] pb-8 md:grid-cols-[1fr_320px]">
        <div>
          <p className="mb-3 text-[12px] font-medium uppercase tracking-[0.08em] text-[var(--color-faint)]">
            Asset
          </p>
          <h1 className="text-[48px] font-semibold leading-none tracking-[-0.04em]">
            {asset.name}
          </h1>
          <p className="mt-4 max-w-[60ch] text-[15px] leading-6 text-[var(--color-muted)]">
            Why is {asset.symbol} moving? SOVYN links unusual moves to relevant
            market events and impact rules.
          </p>
        </div>
        <div className="rounded-[8px] border border-[var(--color-border)] bg-[color:rgba(255,255,255,0.025)] p-4">
          <div className="font-mono text-[32px] tracking-[-0.04em]">
            {quote.value.toFixed(2)}
          </div>
          <div className="mt-2 font-mono text-[14px] text-[var(--color-muted)]">
            {formatPercent(quote.percentageChange)}
          </div>
        </div>
      </section>
      <section className="space-y-4">
        <h2 className="text-[20px] font-semibold tracking-[-0.02em]">
          What happened here?
        </h2>
        <WhatHappenedHere observations={observations} signals={signals} />
      </section>
    </div>
  );
}

