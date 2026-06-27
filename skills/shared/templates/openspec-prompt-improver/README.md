# OpenSpec Prompt Improver Review Surface

Diese Vorlage erzeugt eine lesbare statische HTML-Review-Oberfläche für Prompt- und Provider-A/B-Tests. Sie ist im Compound-Engineering-Plugin die gemeinsame technische Vorlage für static-first Prompt-Labs.

- `ce-prompt-improver`: als `html/index.html` im Evidence-Paket.
- andere Prompt-Lab-Flüsse: als portable HITL-Entscheidungsoberfläche nach einem Prompt-A/B- oder Sanity-Test.

Markdown, JSON, Run-Artefakte und Trace-Dateien bleiben kanonisch. Für den CE-Prompt-Improver ist `html/assets/data.json` der gemeinsame UI-Datenvertrag und `html/index.html` die normale Review-Oberfläche. Dauerhafte Verbesserungen an Layout, Farben, Navigation, Collapse-Logik, Metriken oder Interpretation müssen zuerst in dieser gemeinsamen Vorlage beziehungsweise im Builder-Datenvertrag nachvollzogen werden.

## Dateien

```text
openspec-prompt-improver/
  README.md
  index.template.html
  assets/data.template.json
```

Der Platzhalter in `index.template.html` heißt:

```text
__PROMPT_AB_REVIEW_DATA_JSON__
```

## Datenvertrag

`assets/data.template.json` zeigt die erwartete Form. Wichtig sind diese Felder:

- `leftVariantId`: feste linke Variante, meistens A oder der aktuelle Prompt.
- `defaultRightVariant`: rechte Startvariante.
- `cases[].results[]`: pro Case und Variante Prompt, Provider-Output, Parse-Status, Metriken und Artefaktpfade.
- `prompt.system` und `prompt.user`: die wirklich geprüften Prompts.
- `responseText`: echte Provider-Rückgabe oder klar markiertes Fixture.
- `parsedOutput`: parsebarer Output, wenn vorhanden.
- `providerRoute`, `model`, `durationMs`, `tokenUsage`: Provider-/Modell- und Laufzeitkontext, sofern verfügbar.
- `recommendation`: klare HITL-Empfehlung mit nächstem Schritt; nicht als Promotion-Entscheidung missverstehen.
- `goalProgress`: Ziel, Fortschritt, offener Abstand und nächster sinnvoller Schritt.
- `overallAnalysis`: Gesamtbefund über alle Cases; `assistant_review`, nicht Provider-Output.
- `decisionScorecard`: kompakte Ampel aus Primary, Guardrails, Monitoring, Evidence und HITL-Status.
- `assistant_recommendation`: neutrale Empfehlung. Darf auch Baseline behalten, alle Varianten ablehnen oder `inconclusive` melden.
- `outputTreeDefaultExpanded`, `outputTreeDefaultDepth`, `outputTreeMaxInitialArrayItems`: Standardverhalten des JSON-Baums.
- `jsonFieldRolePatterns`: optionale, generische Rollen-Zuordnung für beliebige JSONs; keine fallbezogenen Firmennamen oder URLs.
- `assistantEvaluation`: vereinbarte Standard- und Rundenfokus-Achsen für Radar/Spinnennetz; das ist `assistant_review`, keine Provider-Metrik.
- `assistantEvaluation.standardAxes[]` und `assistantEvaluation.contextAxes[]` sollten `description` enthalten. Diese 1–2 Sätze werden als Hover-Erklärung im Radar und in der Legende angezeigt.
- `metricMatrix`: typed Vergleichsledger für Primary-, Guardrail-, Monitoring- und Assistant-Review-Metriken.
- `decisionMetrics`: renderfertiges Bundle für Spinnennetz, Metrik-Karten, Detailtexte, Guardrails und Monitoring. Es sollte vom Builder aus `metricMatrix`, Provider-Metriken und Trace-Artefakten abgeleitet werden; manuelle Texte sind nur Overrides.
- `traceIntegrity`, `hitlDecision`, `preflightChecks`: Evidence-Status, menschliche Entscheidung und deterministische Vorprüfung. Fehlende Belege werden sichtbar markiert, nicht simuliert.
- `iterationPath`: strukturierte HITL-Feedbackspur (`must_survive`, `must_reject`, `evaluation_focus`, `investigation_question`).
- `interpretationNotes`: qualitative Entscheidung anhand konkreter Inhalte, bevorzugt pro Case (`interpretationNotes[caseId]`) und pro rechter Variante (`variants[variantId]`) befüllt.

## Rendern

```bash
python <compound-engineering-plugin>/skills/shared/scripts/render_prompt_ab_review_surface.py \
  --data path/to/html/assets/data.json \
  --out path/to/html/index.html
```

Für echte Runs muss `html/assets/data.json` mit den tatsächlichen Prompt-, Provider- und Bewertungsdaten gefüllt und danach gerendert werden.

## Design-Regeln

- GTM-Audit Design System v3 Tokens verwenden.
- Light/Dark Mode erhalten.
- System Prompt und User Prompt zeigen standardmäßig den kanonischen Rohtext, der an das LLM übergeben wurde; über das Subject-Icon kann pro Panel optional eine abgeleitete Lesefassung angezeigt werden.
- User Prompts mit eingebetteten JSON-Blöcken zeigen Rollen-Legende, Pastell-Segmente und semantisch gefärbte JSON-Keys.
- Parsebare Provider-Outputs zeigen standardmäßig den vollständig aufgeklappten JSON-Baum.
- Header, System Prompt, User Prompt, Provider-Output und Interpretation haben synchronisierte Einklapp-Buttons in der Schwebekopfzeile; System/User/Output klappen links und rechts immer gemeinsam.
- Die Schwebekopfzeile markiert beim Scrollen den aktuell sichtbaren Bereich.
- Radar/Spinnennetz-Achsen und Legendenpunkte zeigen im Light- und Dark-Mode gut lesbare Tooltip-Erklärungen.
- Keine neue kanonische Wahrheit in der HTML verstecken; Entscheidungen in Markdown zurückschreiben.

## Evidence-Regeln

- `fixture_core` und echte Run-Artefakte getrennt benennen.
- Eine fixture-basierte Oberfläche darf keine Aussage wie „tatsächliche Stage-Rückgabe passt“ tragen.
- Provider wie Perplexity/Sonar, OpenAI, Gemini oder Claude sind über `providerRoute` sichtbar zu machen.
- Qualitative Interpretation muss konkrete Inhalte aus Rückgabe oder parsed Output nennen, nicht nur Metriken.
- Nicht bewiesene Claims bleiben sichtbar, zum Beispiel `workflow_success`, `production_readiness` oder `model_semantic_quality`.
