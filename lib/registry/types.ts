export type PackageStatus = "verified" | "community";

export type VerificationLevel = "publisher" | "source" | "release";

export type PublisherRecord = {
  readonly id: string;
  readonly slug: string;
  readonly displayName: string;
  readonly github: string;
  readonly website: string;
  readonly verified: boolean;
  readonly verifiedAt: string | null;
  readonly verificationLevel: VerificationLevel | null;
};

export type PackageRecord = {
  readonly slug: string;
  readonly name: string;
  readonly description: string;
  readonly publisher: string;
  readonly status: PackageStatus;
  readonly version: string;
  readonly license: string;
  readonly tags: readonly string[];
  readonly source: {
    readonly repository: string;
    readonly commit: string | null;
    readonly releaseTag: string | null;
  };
  readonly permissions: {
    readonly summary: readonly string[];
    readonly filesystem: {
      readonly read: readonly string[];
      readonly write: readonly string[];
    };
    readonly shell: readonly string[];
    readonly network: readonly string[] | false;
  };
  readonly platforms: readonly string[];
  readonly installCommand: string | null;
  readonly readme: string;
  readonly securityNotes: readonly string[];
};
