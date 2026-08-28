import { detectChange } from "@/engine/detector/change-detector";
import { createEvent } from "@/engine/events/events";
import { impactRules } from "@/engine/rules/impact-rules";
import { calculateImpactScore } from "@/engine/scoring/impact-score";
import type { Asset, MarketEvent, Observation, Signal } from "@/lib/signals/types";

function impactedAssets(event: MarketEvent, assets: readonly Asset[]): Signal["impacts"] {
  const rules = impactRules.filter((rule) => rule.source === event.type);
  return rules.flatMap((rule) => {
    return assets
      .filter((asset) => asset.group === rule.targetGroup)
      .map((asset) => ({
        assetId: asset.id,
        symbol: asset.symbol,
        direction: rule.direction,
        relevance: rule.strength,
        rationale: rule.rationale,
      }));
  });
}

function explanationFor(event: MarketEvent, asset: Asset, impactCount: number): Signal["explanation"] {
  return {
    fact: `${asset.symbol} registered a statistically unusual ${event.direction} move.`,
    interpretation: `${impactCount} linked market groups match SOVYN impact rules for this event type.`,
    uncertainty: "This is a relevance score, not a proven causal attribution or investment advice.",
  };
}

export function generateSignals(
  assets: readonly Asset[],
  histories: ReadonlyMap<string, readonly Observation[]>,
  watchlistSymbols: readonly string[] = [],
): readonly Signal[] {
  const watchlist = new Set(watchlistSymbols.map((symbol) => symbol.toUpperCase()));
  const signals = assets.flatMap((asset) => {
    const observations = histories.get(asset.id) ?? [];
    const change = detectChange(observations);
    if (change === undefined || !change.significant) {
      return [];
    }
    const event = createEvent(asset, change);
    const impacts = impactedAssets(event, assets);
    const watchlistRelevant =
      watchlist.has(asset.symbol) ||
      impacts.some((impact) => watchlist.has(impact.symbol));
    const relevance = watchlistRelevant ? 1 : 0.82;
    const breadth = Math.min(0.45 + impacts.length * 0.17, 1);
    const score = calculateImpactScore(event, relevance, breadth);
    return [
      {
        id: event.id,
        event,
        asset,
        score,
        impacts,
        explanation: explanationFor(event, asset, impacts.length),
      },
    ];
  });
  return signals.sort((left, right) => right.score.total - left.score.total);
}

