import { describe, expect, it } from "vitest";
import { detectChange } from "@/engine/detector/change-detector";
import { createEvent } from "@/engine/events/events";
import { generateSignals } from "@/engine/pipeline/signal-pipeline";
import { calculateImpactScore } from "@/engine/scoring/impact-score";
import { demoAssets, getDemoObservations } from "@/lib/market/mock-data";

describe("change detection", () => {
  it("detects a significant z-score move when the latest observation jumps", () => {
    const observations = getDemoObservations("us10y");

    const result = detectChange(observations);

    expect(result?.significant).toBe(true);
    expect(result?.zScore).toBeGreaterThan(1);
  });
});

describe("event creation", () => {
  it("creates a yield event when a rates indicator moves", () => {
    const asset = demoAssets.find((item) => item.id === "us10y");
    const change = detectChange(getDemoObservations("us10y"));

    expect(asset).toBeDefined();
    expect(change).toBeDefined();
    if (asset === undefined || change === undefined) {
      return;
    }
    const event = createEvent(asset, change);

    expect(event.type).toBe("yield_move");
    expect(event.direction).toBe("up");
    expect(event.confidence).toBeGreaterThan(0.5);
  });
});

describe("impact scoring", () => {
  it("keeps component parts available for debugging", () => {
    const event = {
      id: "event",
      type: "yield_move",
      assetId: "us10y",
      direction: "up",
      magnitude: 0.9,
      timestamp: new Date("2026-08-27T00:00:00Z"),
      confidence: 0.8,
      summary: "Yield move",
    } as const;

    const score = calculateImpactScore(event, 1, 0.75);

    expect(score.total).toBe(54);
    expect(score.magnitude).toBe(0.9);
    expect(score.relevance).toBe(1);
    expect(score.breadth).toBe(0.75);
  });
});

describe("signal ranking", () => {
  it("prioritizes watchlist-relevant signals", () => {
    const histories = new Map(demoAssets.map((asset) => [asset.id, getDemoObservations(asset.id)]));

    const signals = generateSignals(demoAssets, histories, ["NVDA"]);

    expect(signals.length).toBeGreaterThan(0);
    expect(signals[0]?.score.total).toBeGreaterThanOrEqual(signals.at(-1)?.score.total ?? 0);
  });
});

