import type { ImpactRule } from "@/lib/signals/types";

export const impactRules: readonly ImpactRule[] = [
  {
    source: "yield_move",
    targetGroup: "growth_equities",
    direction: "negative",
    strength: 0.86,
    rationale: "Higher yields can pressure long-duration equity valuations.",
  },
  {
    source: "yield_move",
    targetGroup: "usd",
    direction: "positive",
    strength: 0.78,
    rationale: "Higher US yields can improve dollar carry and rate support.",
  },
  {
    source: "yield_move",
    targetGroup: "precious_metals",
    direction: "negative",
    strength: 0.62,
    rationale: "Higher real-rate expectations can weigh on non-yielding assets.",
  },
  {
    source: "fx_move",
    targetGroup: "semiconductors",
    direction: "mixed",
    strength: 0.42,
    rationale: "Dollar strength can affect global revenue translation and risk appetite.",
  },
  {
    source: "commodity_move",
    targetGroup: "broad_equities",
    direction: "mixed",
    strength: 0.44,
    rationale: "Energy and commodity moves can shift inflation and margin expectations.",
  },
  {
    source: "sector_move",
    targetGroup: "growth_equities",
    direction: "mixed",
    strength: 0.72,
    rationale: "Semiconductor weakness often feeds into broader growth-equity risk sentiment.",
  },
] as const;

