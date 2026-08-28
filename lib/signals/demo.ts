import { generateSignals } from "@/engine/pipeline/signal-pipeline";
import { demoAssets, getDemoObservations } from "@/lib/market/mock-data";
import type { Observation, Signal } from "@/lib/signals/types";

export function buildDemoHistories(): ReadonlyMap<string, readonly Observation[]> {
  return new Map(demoAssets.map((asset) => [asset.id, getDemoObservations(asset.id)]));
}

export function getTodaySignals(watchlistSymbols: readonly string[] = []): readonly Signal[] {
  return generateSignals(demoAssets, buildDemoHistories(), watchlistSymbols);
}

export function getAssetSignals(symbol: string): readonly Signal[] {
  const normalized = symbol.toUpperCase();
  return getTodaySignals([normalized]).filter((signal) => {
    return (
      signal.asset.symbol === normalized ||
      signal.impacts.some((impact) => impact.symbol === normalized)
    );
  });
}

