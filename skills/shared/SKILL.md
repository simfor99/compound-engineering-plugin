---
name: shared
description: Internal support references for Compound Engineering skills. Not user-invocable.
user-invocable: false
---

# Shared support references

This directory contains shared reference files used by multiple Compound
Engineering skills.

It is intentionally not user-invocable. Its purpose is portability: plugin
converters and platform installers can copy this support directory alongside
regular skills so relative sibling references such as
`../shared/references/<file>.md` from a skill `SKILL.md`, or
`../../shared/references/<file>.md` from a nested reference file, resolve in
installed runtimes.

Do not invoke this as a workflow skill.
