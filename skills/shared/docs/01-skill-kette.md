> [Zurück zum Index](./INDEX.md) | **Skillkette**

# Skillkette

> **Status:** Aktiv
> **Erstellt:** 2026-06-24
> **Verlinkt mit:** `../SKILL.md`, `../references/`, `../../ce-brainstorm/SKILL.md`, `../../ce-plan/SKILL.md`, `../../ce-work/SKILL.md`

---

## Der kurze Ablauf

Die CE-Skillkette ist ein Staffellauf mit klaren Besitzgrenzen. Ein Skill soll nicht heimlich die Arbeit des nächsten übernehmen: Brainstorming entscheidet nicht die Implementierung, Planung baut nicht, Work ersetzt kein Review, und ein Review ist nicht automatisch Completion.

```text
ce-ideate       optional: starke Richtungen finden
   -> ce-brainstorm   Was soll entstehen?
   -> ce-plan         Wie wird es belastbar umgesetzt?
   -> ce-work         Umsetzung mit passenden Guards
   -> ce-code-review  Code-Befunde, report-only oder interaktiv
   -> ce-test-browser UI-/Browser-Evidence, wenn relevant
   -> ce-commit-push-pr
   -> ce-compound     Lernen festhalten
```

`lfg` ist die autonome Pipeline über diesem Fluss. Sie darf die Reihenfolge nicht abkürzen: Plan vor Work, Work vor Review, Review-Befunde vor Commit/PR, Completion erst nach Gates und Evidence.

---

## Die Guard-Schicht

Die Shared Guards sind die Sicherheitsgurte der Kette. Sie werden nicht immer alle geladen, sondern nur wenn das Thema sie triggert. Prompt-Arbeit lädt den Runtime Prompt Contract Guard. Datenbankarbeit lädt den Supabase Database Change Guard. Readiness-Behauptungen laden Evidence Claim Integrity und Completion Verification. Branches und Worktrees laden den Branch Consent Guard.

Das Muster ist absichtlich einfach: Ein Skill erkennt ein Risiko, lädt die passende Referenz und muss danach ehrlich berichten, was bewiesen, deferred, blocked oder nicht claimed ist.

| Risiko | Shared Reference |
|---|---|
| Prompt-/LLM-Verträge | `ce-runtime-prompt-contract-guard.md` |
| Datenbank/Supabase | `supabase-database-change-guard.md` |
| Live vs Mock/Replay | `evidence-authenticity-guard.md` |
| Zu große Readiness-Claims | `evidence-claim-integrity-guard.md` |
| Externe Side Effects | `external-side-effect-reality-guard.md` |
| Branches/Worktrees | `git-branch-consent-guard.md` |
| Subagent-Ausgaben | `subagent-boundaries.md` |
| Abschlussbehauptungen | `ce-completion-verification.md` |

---

## Die wichtigste Regel

Jeder Skill darf vorbereiten, prüfen oder beitragen, aber die finale Aussage muss zur Evidenz passen. Wenn ein Test nur Replay war, sagt die Kette Replay. Wenn ein Workflow nur gestartet wurde, behauptet sie keine Completion. Wenn ein Prompt als Vertrag akzeptiert wurde, muss er als Vertrag durch Plan, Work, Runtime und Evidence überleben.

Dieser Hub ist deshalb bewusst kurz. Er soll den Weg zeigen; die verbindlichen Details leben in den verlinkten `SKILL.md`-Dateien und Shared References.
