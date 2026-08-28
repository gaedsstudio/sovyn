import { getTodaySignals } from "@/lib/signals/demo";

export async function GET() {
  return Response.json({ results: getTodaySignals(["NVDA", "QQQ", "US10Y"]) });
}

