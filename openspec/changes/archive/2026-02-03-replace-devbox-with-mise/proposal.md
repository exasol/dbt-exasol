# Change: Replace Devbox with Mise-en-place

## Why
The project currently uses `devbox` and `direnv` for managing the development environment. Moving to `mise-en-place` (mise) consolidates tool version management, environment variable configuration, and task running into a single tool. This simplifies the developer workflow, reduces dependencies (removing `devbox` and `direnv`), and provides a faster, cleaner setup.

## What Changes
- Remove `devbox.json` and `devbox.lock`.
- Remove `.envrc` and the `.devbox/` directory.
- Add `mise.toml` to configure:
  - **Tools:** `uv`, `gh`, `bun`, `usage` with version constraints.
  - **Environment:**
    - Load `test.env` for default environment variables.
    - Load `.env` for local overrides (gitignored).
    - Use mise's native `required` directive for mandatory variables (`DBT_DSN`, `DBT_USER`, etc.).
    - Use mise templates for conditional Docker SSH tunnel configuration.
  - **Tasks:** Define standard development tasks (`test`, `sync`, `lint`, `nox`) with descriptions.
- Add `mise.local.toml` to `.gitignore` for developer-specific overrides.
- Include JSON schema reference for IDE autocompletion.

## Impact
- **Affected specs:** `development-environment` (New capability).
- **Affected code:** Root configuration files (`devbox.json`, `.envrc`, `mise.toml`, `.gitignore`).
- **Developer Workflow:**
  1. Install `mise` ([mise.jdx.dev/installing-mise](https://mise.jdx.dev/installing-mise.html)).
  2. Add shell activation to rc file: `eval "$(mise activate bash)"` (or zsh/fish).
  3. Run `mise trust` in the project directory (one-time).
  4. Run `mise install` to install tools.
  5. Commands: `mise run test`, `mise run lint`, or use shims directly (`nox`, `uv`).
