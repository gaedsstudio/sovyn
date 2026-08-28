import type {
  ChangeDetectionConfig,
  ChangeDetectionResult,
  Observation,
} from "@/lib/signals/types";

export const defaultDetectionConfig: ChangeDetectionConfig = {
  lookback: 20,
  zScoreThreshold: 1.85,
  percentageThreshold: 0.015,
};

function mean(values: readonly number[]): number {
  if (values.length === 0) {
    return 0;
  }
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function standardDeviation(values: readonly number[]): number {
  if (values.length < 2) {
    return 0;
  }
  const average = mean(values);
  const variance = mean(values.map((value) => (value - average) ** 2));
  return Math.sqrt(variance);
}

function percentileRank(values: readonly number[], value: number): number {
  if (values.length === 0) {
    return 0;
  }
  const belowOrEqual = values.filter((sample) => sample <= value).length;
  return belowOrEqual / values.length;
}

export function detectChange(
  observations: readonly Observation[],
  config: ChangeDetectionConfig = defaultDetectionConfig,
): ChangeDetectionResult | undefined {
  const ordered = [...observations].sort(
    (left, right) => left.timestamp.getTime() - right.timestamp.getTime(),
  );
  const latest = ordered.at(-1);
  const previous = ordered.at(-2);
  if (latest === undefined || previous === undefined) {
    return undefined;
  }
  const window = ordered.slice(-config.lookback - 1);
  const moves = window.slice(1).map((item, index) => {
    const prior = window[index];
    return prior === undefined ? 0 : item.value - prior.value;
  });
  const absoluteMoves = moves.map((move) => Math.abs(move));
  const absoluteChange = latest.value - previous.value;
  const percentageChange = previous.value === 0 ? 0 : absoluteChange / previous.value;
  const volatility = standardDeviation(moves);
  const zScore = volatility === 0 ? 0 : absoluteChange / volatility;
  const significant =
    Math.abs(zScore) >= config.zScoreThreshold ||
    Math.abs(percentageChange) >= config.percentageThreshold;
  return {
    assetId: latest.assetId,
    latest,
    previous,
    absoluteChange,
    percentageChange,
    meanAbsoluteChange: mean(absoluteMoves),
    volatility,
    zScore,
    percentile: percentileRank(absoluteMoves, Math.abs(absoluteChange)),
    significant,
  };
}

