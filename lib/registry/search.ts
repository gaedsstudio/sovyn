import { listPackages } from "./registry";
import type { PackageRecord } from "./types";

export function searchPackages(query: string): readonly PackageRecord[] {
  const normalized = query.trim().toLowerCase();
  if (normalized.length === 0) {
    return listPackages();
  }
  return listPackages().filter((item) => {
    const haystack = [item.name, item.description, item.publisher, ...item.tags]
      .join(" ")
      .toLowerCase();
    return haystack.includes(normalized);
  });
}
