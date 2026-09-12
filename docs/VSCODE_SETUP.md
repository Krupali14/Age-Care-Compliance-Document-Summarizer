# VS Code: red underlines in Node and React files

What draws those squiggles, why this repository produced a screenful of them, how
to fix the cause, and — when the tool is genuinely wrong — how to silence one line
without silencing the file.

---

## 1. First: which tool is underlining the code?

Three different things draw red in a `.ts` / `.tsx` file, and they are fixed in
completely different ways. Identify the source before doing anything else.

**Open the Problems panel — `Ctrl/Cmd + Shift + M`.** Every entry names its source
in brackets:

| Source shown | Tool | What it means |
|---|---|---|
| `ts(2307)`, `ts(7031)`, any `ts(…)` | **Built-in TypeScript server** (no extension) | A type or module error. Real. |
| `eslint(rule/name)` | **ESLint extension** | A lint rule fired. |
| `Pylance`, `reportMissingImports` | **Pylance** | Python type/import analysis. |
| `Ruff (F401)` | **Ruff extension** | Python lint rule. |
| no source / faint grey | Spell checker or a theme | Cosmetic. |

A number in `ts(NNNN)` means TypeScript, and **TypeScript is not a linter** — you
cannot turn it off and still have working code. It is the compiler telling you the
build will fail. `npm run build` runs `tsc -b` and will fail on exactly these.

Hovering the squiggle shows the same information.

---

## 2. The cause in *this* repository

The screenshot showed `frontend/src/pages/Landing.tsx` with **every line
underlined**, including plain JSX that is obviously valid. That pattern — the whole
file red, not a few spots — almost always means the language server could not
resolve the project's dependencies, so it treats everything downstream as unknown.

Confirmed by running the same check VS Code runs:

```bash
cd frontend && npx tsc -b --noEmit
```

```
src/components/AIAssistant.tsx(2,27): error TS2307: Cannot find module 'react-markdown' …
src/pages/DocumentDetail.tsx(4,27):  error TS2307: Cannot find module 'react-markdown' …
src/pages/DocumentDetail.tsx(19,18): error TS7031: Binding element 'children' implicitly has an 'any' type.
… 14 more
```

**Root cause:** the host's `frontend/node_modules` was stale. `react-markdown` was
added to `package.json` and installed *inside the Docker image*, which has its own
`node_modules` volume. The app ran fine in the container; the editor on the host had
never seen the package. One unresolved module produced a cascade of `TS7031`
errors, because every callback parameter typed by that module became implicitly
`any`.

**Fix — the actual one:**

```bash
cd frontend
npm install          # host node_modules now matches package.json
npx tsc -b --noEmit  # clean
```

Then in VS Code: `Ctrl/Cmd + Shift + P` → **TypeScript: Restart TS Server**.

This has been done; the tree is clean. **Run `npm install` on the host after any
`git pull` that touches `frontend/package.json`.** Working in Docker makes it easy
to forget, and this exact symptom is what forgetting looks like.

### If it comes back

In order, stopping when the squiggles go:

1. **Restart TS Server** — `Ctrl/Cmd + Shift + P` → `TypeScript: Restart TS Server`.
   Fixes stale state after a branch switch or an install.
2. **Use the workspace TypeScript version** — `Ctrl/Cmd + Shift + P` →
   `TypeScript: Select TypeScript Version` → **Use Workspace Version**. VS Code
   ships its own TypeScript; if it differs from the project's, the editor and the
   build disagree. `.vscode/settings.json` in this repo already points `tsdk` at
   `frontend/node_modules/typescript/lib`.
3. **Reinstall from scratch** — `rm -rf frontend/node_modules && npm install`.
4. **Reload the window** — `Developer: Reload Window`.

---

## 3. Extensions worth installing

`.vscode/extensions.json` in this repository lists these; VS Code offers to install
them when the folder is opened (**Extensions → Recommended**).

| Extension | ID | Why |
|---|---|---|
| **ESLint** | `dbaeumer.vscode-eslint` | Underlines lint problems as you type. **Not configured in this repo yet** — see §4. |
| **Prettier** | `esbenp.prettier-vscode` | Formatting, kept separate from linting. |
| **Tailwind CSS IntelliSense** | `bradlc.vscode-tailwindcss` | Completion for the class strings this UI is built from, and it flags a class name that does not exist. |
| **Python** | `ms-python.python` | Backend interpreter, test running, debugging. |
| **Pylance** | `ms-python.vscode-pylance` | Type checking and import resolution for `backend/`. |
| **Ruff** | `charliermarsh.ruff` | Fast Python linter. Understands the `# noqa:` comments already in this codebase. |
| **Docker** | `ms-azuretools.vscode-docker` | Containers and logs from the sidebar. |

TypeScript itself needs **no extension** — it is built in.

