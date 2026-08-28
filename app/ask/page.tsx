import { getExplanationModel } from "@/lib/ai/explanation-model";
import { buildDemoHistories, getTodaySignals } from "@/lib/signals/demo";

export default async function AskPage() {
  const signals = getTodaySignals(["NVDA", "US10Y"]);
  const primary = signals[0];
  const model = getExplanationModel(process.env.AI_PROVIDER);
  const explanation =
    primary === undefined
      ? undefined
      : await model.explain({
          signal: primary,
          observations: buildDemoHistories().get(primary.asset.id) ?? [],
        });
  return (
    <div className="space-y-8">
      <section className="border-b border-[var(--color-border)] pb-8">
        <p className="mb-3 text-[12px] font-medium uppercase tracking-[0.08em] text-[var(--color-faint)]">
          Ask SOVYN
        </p>
        <h1 className="text-[44px] font-semibold leading-[1.04] tracking-[-0.04em] md:text-[56px]">
          Ask from structured signal context
        </h1>
        <form className="mt-6 max-w-[760px] rounded-[8px] border border-[var(--color-border)] bg-[color:rgba(255,255,255,0.025)] p-3">
          <label className="sr-only" htmlFor="query">
            Market question
          </label>
          <textarea
            className="min-h-28 w-full resize-y rounded-[6px] border border-[var(--color-border)] bg-[var(--color-panel)] p-3 text-[15px] text-[var(--color-text)]"
            defaultValue="Why did semiconductor stocks fall today?"
            id="query"
            name="query"
          />
        </form>
      </section>
      <section className="grid gap-4 md:grid-cols-3">
        <div className="rounded-[8px] border border-[var(--color-border)] bg-[color:rgba(255,255,255,0.025)] p-4">
          <div className="mb-2 text-[12px] font-medium uppercase tracking-[0.08em] text-[var(--color-faint)]">
            Fact
          </div>
          <p className="text-[14px] leading-6 text-[var(--color-muted)]">
            {explanation?.fact ?? "No signal context available."}
          </p>
        </div>
        <div className="rounded-[8px] border border-[var(--color-border)] bg-[color:rgba(255,255,255,0.025)] p-4">
          <div className="mb-2 text-[12px] font-medium uppercase tracking-[0.08em] text-[var(--color-faint)]">
            Interpretation
          </div>
          <p className="text-[14px] leading-6 text-[var(--color-muted)]">
            {explanation?.interpretation ?? "No interpretation generated."}
          </p>
        </div>
        <div className="rounded-[8px] border border-[var(--color-border)] bg-[color:rgba(255,255,255,0.025)] p-4">
          <div className="mb-2 text-[12px] font-medium uppercase tracking-[0.08em] text-[var(--color-faint)]">
            Uncertainty
          </div>
          <p className="text-[14px] leading-6 text-[var(--color-muted)]">
            {explanation?.uncertainty ?? "Confidence unavailable."}
          </p>
        </div>
      </section>
    </div>
  );
}

