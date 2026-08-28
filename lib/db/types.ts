import type { Asset, MarketEvent, Observation, Signal } from "@/lib/signals/types";

export type UserRow = {
  readonly id: string;
  readonly email: string | null;
  readonly createdAt: Date;
};

export type AssetRow = Asset;
export type ObservationRow = Observation;
export type EventRow = MarketEvent;

export type EventAssetLinkRow = {
  readonly id: string;
  readonly eventId: string;
  readonly assetId: string;
  readonly direction: string;
  readonly relevance: number;
  readonly rationale: string;
};

export type SignalRow = {
  readonly id: string;
  readonly eventId: string;
  readonly signalDate: Date;
  readonly impactScore: Signal["score"];
};

