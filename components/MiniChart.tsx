import type { Observation } from "@/lib/signals/types";

type MiniChartProps = {
  readonly observations: readonly Observation[];
  readonly selectedIso?: string;
};

function buildPath(observations: readonly Observation[]): string {
  if (observations.length === 0) {
    return "";
  }
  const values = observations.map((item) => item.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  return observations
    .map((item, index) => {
      const x = observations.length === 1 ? 0 : (index / (observations.length - 1)) * 100;
      const y = 100 - ((item.value - min) / range) * 100;
      return `${index === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`;
    })
    .join(" ");
}

export function MiniChart({ observations, selectedIso }: MiniChartProps) {
  const selectedIndex = observations.findIndex(
    (item) => item.timestamp.toISOString().slice(0, 10) === selectedIso,
  );
  const selectedX =
    selectedIndex < 0 || observations.length < 2
      ? undefined
      : (selectedIndex / (observations.length - 1)) * 100;
  return (
    <svg
      aria-label="Historical price chart"
      className="h-64 w-full overflow-visible rounded-[8px] border border-[var(--color-border)] bg-[color:rgba(255,255,255,0.025)] p-3"
      role="img"
      viewBox="-4 -4 108 108"
    >
      <path d={buildPath(observations)} fill="none" stroke="var(--color-accent)" strokeWidth="2" />
      {selectedX === undefined ? null : (
        <line
          stroke="var(--color-warning)"
          strokeDasharray="3 3"
          strokeWidth="1"
          x1={selectedX}
          x2={selectedX}
          y1="0"
          y2="100"
        />
      )}
    </svg>
  );
}

