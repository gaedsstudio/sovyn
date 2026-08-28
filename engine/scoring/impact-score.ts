import type { MarketEvent, Signal } from "@/lib/signals/types";

export type ImpactScoreParts = Signal["score"];

export function calculateImpactScore(
  event: MarketEvent,
  relevance: number,
  breadth: number,
): ImpactScoreParts {
  const magnitude = Math.min(Math.max(event.magnitude, 0), 1);
  const boundedRelevance = Math.min(Math.max(relevance, 0), 1);
  const boundedBreadth = Math.min(Math.max(breadth, 0), 1);
  const confidence = Math.min(Math.max(event.confidence, 0), 1);
  const total = Math.round(
    100 * magnitude * boundedRelevance * boundedBreadth * confidence,
  );
  return {
    magnitude,
    relevance: boundedRelevance,
    breadth: boundedBreadth,
    confidence,
    total,
  };
}

