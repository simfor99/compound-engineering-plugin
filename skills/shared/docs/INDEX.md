# Compound Engineering Skillkette — Skill-Hub

> **Thema:** Zusammenspiel der Compound-Engineering-Skills
> **Domain:** Skill-Orchestrierung
> **Status:** Aktiv
> **Erstellt:** 2026-06-24
> **Letztes Update:** 2026-06-24

---

## Warum dieses System?

Compound Engineering ist wertvoll, weil es nicht nur einzelne Agentenfähigkeiten anbietet, sondern eine Arbeitskette: erst wird verstanden, dann geplant, dann gebaut, dann geprüft, dann gelernt. Ohne eine knappe Kettendoku muss jeder neue Lauf aus verstreuten `SKILL.md`-Dateien rekonstruieren, welcher Skill welche Entscheidung besitzen darf. Das ist fehleranfällig, besonders wenn Prompt-Verträge, Evidence-Gates, Branch-Regeln oder Review-Agenten beteiligt sind.

Die Lösung ist kein zweites Handbuch neben den Skills. Dieser Hub ist die kurze Landkarte: Er erklärt, wann welcher Skill führt, welche Shared Guards quer durch die Kette gelten und wo die eigentliche Wahrheit liegt. Die ausführliche Runtime-Wahrheit bleibt in den jeweiligen `SKILL.md`-Dateien und in `skills/shared/references/`.

Dadurch kann ein Agent schneller richtig einsteigen: `ce-brainstorm` klärt das Was, `ce-plan` übersetzt es in einen belastbaren Weg, `ce-work` führt aus, Reviews prüfen die Behauptungen, und `ce-compound` oder `ce-skill-backup` sorgen dafür, dass das Gelernte und die Skill-Änderungen nicht wieder verschwinden.

| Vorher | Nachher |
|---|---|
| Kettenlogik musste aus vielen Skills zusammengesucht werden | Ein kurzer Einstieg zeigt den normalen Fluss und die Abzweigungen |
| Shared Guards wirkten wie Einzelregeln | Shared Guards sind als Querschnittsschicht sichtbar |
| Review, Backup und Completion wurden leicht verwechselt | Jeder Skill hat eine klare Besitzgrenze |

---

## Wie der Skill funktioniert

Der normale CE-Fluss beginnt nicht beim Code. Wenn die Richtung noch offen ist, hilft `ce-ideate`; wenn die Idee schon da ist, beginnt die Kette meist bei `ce-brainstorm`. Aus dem Ergebnis entsteht mit `ce-plan` ein Ausführungsplan. `ce-work` liest diesen Plan, lädt die passenden Shared Guards und setzt um. Danach prüfen `ce-code-review`, `ce-doc-review`, `ce-test-browser` oder andere On-Demand-Skills genau den Teil, für den sie gebaut wurden. Am Ende halten `ce-compound` und `ce-skill-backup` Wissen und Skill-Zustand fest.

Der wichtigste Punkt ist die Besitzgrenze: Brainstorming besitzt Produkt- und Scope-Fragen, Planung besitzt Umsetzungspfad und Gates, Work besitzt Code- und Artefaktänderungen, Review besitzt Befunde, aber nicht die letzte Wahrheit. Die finale Completion-Behauptung gehört dem Hauptagenten, der Tests, Evidenz und Deferrals zusammenführt.

### Kern-Daten

| Feld | Wert |
|---|---|
| Normaler Einstieg | `ce-brainstorm` oder `ce-plan` |
| Umsetzung | `ce-work` |
| Review | `ce-doc-review`, `ce-code-review`, `ce-test-browser` |
| Wissen sichern | `ce-compound`, `ce-skill-backup` |
| Querschnittsregeln | `skills/shared/references/*.md` |
| Vollständiger Ablauf | [Skillkette](./01-skill-kette.md) |

---

## Wie es zusammenhängt

Dieser Hub verbindet die endnutzernahe Skill-Übersicht in `docs/skills/README.md` mit der runtime-nahen Wahrheit in `skills/*/SKILL.md`. `docs/skills/README.md` erklärt den Katalog für Menschen; dieser Hub erklärt die operative Kette für Agenten; die `SKILL.md`-Dateien bleiben die ausführbaren Verträge.

Das verbindet sich mit `skills/shared/references/`, weil dort die Regeln liegen, die über einzelne Skills hinaus gelten: Evidence, Prompt-Verträge, Datenbankänderungen, Side Effects, Branch Consent, Subagent Boundaries und Completion Verification. Ohne diese Shared Guards würde jeder Skill seine eigene kleine Version von Qualitätssicherung bauen und die Kette würde auseinanderlaufen.

---

## Schlüssel-Entscheidungen

### Shared Hub statt Kopie pro Skill

**Kontext:** Die CE-Kette umfasst viele Skills. Eine Erklärung direkt in jedem Skill würde schnell driften.

**Entscheidung:** Die knappe Kettendoku liegt unter `skills/shared/docs/`, weil `shared` die Querschnittsschicht der CE-Skills ist.

**Konsequenzen:**
- (+) Ein Ort erklärt den Fluss und die Guard-Schicht.
- (-) Der Hub ist ein Einstieg, nicht die vollständige Runtime-Spezifikation.
- (~) Änderungen an Shared Guards sollten diesen Hub kurz mitprüfen.

---

## Skill-Dokumente in diesem Ordner

| # | Dokument | Inhalt |
|---|---|---|
| 01 | [Skillkette](./01-skill-kette.md) | Kompakter Ablauf von Idee bis Backup |

---

## Leseempfehlung

**Einstieg:** Dieses Dokument, dann [Skillkette](./01-skill-kette.md).
**Für den Skill-Katalog:** `../../../docs/skills/README.md`.
**Für verbindliches Runtime-Verhalten:** die jeweilige `../../<skill>/SKILL.md` und `../references/*.md`.

---

## Änderungshistorie

| Datum | Was |
|---|---|
| 2026-06-24 | Initialer kompakter Hub für das Zusammenspiel der CE-Skillkette |
