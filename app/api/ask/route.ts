import { z } from "zod";
import { getExplanationModel } from "@/lib/ai/explanation-model";
import { buildDemoHistories, getTodaySignals } from "@/lib/signals/demo";

const askRequestSchema = z.object({
  query: z.string().min(1),
});

export async function POST(request: Request) {
  const body = askRequestSchema.parse(await request.json());
  const signals = getTodaySignals([body.query.toUpperCase().includes("NVDA") ? "NVDA" : "US10Y"]);
  const signal = signals[0];
  if (signal === undefined) {
    return Response.json({ answer: undefined, evidence: [] }, { status: 404 });
  }
  const model = getExplanationModel(process.env.AI_PROVIDER);
  const answer = await model.explain({
    signal,
    observations: buildDemoHistories().get(signal.asset.id) ?? [],
  });
  return Response.json({
    answer,
    evidence: {
      event: signal.event,
      impacts: signal.impacts,
      score: signal.score,
    },
  });
}

