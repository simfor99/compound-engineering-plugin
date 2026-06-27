# Workspace and daily-room guard

The skill may create lab workspaces, but it must not invent a new `docs/todo/YYYY_MM_DD` Tagesraum from the current calendar date.

## Allowed workspace selection

Use one of these, in order:

1. Explicit user path or `--campaign`.
2. Explicit existing `--day-dir`.
3. Source file already lives under `docs/todo/YYYY_MM_DD/`; reuse that same day directory.
4. Fallback non-render workspace under `.context/compound-engineering/ce-prompt-improver/`.

## Forbidden behavior

- Do not create `docs/todo/<today>/` just because the current date exists.
- Do not claim a static review snapshot will render until `html/index.html` exists and the packet at `html/assets/data.json` validates.
- Do not silently move lab artifacts between daily rooms.

The scaffold script enforces this by never deriving a `docs/todo` directory from today's date.
