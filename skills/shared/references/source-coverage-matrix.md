# CE source coverage matrix

Use this reference when CE work starts from a source artifact whose important
facts must survive into planning, implementation, review, or contracts.

## Trigger

Apply for:

- brainstorm or requirements documents;
- strategy, architecture, or review reports;
- user-provided exact instructions;
- prompt contracts, Stage authoring docs, or workflow specs;
- transfer reports and migration plans;
- any source with "must", "P0/P1", "acceptance", "non-goal", or
  "must-survive" language.

## Coverage classes

| Class | Meaning |
|---|---|
| `covered` | The source item is represented in a plan unit, contract, gate, test, or explicit implementation target. |
| `covered_by_reference` | The target artifact points to a canonical source instead of restating it. |
| `deferred` | The source item is intentionally postponed with owner/gate. |
| `not_applicable` | The item is outside current scope and does not need follow-up. |
| `missing` | The item matters and is not represented. |

## Minimum matrix

```md
| Source item | Source path/section | Must survive into | Coverage | Evidence/target | Notes |
|---|---|---|---|---|---|
| <short item> | `<path>#section` | plan|contract|test|skill hook|validator|report | covered|covered_by_reference|deferred|not_applicable|missing | `<path>` | <short note> |
```

## Skill behavior

- `ce-plan` uses this matrix or a compact equivalent when a source artifact has
  material P0/P1 items.
- `ce-doc-review` flags missing coverage when a requirements or plan document
  drops source commitments without an explicit deferral.
- `ce-work` treats source coverage as part of completion verification when the
  active plan or goal names it.
