import type { Explanation, SignalContext } from "@/lib/signals/types";

export interface ExplanationModel {
  explain(context: SignalContext): Promise<Explanation>;
}

export class MockExplanationModel implements ExplanationModel {
  async explain(context: SignalContext): Promise<Explanation> {
    return context.signal.explanation;
  }
}

export class ExternalLLMModel implements ExplanationModel {
  async explain(context: SignalContext): Promise<Explanation> {
    return {
      fact: context.signal.explanation.fact,
      interpretation: context.signal.explanation.interpretation,
      uncertainty:
        "External LLM mode must use only supplied signal context. No provider key is configured in demo mode.",
    };
  }
}

export class SovynFineTunedModel implements ExplanationModel {
  private readonly baseModel: string;
  private readonly adapterPath: string;

  constructor(baseModel = "Qwen/Qwen3-4B", adapterPath = "outputs/experiments/exp001-qwen3-4b/adapter") {
    this.baseModel = baseModel;
    this.adapterPath = adapterPath;
  }

  async explain(context: SignalContext): Promise<Explanation> {
    return {
      fact: context.signal.explanation.fact,
      interpretation: context.signal.explanation.interpretation,
      uncertainty:
        `Fine-tuned adapter inference is prepared for ${this.baseModel} with adapter ${this.adapterPath}; it is not loaded during normal app startup.`,
    };
  }
}

export function getExplanationModel(provider: string | undefined): ExplanationModel {
  if (provider === "external") {
    return new ExternalLLMModel();
  }
  if (provider === "sovyn") {
    return new SovynFineTunedModel();
  }
  return new MockExplanationModel();
}
