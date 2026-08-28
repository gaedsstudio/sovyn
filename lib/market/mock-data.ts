import type { Asset, Observation } from "@/lib/signals/types";

export const demoAssets: readonly Asset[] = [
  { id: "spy", symbol: "SPY", name: "S&P 500 ETF", type: "index", group: "broad_equities" },
  { id: "qqq", symbol: "QQQ", name: "NASDAQ 100 ETF", type: "index", group: "growth_equities" },
  { id: "nvda", symbol: "NVDA", name: "NVIDIA", type: "equity", group: "semiconductors" },
  { id: "amd", symbol: "AMD", name: "AMD", type: "equity", group: "semiconductors" },
  { id: "btc", symbol: "BTC", name: "Bitcoin", type: "crypto", group: "crypto" },
  { id: "gold", symbol: "GOLD", name: "Gold", type: "commodity", group: "precious_metals" },
  { id: "oil", symbol: "OIL", name: "Crude Oil", type: "commodity", group: "energy" },
  { id: "dxy", symbol: "DXY", name: "US Dollar Index", type: "fx", group: "usd" },
  { id: "usdkrw", symbol: "USD/KRW", name: "US Dollar Korean Won", type: "fx", group: "usd_asia_fx" },
  { id: "us2y", symbol: "US2Y", name: "US 2Y Treasury Yield", type: "indicator", group: "rates" },
  { id: "us10y", symbol: "US10Y", name: "US 10Y Treasury Yield", type: "indicator", group: "rates" },
] as const;

const baseDate = Date.UTC(2026, 7, 27);

const seedValues: Record<string, readonly number[]> = {
  spy: [641, 642, 640, 644, 646, 645, 649, 651, 650, 647, 644, 641, 638, 642, 639, 636, 632, 628, 625, 621, 617],
  qqq: [602, 604, 606, 608, 611, 609, 612, 615, 617, 612, 608, 603, 597, 602, 598, 593, 585, 579, 572, 566, 558],
  nvda: [178, 181, 183, 184, 187, 186, 190, 193, 195, 190, 188, 184, 181, 186, 182, 179, 176, 172, 170, 168, 164],
  amd: [169, 170, 172, 171, 174, 173, 175, 178, 177, 174, 171, 168, 166, 169, 165, 162, 159, 156, 154, 151, 148],
  btc: [112000, 113200, 111900, 114100, 115000, 114300, 116400, 117200, 116900, 115600, 114800, 113900, 112400, 111700, 110900, 109500, 108200, 106900, 105700, 104600, 103100],
  gold: [3360, 3368, 3374, 3380, 3372, 3385, 3391, 3388, 3375, 3382, 3369, 3358, 3340, 3334, 3326, 3318, 3310, 3302, 3298, 3291, 3280],
  oil: [78.2, 78.4, 77.9, 78.8, 79.1, 79.4, 79.0, 80.1, 80.4, 79.8, 80.6, 81.2, 82.0, 81.5, 82.6, 83.1, 83.7, 84.4, 84.9, 85.5, 86.4],
  dxy: [101.1, 101.2, 101.0, 101.4, 101.5, 101.7, 101.6, 101.9, 102.0, 102.3, 102.6, 102.9, 103.1, 103.5, 103.6, 103.9, 104.2, 104.6, 104.8, 105.0, 105.4],
  usdkrw: [1371, 1374, 1370, 1376, 1379, 1382, 1380, 1388, 1391, 1394, 1398, 1401, 1404, 1408, 1412, 1416, 1420, 1425, 1432, 1436, 1444],
  us2y: [3.82, 3.83, 3.81, 3.84, 3.86, 3.85, 3.87, 3.89, 3.88, 3.91, 3.93, 3.96, 3.97, 3.99, 4.02, 4.05, 4.09, 4.12, 4.16, 4.19, 4.27],
  us10y: [4.02, 4.03, 4.01, 4.04, 4.06, 4.05, 4.08, 4.09, 4.08, 4.11, 4.13, 4.15, 4.16, 4.18, 4.21, 4.23, 4.26, 4.29, 4.33, 4.36, 4.47],
};

export function getDemoObservations(assetId: string): readonly Observation[] {
  const values = seedValues[assetId] ?? [];
  return values.map((value, index) => ({
    assetId,
    timestamp: new Date(baseDate - (values.length - index - 1) * 86_400_000),
    value,
    source: "SOVYN demo provider",
  }));
}

export function findAsset(symbol: string): Asset | undefined {
  const normalized = symbol.toUpperCase();
  return demoAssets.find((asset) => asset.symbol.toUpperCase() === normalized);
}

