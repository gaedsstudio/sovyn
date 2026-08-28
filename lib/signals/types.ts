import { z } from "zod";

export const assetTypeSchema = z.union([
  z.literal("equity"),
  z.literal("index"),
  z.literal("commodity"),
  z.literal("fx"),
  z.literal("crypto"),
  z.literal("indicator"),
]);

export const directionSchema = z.union([
  z.literal("up"),
  z.literal("down"),
  z.literal("flat"),
]);

export const impactDirectionSchema = z.union([
  z.literal("positive"),
  z.literal("negative"),
  z.literal("mixed"),
  z.literal("neutral"),
]);

export const eventTypeSchema = z.union([
  z.literal("yield_move"),
  z.literal("equity_index_move"),
  z.literal("fx_move"),
  z.literal("commodity_move"),
  z.literal("crypto_move"),
  z.literal("inflation_release"),
  z.literal("employment_release"),
  z.literal("growth_release"),
  z.literal("central_bank_event"),
  z.literal("sector_move"),
  z.literal("company_move"),
]);

export const assetSchema = z.object({
  id: z.string().min(1),
  symbol: z.string().min(1),
  name: z.string().min(1),
  type: assetTypeSchema,
  group: z.string().min(1),
});

export const observationSchema = z.object({
  assetId: z.string().min(1),
  timestamp: z.coerce.date(),
  value: z.number(),
  source: z.string().min(1),
});

export const eventSchema = z.object({
  id: z.string().min(1),
  type: eventTypeSchema,
  assetId: z.string().min(1),
  direction: directionSchema,
  magnitude: z.number(),
  timestamp: z.coerce.date(),
  confidence: z.number().min(0).max(1),
  summary: z.string().min(1),
});

export const impactRuleSchema = z.object({
  source: eventTypeSchema,
  targetGroup: z.string().min(1),
  direction: impactDirectionSchema,
  strength: z.number().min(0).max(1),
  rationale: z.string().min(1),
});

export const signalSchema = z.object({
  id: z.string().min(1),
  event: eventSchema,
  asset: assetSchema,
  score: z.object({
    magnitude: z.number().min(0).max(1),
    relevance: z.number().min(0).max(1),
    breadth: z.number().min(0).max(1),
    confidence: z.number().min(0).max(1),
    total: z.number().min(0).max(100),
  }),
  impacts: z.array(
    z.object({
      assetId: z.string().min(1),
      symbol: z.string().min(1),
      direction: impactDirectionSchema,
      relevance: z.number().min(0).max(1),
      rationale: z.string().min(1),
    }),
  ),
  explanation: z.object({
    fact: z.string().min(1),
    interpretation: z.string().min(1),
    uncertainty: z.string().min(1),
  }),
});

export type Asset = z.infer<typeof assetSchema>;
export type Observation = z.infer<typeof observationSchema>;
export type EventType = z.infer<typeof eventTypeSchema>;
export type MarketEvent = z.infer<typeof eventSchema>;
export type ImpactRule = z.infer<typeof impactRuleSchema>;
export type Signal = z.infer<typeof signalSchema>;
export type Direction = z.infer<typeof directionSchema>;
export type ImpactDirection = z.infer<typeof impactDirectionSchema>;

export type ChangeDetectionConfig = {
  readonly lookback: number;
  readonly zScoreThreshold: number;
  readonly percentageThreshold: number;
};

export type ChangeDetectionResult = {
  readonly assetId: string;
  readonly latest: Observation;
  readonly previous: Observation;
  readonly absoluteChange: number;
  readonly percentageChange: number;
  readonly meanAbsoluteChange: number;
  readonly volatility: number;
  readonly zScore: number;
  readonly percentile: number;
  readonly significant: boolean;
};

export type SignalContext = {
  readonly signal: Signal;
  readonly observations: readonly Observation[];
};

export type Explanation = {
  readonly fact: string;
  readonly interpretation: string;
  readonly uncertainty: string;
};

