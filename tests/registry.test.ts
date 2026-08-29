import { describe, expect, test } from "vitest";
import {
  getPackage,
  getPublisher,
  listPackages,
  listVerifiedPackages,
} from "../lib/registry/registry";
import { packagesResponse } from "../lib/registry/responses";
import {
  communitySubmissionSchema,
  packageSchema,
  publisherSchema,
} from "../lib/registry/schema";
import { searchPackages } from "../lib/registry/search";

describe("registry", () => {
  test("validates package schema", () => {
    const item = getPackage("sovyn-core");

    expect(item).not.toBeNull();
    expect(packageSchema.safeParse(item).success).toBe(true);
  });

  test("validates publisher schema", () => {
    const publisher = getPublisher("gaedsstudio");

    expect(publisherSchema.safeParse(publisher).success).toBe(true);
  });

  test("searches name description publisher and tags", () => {
    expect(searchPackages("runtime")).toHaveLength(1);
    expect(searchPackages("gaedsstudio")).toHaveLength(1);
    expect(searchPackages("ollama")).toHaveLength(1);
    expect(searchPackages("missing")).toHaveLength(0);
  });

  test("filters verified packages from trusted registry data", () => {
    const verified = listVerifiedPackages();

    expect(verified).toHaveLength(1);
    expect(verified[0]?.status).toBe("verified");
  });

  test("looks up package details", () => {
    expect(getPackage("sovyn-core")?.name).toBe("SOVYN Core");
    expect(getPackage("missing")).toBeNull();
  });

  test("rejects invalid community manifests that try to self-assign verified status", () => {
    const trusted = listPackages()[0];

    const result = communitySubmissionSchema.safeParse({
      ...trusted,
      slug: "community-test",
      name: "Community Test",
      publisher: "external",
      status: "verified",
    });

    expect(result.success).toBe(false);
  });

  test("returns versioned API response format", () => {
    const response = packagesResponse(listPackages());

    expect(response.api_version).toBe("1");
    expect(response.packages).toHaveLength(1);
  });
});
