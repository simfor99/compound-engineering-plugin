import { readFile } from "fs/promises"
import path from "path"
import { describe, expect, test } from "bun:test"

async function readRepoFile(relativePath: string): Promise<string> {
  return readFile(path.join(process.cwd(), relativePath), "utf8")
}

function activeRootPlanFiles(paths: string[]): string[] {
  return paths.filter(
    (filePath) =>
      /^docs\/plans\/[^/]+\.(md|html)$/.test(filePath) &&
      !filePath.startsWith("docs/plans/_archive/"),
  )
}

function activeRootBrainstormRequirements(paths: string[]): string[] {
  return paths.filter(
    (filePath) =>
      /^docs\/brainstorms\/[^/]+-requirements\.(md|html)$/.test(filePath) &&
      !filePath.startsWith("docs/brainstorms/_archive/"),
  )
}

function brainstormArtifactFamilyKey(filePath: string): string {
  return path
    .basename(filePath)
    .replace(/\.(md|html)$/, "")
    .replace(/-(requirements|working-notes|review-log)$/, "")
}

describe("CE artifact archive lifecycle", () => {
  test("shared contract defines roots, archive paths, sidecars, family key, and reopening", async () => {
    const contract = await readRepoFile(
      "skills/shared/references/artifact-archive-lifecycle.md",
    )

    for (const expected of [
      "docs/plans/",
      "docs/plans/_archive/",
      "docs/brainstorms/",
      "docs/brainstorms/_archive/",
      "Explicit paths",
      "same-stem plan sidecar",
      "brainstorm_artifact_family_key",
      "Reopening",
      "requires_simon_decision",
    ]) {
      expect(contract).toContain(expected)
    }

    expect(contract).toContain("Do not add a mutable `status:` lifecycle field")
  })

  test("auto-discovery filters ignore archive roots but explicit archived paths remain valid", async () => {
    const paths = [
      "docs/plans/2026-06-26-001-feat-active-plan.md",
      "docs/plans/2026-06-26-002-feat-active-plan.html",
      "docs/plans/_archive/2026-06-25-001-feat-done-plan.md",
      "docs/plans/_archive/2026-06-25-001-feat-done-plan/evidence-receipt.md",
      "docs/brainstorms/2026-06-26-open-requirements.md",
      "docs/brainstorms/_archive/2026-06-25-done-requirements.md",
    ]

    expect(activeRootPlanFiles(paths)).toEqual([
      "docs/plans/2026-06-26-001-feat-active-plan.md",
      "docs/plans/2026-06-26-002-feat-active-plan.html",
    ])
    expect(activeRootBrainstormRequirements(paths)).toEqual([
      "docs/brainstorms/2026-06-26-open-requirements.md",
    ])

    const contract = await readRepoFile(
      "skills/shared/references/artifact-archive-lifecycle.md",
    )
    const plan = await readRepoFile("skills/ce-plan/SKILL.md")
    const work = await readRepoFile("skills/ce-work/SKILL.md")

    expect(contract).toContain(
      "Explicit paths may point to active roots or `_archive` paths",
    )
    expect(plan).toContain("explicit archived requirements path")
    expect(plan).toContain("archived plan path under `docs/plans/_archive/`")
    expect(work).toContain(
      "If the user explicitly passed a plan path under `docs/plans/_archive/`",
    )
    expect(work).toContain("read it as historical/review context only")
  })

  test("brainstorm family matching strips exactly one terminal suffix", () => {
    expect(
      brainstormArtifactFamilyKey(
        "docs/brainstorms/2026-06-23-url-admission-beta-ux-requirements.md",
      ),
    ).toBe("2026-06-23-url-admission-beta-ux")
    expect(
      brainstormArtifactFamilyKey(
        "docs/brainstorms/2026-06-23-url-admission-beta-ux-working-notes.md",
      ),
    ).toBe("2026-06-23-url-admission-beta-ux")
    expect(
      brainstormArtifactFamilyKey(
        "docs/brainstorms/2026-06-23-url-admission-beta-ux-review-log.md",
      ),
    ).toBe("2026-06-23-url-admission-beta-ux")
    expect(
      brainstormArtifactFamilyKey(
        "docs/brainstorms/2026-06-23-url-admission-beta-ux-extra-notes.md",
      ),
    ).toBe("2026-06-23-url-admission-beta-ux-extra-notes")
  })

  test("planning, work, and review skills route through archive lifecycle guard", async () => {
    const skillPaths = [
      "skills/ce-brainstorm/SKILL.md",
      "skills/ce-plan/SKILL.md",
      "skills/ce-work/SKILL.md",
      "skills/ce-work-beta/SKILL.md",
      "skills/ce-code-review/SKILL.md",
      "skills/lfg/SKILL.md",
    ]

    for (const skillPath of skillPaths) {
      const content = await readRepoFile(skillPath)
      expect(content).toContain("../shared/references/artifact-archive-lifecycle.md")
    }

    const work = await readRepoFile("skills/ce-work/SKILL.md")
    expect(work).toContain("Ignore `docs/plans/_archive/` for blank/latest discovery")
    expect(work).toContain("Move the plan file and same-stem sidecar directory together")
    expect(work).toContain("read it as historical/review context only")

    const codeReview = await readRepoFile("skills/ce-code-review/SKILL.md")
    expect(codeReview).toContain("docs/plans/_archive/*.md")
    expect(codeReview).toContain("Glob active-root `docs/plans/*.md`")
  })

  test("ce-plan archives brainstorm origins before post-generation handoff routes", async () => {
    const plan = await readRepoFile("skills/ce-plan/SKILL.md")

    const archiveStep = plan.indexOf(
      "#### 5.5 Archive represented brainstorm origin before handoff",
    )
    const menuQuestion = plan.indexOf("**Question:** \"Plan ready at")
    const startWorkRoute = plan.indexOf("- **Start `/ce-work`**")

    expect(archiveStep).toBeGreaterThan(-1)
    expect(menuQuestion).toBeGreaterThan(archiveStep)
    expect(startWorkRoute).toBeGreaterThan(archiveStep)
    expect(plan).toContain("archive-lifecycle-ledger.md")
  })

  test("rendering and section contracts reject mutable status while naming archive location", async () => {
    const files = [
      "skills/ce-plan/references/markdown-rendering.md",
      "skills/ce-brainstorm/references/markdown-rendering.md",
      "skills/ce-ideate/references/markdown-rendering.md",
      "skills/ce-plan/references/plan-sections.md",
      "skills/ce-brainstorm/references/brainstorm-sections.md",
    ]

    for (const file of files) {
      const content = await readRepoFile(file)
      expect(content.toLowerCase()).toContain("no mutable")
      expect(content).toContain("_archive")
      expect(content).toContain("artifact-archive-lifecycle.md")
    }
  })
})
