import { readFile } from "fs/promises"
import path from "path"
import { describe, expect, test } from "bun:test"

async function readRepoFile(relativePath: string): Promise<string> {
  return readFile(path.join(process.cwd(), relativePath), "utf8")
}

const SHARED_REFERENCES = [
  "artifact-archive-lifecycle.md",
  "decision-assumption-ledger.md",
  "evidence-claim-integrity-guard.md",
  "ce-quality-gates.md",
  "ce-implementation-ledger.md",
  "ce-completion-verification.md",
  "external-side-effect-reality-guard.md",
  "subagent-boundaries.md",
  "source-coverage-matrix.md",
]

describe("OpenSpec transfer guards", () => {
  test("adds shared P0/P1 references for CE governance and evidence transfer", async () => {
    for (const reference of SHARED_REFERENCES) {
      const content = await readRepoFile(`skills/shared/references/${reference}`)
      expect(content.length).toBeGreaterThan(500)
    }

    const decisionLedger = await readRepoFile(
      "skills/shared/references/decision-assumption-ledger.md",
    )
    expect(decisionLedger).toContain("clarify_first")
    expect(decisionLedger).toContain("user_decision")
    expect(decisionLedger).toContain("carry_visible")

    const claimGuard = await readRepoFile(
      "skills/shared/references/evidence-claim-integrity-guard.md",
    )
    expect(claimGuard).toContain("workflow_completion")
    expect(claimGuard).toContain("trace_visibility")
    expect(claimGuard).toContain("Does not prove")

    const qualityGates = await readRepoFile("skills/shared/references/ce-quality-gates.md")
    expect(qualityGates).toContain("pre_ship")
    expect(qualityGates).toContain("not_claimed")
    expect(qualityGates).toContain("deferred")

    const completion = await readRepoFile(
      "skills/shared/references/ce-completion-verification.md",
    )
    expect(completion).toContain("verified_complete")
    expect(completion).toContain("verified_with_deferrals")

    const sideEffects = await readRepoFile(
      "skills/shared/references/external-side-effect-reality-guard.md",
    )
    expect(sideEffects).toContain("email/SMS/push")
    expect(sideEffects).toContain("billing")
    expect(sideEffects).toContain("Readback/visibility evidence")

    const subagents = await readRepoFile("skills/shared/references/subagent-boundaries.md")
    expect(subagents).toContain("Subagents provide evidence")
    expect(subagents).toContain("The main agent owns")

    const sourceCoverage = await readRepoFile(
      "skills/shared/references/source-coverage-matrix.md",
    )
    expect(sourceCoverage).toContain("must-survive")
    expect(sourceCoverage).toContain("covered_by_reference")
  })

  test("routes decision and source coverage guards into planning and document review", async () => {
    const brainstorm = await readRepoFile("skills/ce-brainstorm/SKILL.md")
    const plan = await readRepoFile("skills/ce-plan/SKILL.md")
    const docReview = await readRepoFile("skills/ce-doc-review/SKILL.md")

    for (const content of [brainstorm, plan, docReview]) {
      expect(content).toContain("../shared/references/decision-assumption-ledger.md")
    }
    for (const content of [plan, docReview]) {
      expect(content).toContain("../shared/references/source-coverage-matrix.md")
    }
    expect(docReview).toContain("../shared/references/ce-implementation-ledger.md")
  })

  test("routes claim integrity and side-effect guards into execution and review skills", async () => {
    const skillPaths = [
      "skills/ce-plan/SKILL.md",
      "skills/ce-work/SKILL.md",
      "skills/ce-work-beta/SKILL.md",
      "skills/ce-code-review/SKILL.md",
      "skills/ce-doc-review/SKILL.md",
      "skills/ce-dogfood-beta/SKILL.md",
      "skills/lfg/SKILL.md",
    ]

    for (const skillPath of skillPaths) {
      const content = await readRepoFile(skillPath)
      expect(content).toContain("../shared/references/evidence-claim-integrity-guard.md")
    }

    for (const skillPath of [
      "skills/ce-plan/SKILL.md",
      "skills/ce-work/SKILL.md",
      "skills/ce-work-beta/SKILL.md",
      "skills/ce-code-review/SKILL.md",
      "skills/ce-doc-review/SKILL.md",
      "skills/ce-dogfood-beta/SKILL.md",
      "skills/lfg/SKILL.md",
    ]) {
      const content = await readRepoFile(skillPath)
      expect(content).toContain("../shared/references/external-side-effect-reality-guard.md")
    }
  })

  test("routes quality gates, completion verification, and subagent boundaries", async () => {
    const plan = await readRepoFile("skills/ce-plan/SKILL.md")
    const work = await readRepoFile("skills/ce-work/SKILL.md")
    const workBeta = await readRepoFile("skills/ce-work-beta/SKILL.md")
    const codeReview = await readRepoFile("skills/ce-code-review/SKILL.md")
    const commitPr = await readRepoFile("skills/ce-commit-push-pr/SKILL.md")
    const docReview = await readRepoFile("skills/ce-doc-review/SKILL.md")
    const optimize = await readRepoFile("skills/ce-optimize/SKILL.md")
    const lfg = await readRepoFile("skills/lfg/SKILL.md")

    for (const content of [plan, work, workBeta, codeReview, commitPr, docReview, optimize, lfg]) {
      expect(content).toContain("../shared/references/ce-quality-gates.md")
    }
    for (const content of [work, workBeta, lfg]) {
      expect(content).toContain("../shared/references/ce-completion-verification.md")
    }
    for (const content of [work, workBeta, codeReview, docReview, optimize, lfg]) {
      expect(content).toContain("../shared/references/subagent-boundaries.md")
    }

    const shippingWorkflow = await readRepoFile("skills/ce-work/references/shipping-workflow.md")
    expect(shippingWorkflow).toContain("../../shared/references/ce-completion-verification.md")
  })

  test("prompt guard now includes fidelity chain and output contract inventory", async () => {
    const guard = await readRepoFile(
      "skills/shared/references/ce-runtime-prompt-contract-guard.md",
    )

    expect(guard).toContain("Prompt fidelity contract")
    expect(guard).toContain("accepted target contract")
    expect(guard).toContain("effective provider request")
    expect(guard).toContain("LLM output contract inventory")
    expect(guard).toContain("Must-survive fields")
    expect(guard).not.toContain("Sanctum")
    expect(guard).not.toContain("services/gtm-agents")
    expect(guard).not.toContain("docs/architecture/testing-agent-entrypoints/gtm-stage-authoring.md")
  })

  test("ce-skill-backup is bundle-manifest and checksum aware", async () => {
    const backupSkill = await readRepoFile("skills/ce-skill-backup/SKILL.md")
    const backupScript = await readRepoFile(
      "skills/ce-skill-backup/scripts/backup_ce_skill_bundle.py",
    )

    expect(backupSkill).toContain("skills/shared/ce-bundle.json")
    expect(backupSkill).toContain("src/release/bundleManifest.ts")
    expect(backupSkill).toContain("bun run release:validate")
    expect(backupSkill).toContain("root release-validation hook")
    expect(backupSkill).toContain("checksum")
    expect(backupSkill).toContain("active cache")
    expect(backupSkill).toContain("fork")
    expect(backupScript).toContain('Path("src/release")')
    expect(backupScript).toContain('Path("scripts/release")')
    expect(backupScript).toContain('Path("package.json")')
    expect(backupScript).toContain('Path(".opencode")')
    expect(backupScript).toContain('Path(".pi")')
    expect(backupScript).toContain("bundle_manifest")
  })

  test("status docs record anti-clone and explicit deferral gates", async () => {
    const status = await readRepoFile(
      "docs/solutions/skill-design/2026-06-23-openspec-transfer-implementation-status.md",
    )
    const ledger = await readRepoFile(
      "docs/solutions/skill-design/2026-06-23-openspec-transfer-implementation-ledger.md",
    )

    expect(status).toContain("Anti-clone-Gate")
    expect(status).toContain("no default `openspec/changes/**`")
    expect(status).toContain("security_deferral")
    expect(status).toContain("blocked_missing_prompt_contract_profile")
    expect(status).toContain("Supabase/DB Guard")
    expect(status).toContain("no unacknowledged P0/P1 gaps")
    expect(ledger).toContain("P0.6")
    expect(ledger).toContain("P1.12")
  })
})
