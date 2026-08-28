import { demoAssets, findAsset, getDemoObservations } from "@/lib/market/mock-data";
import type { Asset, Observation } from "@/lib/signals/types";

export type Quote = {
  readonly asset: Asset;
  readonly value: number;
  readonly change: number;
  readonly percentageChange: number;
  readonly timestamp: Date;
};

export type TimeRange = "1M" | "3M" | "1Y";

export interface MarketProvider {
  getQuote(symbol: string): Promise<Quote | undefined>;
  getHistory(symbol: string, range: TimeRange): Promise<readonly Observation[]>;
  searchAssets(query: string): Promise<readonly Asset[]>;
}

export class MockMarketProvider implements MarketProvider {
  async getQuote(symbol: string): Promise<Quote | undefined> {
    const asset = findAsset(symbol);
    if (asset === undefined) {
      return undefined;
    }
    const history = getDemoObservations(asset.id);
    const latest = history.at(-1);
    const previous = history.at(-2);
    if (latest === undefined || previous === undefined) {
      return undefined;
    }
    const change = latest.value - previous.value;
    return {
      asset,
      value: latest.value,
      change,
      percentageChange: previous.value === 0 ? 0 : change / previous.value,
      timestamp: latest.timestamp,
    };
  }

  async getHistory(symbol: string, _range: TimeRange): Promise<readonly Observation[]> {
    const asset = findAsset(symbol);
    return asset === undefined ? [] : getDemoObservations(asset.id);
  }

  async searchAssets(query: string): Promise<readonly Asset[]> {
    const normalized = query.trim().toUpperCase();
    if (normalized === "") {
      return demoAssets;
    }
    return demoAssets.filter((asset) => {
      return (
        asset.symbol.toUpperCase().includes(normalized) ||
        asset.name.toUpperCase().includes(normalized)
      );
    });
  }
}

export const marketProvider = new MockMarketProvider();

