import { z } from "zod";

export const publisherSchema = z.object({
  id: z.string().min(1),
  slug: z.string().regex(/^[a-z0-9-]+$/),
  displayName: z.string().min(1),
  github: z.string().url(),
  website: z.string().url(),
  verified: z.boolean(),
  verifiedAt: z.string().datetime().nullable(),
  verificationLevel: z.enum(["publisher", "source", "release"]).nullable(),
});

export const packageSchema = z.object({
  slug: z.string().regex(/^[a-z0-9-]+$/),
  name: z.string().min(1),
  description: z.string().min(1),
  publisher: z.string().min(1),
  status: z.enum(["verified", "community"]),
  version: z.string().min(1),
  license: z.string().min(1),
  tags: z.array(z.string().min(1)),
  source: z.object({
    repository: z.string().url(),
    commit: z.string().min(1).nullable(),
    releaseTag: z.string().min(1).nullable(),
  }),
  permissions: z.object({
    summary: z.array(z.string().min(1)),
    filesystem: z.object({
      read: z.array(z.string().min(1)),
      write: z.array(z.string().min(1)),
    }),
    shell: z.array(z.string().min(1)),
    network: z.union([z.array(z.string().min(1)), z.literal(false)]),
  }),
  platforms: z.array(z.string().min(1)),
  installCommand: z.string().min(1).nullable(),
  readme: z.string().min(1),
  securityNotes: z.array(z.string().min(1)),
});

export const communitySubmissionSchema = packageSchema
  .omit({ status: true })
  .strict();
