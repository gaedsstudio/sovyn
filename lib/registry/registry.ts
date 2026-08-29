import { packages, publishers } from "./data";
import { packageSchema, publisherSchema } from "./schema";
import type { PackageRecord, PublisherRecord } from "./types";

const registryPackages = packageSchema.array().parse(packages);
const registryPublishers = publisherSchema.array().parse(publishers);

export function listPackages(): readonly PackageRecord[] {
  return registryPackages;
}

export function listVerifiedPackages(): readonly PackageRecord[] {
  return registryPackages.filter((item) => item.status === "verified");
}

export function getPackage(slug: string): PackageRecord | null {
  return registryPackages.find((item) => item.slug === slug) ?? null;
}

export function getPublisher(slug: string): PublisherRecord | null {
  return registryPublishers.find((item) => item.slug === slug) ?? null;
}

export function listPublishers(): readonly PublisherRecord[] {
  return registryPublishers;
}
