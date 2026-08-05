# RealityNG Version 2 Release Decision

## Decision Summary

Do not move the existing `v2.0.0` tags.

Create a new immutable release tag:

```text
v2.1.0
```

## Reasoning

The existing `v2.0.0` tags are already published in both repositories and point to the earlier Verification and Guided Assistant release.

Backend existing `v2.0.0` target:

```text
a5d8824b8f89f80ca31fad2cc4a4f4b4453952a6
```

Frontend existing `v2.0.0` target:

```text
04c7b68ed085d37e7fab9cd929525b833b6d062f
```

Moving those tags would rewrite release history and could confuse deployment, rollback, and audit records.

Sprint 9.1 through Sprint 9.8 introduced a substantial production capability: the Services Marketplace. This is larger than a patch release, so `v2.1.0` is more appropriate than `v2.0.1`.

## Version Meaning

`v2.0.0` remains:

```text
Verification and Guided Assistant Release
```

`v2.1.0` represents:

```text
Services Marketplace Production Release
```

## Release Tag Message

Use this annotated tag message:

```text
RealityNG Version 2.1
Services Marketplace Production Release
Sprint 9 Complete
```

## Tagging Rules

- Do not delete or move `v2.0.0`.
- Do not force-push tags.
- Create `v2.1.0` only if it does not already exist locally or remotely.
- Tag backend and frontend separately.
- Record exact tag targets in the final closure report.

## Production Runtime Note

The backend production runtime deployed during Sprint 9.8 is:

```text
c2b9c62617e9666512a5b5c636715024b217c5ac
```

Subsequent backend commits after that point are documentation-only release-freeze and closure commits. The `v2.1.0` backend tag may therefore point to a documentation-inclusive baseline while the runtime code remains unchanged from the deployed commit.

