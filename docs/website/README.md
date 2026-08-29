# SOVYN Website

This repository contains the production source for `https://sovyn.org`.

## Purpose

The website is the public home for SOVYN and SOVYN Hub. It explains the open-source, local-first runtime and exposes a read-only package registry.

## Architecture

- Next.js App Router
- TypeScript
- Server-rendered pages by default
- Zod-validated registry data
- Read-only API routes under `/api/registry`
- Cloudflare deployment through OpenNext and Wrangler

## Development

```bash
npm install
npm run dev
```

## Checks

```bash
npm run lint
npm run typecheck
npm test
npm run build
```

## Cloudflare

The Cloudflare target is `sovyn-org` in `wrangler.jsonc`.
The production domain is `https://sovyn.org`.

Authenticate once in an interactive terminal before deployment:

```bash
npx wrangler login
```

Then deploy:

```bash
npm run cf:build
npm run deploy
```

## Environment Variables

No secrets are required for public registry reads.
Future authenticated Cloudflare or GitHub workflows must use environment variables and never commit tokens.

## Security

The registry is read-only in v0.1. Community package submission happens through GitHub review, not arbitrary upload.
Verified state is controlled by trusted registry data, not browser input.
