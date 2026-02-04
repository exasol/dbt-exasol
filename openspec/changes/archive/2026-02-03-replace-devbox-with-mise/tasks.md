## 1. Implementation

- [x] 1.1 Create `mise.toml` with:
  - JSON schema reference (`#:schema https://mise.jdx.dev/schema/mise.json`)
  - Tool versions (`uv`, `gh`, `bun`, `usage`) with version constraints
  - Environment loading (`test.env` as defaults, `.env` for overrides)
  - Required environment variables using `{ required = "help text" }` syntax
  - Docker SSH tunnel using mise templates (conditional on `DOCKER_SSH_HOST`)
  - Tasks with descriptions (`test`, `sync`, `lint`, `nox`)

- [x] 1.2 Update `.gitignore` to include:
  - `mise.local.toml` (developer-specific overrides)
  - `.env` (local environment overrides, if not already present)

- [x] 1.3 Verify mise configuration:
  - Run `mise install` and confirm tools are installed
  - Run `mise env` and verify environment variables are set correctly
  - Test Docker SSH tunnel by setting `DOCKER_SSH_HOST` and verifying `DOCKER_HOST`
  - Test required variables by unsetting one and confirming error message

- [x] 1.4 Verify mise tasks:
  - Run `mise tasks` and confirm all tasks are listed with descriptions
  - Run `mise run sync` and verify `uv sync` executes
  - Run `mise run test --help` or a quick test
  - Run `mise run lint` and verify both ruff and sqlfluff run
  - Run `mise run nox -- --version` and verify arguments pass through

- [x] 1.5 Remove legacy files:
  - `devbox.json`
  - `devbox.lock`
  - `.envrc`
  - `.devbox/` directory

- [x] 1.6 Update `README.md`:
  - Replace devbox instructions with mise setup
  - Document: install mise, shell activation, `mise trust`, `mise install`
  - Document available tasks (`mise run test`, etc.)
  - Mention `mise.local.toml` for local overrides
