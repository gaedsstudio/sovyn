import type {
  Asset,
  ChangeDetectionResult,
  Direction,
  EventType,
  MarketEvent,
} from "@/lib/signals/types";
import { assertNever } from "@/lib/utils/assertNever";

function eventTypeForAsset(asset: Asset): EventType {
  switch (asset.type) {
    case "indicator":
      return asset.group === "rates" ? "yield_move" : "growth_release";
    case "index":
      return "equity_index_move";
    case "fx":
      return "fx_move";
    case "commodity":
      return "commodity_move";
    case "crypto":
      return "crypto_move";
    case "equity":
      return asset.group === "semiconductors" ? "sector_move" : "company_move";
    default:
      return assertNever(asset.type);
  }
}

function directionFromChange(change: number): Direction {
  if (change > 0) {
    return "up";
  }
  if (change < 0) {
    return "down";
  }
  return "flat";
}

export function createEvent(asset: Asset, change: ChangeDetectionResult): MarketEvent {
  const direction = directionFromChange(change.absoluteChange);
  const magnitude = Math.min(Math.abs(change.zScore) / 3, 1);
  return {
    id: `${asset.symbol}-${change.latest.timestamp.toISOString().slice(0, 10)}`,
    type: eventTypeForAsset(asset),
    assetId: asset.id,
    direction,
    magnitude,
    timestamp: change.latest.timestamp,
    confidence: Math.min(0.55 + Math.abs(change.zScore) / 5, 0.96),
    summary: `${asset.symbol} moved ${direction} by ${(change.percentageChange * 100).toFixed(2)}%.`,
  };
}
