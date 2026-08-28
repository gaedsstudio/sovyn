"use client";

import { useMemo, useState } from "react";
import { MiniChart } from "@/components/MiniChart";
import type { Observation, Signal } from "@/lib/signals/types";

type WhatHappenedHereProps = {
  readonly observations: readonly Observation[];
  readonly signals: readonly Signal[];
};

export function WhatHappenedHere({ observations, signals }: WhatHappenedHereProps) {
  const initialDate = observations.at(-1)?.timestamp.toISOString().slice(0, 10) ?? "";
  const [selectedDate, setSelectedDate] = useState(initialDate);
  const drivers = useMemo(() => {
    const seen = new Set<string>();
    return signals.flatMap((signal) => {
      return signal.impacts.slice(0, 1).flatMap((impact) => {
        const key = `${signal.asset.symbol}-${signal.event.type}`;
        if (seen.has(key)) {
          return [];
        }
        seen.add(key);
        return [
          {
            label: `${signal.asset.symbol} ${signal.event.type.replaceAll("_", " ")}`,
            relevance: Math.round(impact.relevance * signal.score.confidence * 100),
            rationale: impact.rationale,
          },
        ];
      });
    });
  }, [signals]);
  return (
    <section className="space-y-5">
      <MiniChart observations={observations} selectedIso={selectedDate} />
      <div className="grid gap-4 md:grid-cols-[240px_1fr]">
        <label className="flex flex-col gap-2 text-[13px] text-[var(--color-muted)]">
          Select date
          <select
            className="rounded-[6px] border border-[var(--color-border)] bg-[var(--color-panel)] px-3 py-2 text-[14px] text-[var(--color-text)]"
            onChange={(event) => {
              setSelectedDate(event.target.value);
            }}
            value={selectedDate}
          >
            {observations
              .slice()
              .reverse()
              .map((item) => {
                const iso = item.timestamp.toISOString().slice(0, 10);
                return (
                  <option key={iso} value={iso}>
                    {iso}
                  </option>
                );
              })}
          </select>
        </label>
        <div className="rounded-[8px] border border-[var(--color-border)] bg-[color:rgba(255,255,255,0.025)] p-4">
          <div className="mb-3 text-[12px] font-medium uppercase tracking-[0.08em] text-[var(--color-faint)]">
            Likely drivers
          </div>
          <div className="space-y-3">
            {drivers.slice(0, 4).map((driver) => (
              <div className="grid gap-2 md:grid-cols-[72px_1fr]" key={driver.label}>
                <div className="font-mono text-[18px] text-[var(--color-text)]">
                  {driver.relevance}%
                </div>
                <div>
                  <div className="text-[14px] text-[var(--color-text)]">{driver.label}</div>
                  <div className="text-[13px] leading-5 text-[var(--color-muted)]">
                    {driver.rationale}
                  </div>
                </div>
              </div>
            ))}
          </div>
          <p className="mt-4 text-[12px] leading-5 text-[var(--color-faint)]">
            Percentages are contribution scores for relevance ranking. They are not
            mathematically proven causal attribution.
          </p>
        </div>
      </div>
    </section>
  );
}
