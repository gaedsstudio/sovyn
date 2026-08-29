# SOVYN Registry

The SOVYN Registry is the read-only public package index behind SOVYN Hub.
For v0.1, registry data is version-controlled so package source, publisher state, licenses, and declared permissions remain inspectable.

## API

All responses include `api_version: "1"`.

```text
GET /api/registry/packages
GET /api/registry/packages/[slug]
GET /api/registry/search?q=pytest
GET /api/registry/verified
GET /api/registry/publishers/[name]
```

The API exposes public reads only. v0.1 does not expose public mutation endpoints.

## Package Schema

Packages declare:

- slug and display name
- description
- publisher
- Verified or Community status
- version
- license
- tags
- source repository
- source commit or release tag
- filesystem, shell, and network permissions
- supported platforms
- install command when it is real
- security notes

## Manifest

```yaml
name: pytest-doctor
version: 1.0.0
publisher: acme

source:
  repository: https://github.com/acme/pytest-doctor
  commit: abc123

license: MIT

permissions:
  filesystem:
    read:
      - workspace/**
    write:
      - workspace/**
  shell:
    - pytest
    - python
  network: false
```

## Verified vs Community

Verified means publisher identity, source repository, release integrity, manifest, and permission declarations have been reviewed.
It does not mean guaranteed safe, malware-proof, or permanently endorsed.

Community packages must provide public source, an open-source license, package metadata, and a permission manifest.
Browser submissions cannot self-assign Verified status.

## Publishing

SOVYN Hub v0.1 accepts package proposals through GitHub Issues or Pull Requests:

```text
https://github.com/gaedsstudio/sovyn/issues/new/choose
```

## Future CLI Usage

```bash
sovyn search pytest
sovyn info publisher/package
sovyn install publisher/package
sovyn update
sovyn publish
```

These commands are future-facing website documentation and are not implemented by this website pass.
