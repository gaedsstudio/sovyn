import type { PackageRecord, PublisherRecord } from "./types";

export const API_VERSION = "1";

export type PackageListResponse = {
  readonly api_version: typeof API_VERSION;
  readonly packages: readonly PackageRecord[];
};

export type PackageDetailResponse = {
  readonly api_version: typeof API_VERSION;
  readonly package: PackageRecord | null;
};

export type PublisherResponse = {
  readonly api_version: typeof API_VERSION;
  readonly publisher: PublisherRecord | null;
};

export function packagesResponse(
  packages: readonly PackageRecord[],
): PackageListResponse {
  return { api_version: API_VERSION, packages };
}

export function packageResponse(
  item: PackageRecord | null,
): PackageDetailResponse {
  return { api_version: API_VERSION, package: item };
}

export function publisherResponse(
  publisher: PublisherRecord | null,
): PublisherResponse {
  return { api_version: API_VERSION, publisher };
}
