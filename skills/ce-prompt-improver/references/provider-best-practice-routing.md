# Provider best-practice routing for CE prompt labs

The CE Prompt Improver inherits the OpenSpec Prompt Optimizer rule that prompt
tests must be provider-routed. A prompt that is good for a GPT-style Responses
run may be wrong for Perplexity Search, and a Perplexity Search rule may be
nonsense for a non-search LLM. Choose the provider profile before writing the
candidate prompt, before scoring the result, and before rendering the review
surface.

## Required provider-profile artifact

For every round that touches provider behavior, write a provider profile under
the round artifacts, for example:

```json
{
  "provider": "openai | perplexity | anthropic | google | generic | unknown",
  "ruleset": "openai_gpt_5_4 | perplexity_sonar | claude_opus_4_6 | gemini_3_5_flash | generic_llm",
  "model_family": "string",
  "prompt_surface": "responses | chat | sonar_chat | sonar_pro_search | search_api | agent_api | unknown",
  "confidence": 0.0,
  "evidence": []
}
```

Use `generic_llm` when the runtime route is unknown. Do not apply provider-
specific findings as blockers unless the profile supports them.

## Routing sources

Use the shared Prompt Improver provider profiles as the detailed source of
truth:

- `~/.codex/skills/prompt-improver/references/provider-prompting/00-routing-matrix.md`
- `~/.codex/skills/prompt-improver/references/provider-prompting/01-generic-smart-average.md`
- `~/.codex/skills/prompt-improver/references/provider-prompting/02-openai-gpt-5-4.md`
- `~/.codex/skills/prompt-improver/references/provider-prompting/05-perplexity-sonar.md`

The local CE preflight scripts implement the same core gates used by the
OpenSpec Prompt Optimizer: provider fit, simplicity, anti-overfit/hardcoding
risk, and generalization evidence.

## OpenAI / GPT-series profile

Use an OpenAI/GPT profile when the runtime model, provider route, or request
surface clearly points to OpenAI. For current GPT-series guidance, prefer the
latest official OpenAI prompt/model docs when the exact model is not fixed.
The current OpenAI guidance emphasizes outcome-first prompts, explicit success
criteria, structured output controls when available, static prompt parts before
dynamic parts for caching, and runtime reasoning/verbosity controls instead of
long process-heavy prompt stacks.

Review focus:

- keep System and User responsibilities separated;
- make the task, input blocks, schema, success criteria, and stop/fallback
  behavior explicit;
- use runtime controls such as reasoning effort and verbosity when the route
  supports them;
- avoid visible chain-of-thought; request concise audit fields or supported
  evidence summaries instead;
- remove contradictions and vague aspiration language;
- prefer Structured Outputs or typed parser contracts where the runtime
  supports them.

## Perplexity / Sonar profile

Use `perplexity_sonar` for Sonar, Search API, or Agent API routes. First
classify the Perplexity surface because each surface has different control
levers.

Review focus:

- Sonar search behavior belongs in the User Prompt and API parameters; the
  System Prompt is for output discipline and evidence hygiene;
- Search API has no System/User prompt; query construction, filters, result
  count, and downstream validation are the contract;
- Agent API instructions should be short and stable, while case-specific
  research details belong in the input;
- prefer API parameters for domain, recency, region, language, search type,
  result count, tool budget, and presets;
- avoid few-shot blocks unless evidence proves they help the retrieval task;
- treat citations and source refs as provenance, not as crawl candidates or a
  deterministic URL-selection oracle.

## Required preflight and review behavior

For every rendered prompt in a real A/B round, run:

```bash
python <skill>/scripts/preflight_prompt_contract.py --prompt <rendered-prompt.txt> --variant-id <id> --provider-route <route> --out <round>/artifacts/preflight/<case>__<variant>.json
```

Then pass all preflight reports into the review-data builder or preserve them
through `preflightChecks`. The rendered static report must show provider-fit
status, uncertainty, and any red/yellow findings. A red preflight finding does
not rewrite observed provider output, but it blocks promotion unless Simon
explicitly accepts the risk.

If an external provider guide caused a prompt change, record the source URL and
access date in the round brief or iteration path, and explain the intended
mechanism. This keeps the lab from smuggling generic "best practices" into a
provider where they do not apply.

## Current official sources

- OpenAI prompt guidance: `https://developers.openai.com/api/docs/guides/prompt-guidance`
- OpenAI latest-model guidance: `https://developers.openai.com/api/docs/guides/latest-model`
- OpenAI GPT-5 prompting guide: `https://developers.openai.com/cookbook/examples/gpt-5/gpt-5_prompting_guide`
- Perplexity Sonar prompt guide: `https://docs.perplexity.ai/docs/sonar/prompt-guide`
- Perplexity Agent API prompt guide: `https://docs.perplexity.ai/docs/agent-api/prompt-guide`
- Perplexity Search API quickstart: `https://docs.perplexity.ai/docs/search/quickstart`
