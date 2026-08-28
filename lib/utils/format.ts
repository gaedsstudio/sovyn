export function formatScore(score: number): string {
  return score.toString().padStart(2, "0");
}

export function formatValue(value: number): string {
  return value.toFixed(2);
}

export function formatPercent(value: number): string {
  const sign = value > 0 ? "+" : "";
  return `${sign}${(value * 100).toFixed(2)}%`;
}

export function formatChange(direction: string): string {
  return direction.toUpperCase();
}