---

## 4. A note on `npm run lint`

`frontend/package.json` declares:

```json
"lint": "eslint ."
```

**ESLint is not installed and there is no config file.** The script fails, and the
ESLint extension has nothing to read — which is why nothing in the screenshot was
an `eslint(...)` error. It was all TypeScript.

Either wire ESLint up:

```bash
cd frontend
npm i -D eslint @eslint/js typescript-eslint eslint-plugin-react-hooks \
         eslint-plugin-react-refresh globals
npx eslint --init      # choose: TypeScript, React, ESM → writes eslint.config.js
```

…or remove the script so it stops advertising a check that does not exist. Leaving
it as-is is the worst of the three.

---

## 5. Silencing a warning — and when that is legitimate

> Sometimes the code is correct and the tool is wrong. Sometimes the tool is right
> and it is inconvenient. Only the first case justifies a suppression, and every
> suppression should say which case it is.

Suppressions are for **lint rules and type-checker limitations**. A `ts(NNNN)`
error from an unresolved module is not a false positive — silencing it hides a
broken build, and `npm run build` fails anyway.

### TypeScript — one line

```ts
// @ts-expect-error - upstream types omit the `size` prop; see PR #123
<Icon size={16} />
```

**Use `@ts-expect-error`, not `@ts-ignore`.** They suppress identically, but
`@ts-expect-error` becomes an error itself once the line stops erroring, so the
comment is removed when the upstream type is fixed. `@ts-ignore` lingers for years
and hides the next, real error on that line.

Always write the reason after the `-`.

### TypeScript — a third-party package with no types

```
TS7016: Could not find a declaration file for module 'some-lib'
```

Prefer the real types:

```bash
npm i -D @types/some-lib
```

If none exist, declare the module once instead of suppressing at each import —
add to `frontend/src/vite-env.d.ts`:

```ts
declare module "some-lib";
```

### ESLint — one line, one rule

```ts
// eslint-disable-next-line react-hooks/exhaustive-deps -- `mutate` is stable; adding it re-fires the effect
}, [runs, isLoading, doc]);
```

Name the specific rule. A bare `// eslint-disable-next-line` disables every rule on
that line, including ones you have not thought about.

Other forms, in descending order of preference:

```ts
/* eslint-disable-next-line no-console */   // one line   — best
foo(); // eslint-disable-line no-console    // one line, trailing
/* eslint-disable no-console */             // rest of file — avoid
```

A rule that is wrong *everywhere* belongs in the config, not in fifty comments:

```js
// eslint.config.js
rules: { "react-refresh/only-export-components": "off" }
```

### Python — Ruff / Flake8

```python
except Exception:  # noqa: BLE001 - one bad batch shouldn't fail the whole document
    logger.exception(...)
```

Always name the code (`BLE001`), never a bare `# noqa`. This codebase already uses
this style throughout `backend/app/services/` — match it.

### Python — Pylance

```python
value = thing.attr  # type: ignore[attr-defined]  # set dynamically by the ORM
```

Project-wide strictness is a setting, not a comment. `.vscode/settings.json` here
uses `"python.analysis.typeCheckingMode": "basic"`; `"off"` disables type analysis
entirely and `"strict"` is much noisier.

---

## 6. Turning the display down (without changing the code)

If squiggles are distracting during a demo, change what is *rendered* rather than
what is *reported*. The Problems panel still lists everything.

`.vscode/settings.json`, or `Ctrl/Cmd + ,`:

```jsonc
{
  // Draw problems in the gutter/Problems panel only, not under the text
  "editor.renderValidationDecorations": "off",

  // Hide the coloured marks in the scrollbar
  "problems.decorations.enabled": false,

  // Stop type-checking JavaScript files that were never meant to be checked
  "js/ts.implicitProjectConfig.checkJs": false
}
```

To check a file **only on save** rather than on every keystroke:

```jsonc
{ "editor.codeActionsOnSave": {}, "eslint.run": "onSave" }
```

**None of this fixes anything.** If `npx tsc -b --noEmit` reports errors, the build
is broken whether or not the editor draws them. Treat these as presentation
settings, and never as a substitute for §2.

---

## 7. The 30-second checklist

```bash
# 1. Does the compiler agree with the editor?
cd frontend && npx tsc -b --noEmit

# 2. Does it build?
npm run build

# 3. Do the backend tests pass?
cd .. && docker compose exec backend python -m pytest tests -q
```

- All three clean, squiggles still showing → stale editor state. **Restart TS
  Server**, then **Use Workspace Version**.
- `tsc` reports `TS2307: Cannot find module` → **`npm install` on the host**. This
  was the cause here.
- A single line is genuinely a tool limitation → `@ts-expect-error` /
  `eslint-disable-next-line <rule>` / `# noqa: CODE`, **with a reason**.
