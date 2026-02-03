# UV Package Manager Decision

## Overview

This project uses **[UV](https://github.com/astral-sh/uv)** as its primary package manager and task runner instead of Poetry. UV is a fast, modern Python package manager written in Rust by Astral (the team behind Ruff).

**Key characteristics:**
- Fast dependency resolution and installation
- Built-in virtual environment management
- Modern, actively developed tooling
- Compatible with standard Python packaging (PEP 621)

## Decision Rationale

### Why UV Instead of Poetry?

While other Exasol Python projects (like `pyexasol`) use Poetry as the standard package manager, we chose UV for the following reasons:

#### 1. Performance
- **10-100x faster** dependency resolution compared to Poetry
- Parallel downloads and installations
- Written in Rust for optimal performance
- Significantly faster CI/CD workflow execution

#### 2. Modern Architecture
- Actively developed by Astral (same team as Ruff)
- Growing adoption in the Python ecosystem
- Forward-looking design principles
- Native support for modern Python standards (PEP 621)

#### 3. Simplicity
- Single tool for environment management, dependency resolution, and execution
- No separate virtualenv management complexity
- Simpler GitHub Actions setup (no Poetry caching intricacies)
- Fewer configuration files and conventions

#### 4. Flexibility
- Can still use `exasol-toolbox` nox sessions (see Hybrid Approach below)
- Not locked into Cookiecutter template structure
- Freedom to customize workflows

#### 5. DBT Ecosystem Alignment
- No strong Poetry standard in the dbt community
- dbt projects use diverse tooling approaches
- UV aligns well with dbt's focus on developer experience

### Trade-offs

While UV provides significant benefits, there are trade-offs:

| Aspect | UV (Current) | Poetry (Alternative) |
|--------|--------------|----------------------|
| **Speed** | ✅ Extremely fast | ❌ Slow dependency resolution |
| **CI/CD Time** | ✅ Faster workflows | ❌ Longer build times |
| **Exasol Consistency** | ❌ Different from other projects | ✅ Standard across Exasol |
| **Toolbox Integration** | ⚠️ Partial (nox only) | ✅ Full integration |
| **Workflow Automation** | ❌ Manual maintenance | ✅ `tbx` CLI for updates |
| **Maturity** | ⚠️ Newer tool | ✅ Well-established |
| **Lock File** | ⚠️ `uv.lock` (newer format) | ✅ `poetry.lock` (TOML standard) |
| **Learning Curve** | ✅ Simple commands | ⚠️ More complex |

### Detailed Analysis of Trade-off Downsides

#### 1. Maturity Concerns (UV as a Newer Tool)

UV is actively developed but relatively new compared to Poetry:

| Concern | Details | Risk Level |
|---------|---------|------------|
| **Battle-tested** | Less production usage history | Medium |
| **Community size** | Smaller community, fewer Stack Overflow answers | Low |
| **Edge cases** | Potential for undiscovered bugs | Medium |
| **Breaking changes** | Newer projects may have more API changes | Medium |
| **Ecosystem support** | Some tools may not yet support UV | Low |

**Mitigating factors:**
- Backed by Astral (same team as Ruff, which is widely adopted)
- Rapid development pace with frequent releases
- Growing adoption in the Python community
- Active GitHub issues resolution

#### 2. Lock File Format Concerns (`uv.lock`)

The `uv.lock` file uses a custom format rather than standard TOML:

| Concern | Details | Impact |
|---------|---------|--------|
| **Format** | Custom format, not TOML like `poetry.lock` | Harder to parse with standard tools |
| **Tooling support** | Dependabot, Renovate may have limited support | Manual dependency updates |
| **Code review** | Less human-readable diffs | Harder to review dependency changes |
| **Ecosystem adoption** | Not widely adopted yet | May need custom tooling |
| **Parsing** | Fewer libraries to parse/analyze | Limited automation options |

**Mitigating factors:**
- UV is gaining rapid adoption, tooling support is improving
- Lock file format is documented and stable
- Dependabot and Renovate are adding UV support
- The format is designed to be more efficient than TOML

#### 3. Exasol Ecosystem Consistency Concerns

Using different tooling than other Exasol projects creates friction:

| Concern | Details | Impact |
|---------|---------|--------|
| **Onboarding** | New contributors must learn UV | Increased ramp-up time |
| **Knowledge transfer** | Poetry expertise doesn't fully apply | Training overhead |
| **Documentation** | Must maintain UV-specific docs | Documentation burden |
| **Cross-project work** | Context switching between tools | Reduced efficiency |

**Mitigating factors:**
- UV commands are simpler and more intuitive than Poetry
- This documentation serves as a complete reference
- UV is gaining traction and may become more common

### Mitigations for Key Downsides

#### Mitigation 1: AI Coding Agents for Workflow Maintenance

The loss of `tbx workflow update` automation is **fully mitigated** by using AI coding agents:

| Manual Task | AI Agent Solution |
|-------------|-------------------|
| Writing new workflows | AI agents can generate workflows from requirements |
| Updating workflows | AI agents can analyze and apply updates |
| Consistency checks | AI agents can compare against Exasol standards |
| Best practice application | AI agents can suggest and implement improvements |

**How it works:**
```bash
# Instead of: tbx workflow update
# Use AI agent with prompts like:
"Update CI workflow to match latest Exasol toolbox patterns"
"Add security scanning to match exasol-toolbox standards"
"Review and improve workflows against Python best practices"
```

**Advantages over `tbx` automation:**
- More flexible - can apply custom requirements
- Context-aware - understands project-specific needs
- Can explain changes and rationale
- Can adapt patterns rather than just copying templates

#### Mitigation 2: Comprehensive Documentation

This document serves as the single source of truth for UV usage, reducing:
- Onboarding friction for new contributors
- Knowledge transfer overhead
- Risk of inconsistent practices

#### Mitigation 3: Hybrid Toolbox Integration

By using toolbox nox sessions, we retain standardized:
- Code formatting
- Linting
- Security scanning
- Testing patterns
- Coverage reporting

#### Mitigation 4: Regular Dependency Tooling Review

We periodically review tooling support for `uv.lock`:
- Check Dependabot/Renovate UV support status
- Evaluate new UV ecosystem tools
- Consider migration if ecosystem support becomes critical

**Decision:** The performance benefits, simpler workflow, and effective mitigations (especially AI-assisted workflow maintenance) outweigh the consistency concerns with other Exasol projects.

## Hybrid Approach: UV + Exasol Python-Toolbox

This project uses a **hybrid approach** that combines the best of both worlds:

### What We Use from Exasol-Toolbox

✅ **Standardized Nox Sessions** (`exasol-toolbox>=1.13.0`)
- `format:check` / `format:fix` - Code formatting
- `lint:code` / `lint:security` / `lint:typing` - Static analysis
- `test:unit` / `test:coverage` - Testing
- `sonar:check` - SonarCloud integration
- `artifacts:copy` - Artifact consolidation

✅ **Configuration System**
- `noxconfig.py` with `BaseConfig` for project settings
- Plugin system via `@hookimpl` for custom hooks

### What We Don't Use from Exasol-Toolbox

❌ **Poetry Dependency Management**
- We use `uv sync` instead of `poetry install`
- We use `uv.lock` instead of `poetry.lock`

❌ **Workflow Templates**
- We maintain `.github/workflows/*.yml` manually
- We don't use `python -m exasol.toolbox.tools.tbx workflow install/update`

❌ **Cookiecutter Project Template**
- We have a custom project structure optimized for dbt-exasol

### Detailed Analysis of Missing Integrations

#### 1. Poetry Dependency Management Gap

| Feature | What's Missing | Impact |
|---------|----------------|--------|
| `poetry install` | Cannot use Poetry commands that toolbox workflows expect | Must adapt all toolbox documentation |
| `poetry.lock` | Standard lock file format not available | Less ecosystem tooling support |
| Poetry plugins | Toolbox Poetry plugins not usable | May miss specialized features |

#### 2. Workflow Templates Gap (Most Significant)

The `tbx` CLI provides powerful automation that we cannot use:

```bash
# These commands are NOT available to us:
python -m exasol.toolbox.tools.tbx workflow install  # Initial setup
python -m exasol.toolbox.tools.tbx workflow update   # Sync with latest
python -m exasol.toolbox.tools.tbx workflow check    # Verify compliance
```

**What's lost:**
- **Automated workflow installation** - Must write workflows from scratch
- **Automated updates** - Cannot pull in toolbox improvements automatically
- **Consistency checks** - No automated verification against Exasol standards
- **Best practice enforcement** - Must manually track and apply best practices
- **Cross-project standardization** - Workflows may drift from other Exasol projects

#### 3. Cookiecutter Template Gap

| Standard Feature | Impact of Missing |
|------------------|-------------------|
| Project structure | Custom layout may confuse Exasol contributors |
| Configuration files | May miss standard config conventions |
| Documentation templates | Must create docs structure manually |
| CI/CD scaffolding | No pre-built workflow templates |

### How It Works

Our `noxfile.py` imports toolbox tasks while executing them via UV:

```python
from exasol.toolbox.nox.tasks import *  # Import standard nox sessions
```

In CI/CD and local development, we run:
```bash
uv run nox -s format:check   # UV executes toolbox's nox session
uv run nox -s lint:code
uv run nox -s test:unit
```

This approach gives us:
- ✅ Standardized toolbox tasks
- ✅ Fast UV execution
- ✅ Flexibility to customize

## Common UV Commands

### Installation & Setup

```bash
# Install UV (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync dependencies from pyproject.toml
uv sync

# Sync with dev dependencies
uv sync --all-extras
```

### Running Commands

```bash
# Run pytest directly
uv run pytest tests/

# Run with parallel execution
uv run pytest -n48 tests/

# Run nox sessions (via exasol-toolbox)
uv run nox -s format:check
uv run nox -s lint:code
uv run nox -s test:unit
uv run nox -s test:unit -- --coverage

# Run Python scripts
uv run python script.py
```

### Dependency Management

```bash
# Add a dependency
uv add pyexasol

# Add a dev dependency
uv add --dev pytest

# Update dependencies
uv sync --upgrade

# Show dependency tree
uv tree
```

### Building & Publishing

```bash
# Build package
uv build

# Publish to PyPI
uv publish --token $PYPI_TOKEN
```

### Virtual Environment

```bash
# UV automatically manages virtualenvs in .venv/
# Activate manually if needed (usually not required)
source .venv/bin/activate  # Unix
.venv\Scripts\activate     # Windows

# UV commands automatically use the virtualenv
uv run <command>  # Preferred - no activation needed
```

## CI/CD Integration

### GitHub Actions Workflows

We use the official `astral-sh/setup-uv` action:

**`.github/workflows/ci.yml`:**
```yaml
- name: Setup uv
  uses: astral-sh/setup-uv@v5
  with:
    python-version: ${{ matrix.python-version }}

- name: Install dependencies
  run: uv sync

- name: Run tests
  run: uv run nox -s test:unit -- --coverage
```

**`.github/workflows/release.yml`:**
```yaml
- name: Setup uv
  uses: astral-sh/setup-uv@v5

- name: Build package
  run: uv build

- name: Publish to PyPI
  run: uv publish --token ${{ secrets.PYPI_TOKEN }}
```

### Devbox Integration

The `devbox.json` scripts use UV:

```json
{
  "shell": {
    "scripts": {
      "format": "uv run nox -s format:check",
      "lint": "uv run nox -s lint:code",
      "unit-test": "uv run nox -s test:unit",
      "coverage": "uv run nox -s test:unit -- --coverage && uv run coverage report -m",
      "ci": "uv run nox -s format:check && uv run nox -s lint:code && uv run nox -s test:unit -- --coverage"
    }
  }
}
```

## Migration Guide (Poetry → UV)

For developers coming from other Exasol projects that use Poetry:

| Poetry Command | UV Equivalent | Notes |
|----------------|---------------|-------|
| `poetry install` | `uv sync` | Installs all dependencies |
| `poetry add <pkg>` | `uv add <pkg>` | Adds a dependency |
| `poetry add --group dev <pkg>` | `uv add --dev <pkg>` | Adds dev dependency |
| `poetry run <cmd>` | `uv run <cmd>` | Executes command in venv |
| `poetry shell` | `source .venv/bin/activate` | Activates virtualenv (rarely needed) |
| `poetry build` | `uv build` | Builds package |
| `poetry publish` | `uv publish` | Publishes to PyPI |
| `poetry lock` | `uv sync` | Updates lock file |
| `poetry show` | `uv tree` | Shows dependencies |

### Key Differences

1. **Lock File Format**
   - Poetry: `poetry.lock` (TOML format)
   - UV: `uv.lock` (custom format)
   - Both files should be committed to version control

2. **Virtualenv Management**
   - Poetry: Creates venvs in global cache by default
   - UV: Creates `.venv/` in project directory
   - UV's approach is more transparent and IDE-friendly

3. **Dependency Groups**
   - Poetry: Uses `[tool.poetry.group.dev.dependencies]`
   - UV: Uses `[project.optional-dependencies]` and `[dependency-groups]` (PEP 735)

4. **Speed**
   - UV is significantly faster for all operations
   - Initial sync: ~2-5s vs ~30-60s with Poetry

## Migrating Legacy Exasol Poetry Projects to UV Hybrid Approach

This chapter provides a step-by-step guide for migrating existing Exasol ecosystem projects from Poetry to the UV hybrid approach while retaining exasol-toolbox nox session compatibility.

### Migration Overview

The migration process converts a Poetry-based Exasol project to use UV while keeping:
- Exasol-toolbox nox sessions for standardized tasks
- Compatibility with existing CI/CD patterns
- All existing functionality intact

**Estimated time:** 2-4 hours for a typical project

### Pre-Migration Checklist

Before starting the migration:

- [ ] Ensure all tests pass with current Poetry setup
- [ ] Commit all pending changes
- [ ] Create a migration branch: `git checkout -b migrate-to-uv`
- [ ] Document current Python version requirements
- [ ] List all Poetry dependency groups in use
- [ ] Backup `poetry.lock` (for reference)

### Step-by-Step Migration Process

#### Step 1: Install UV

```bash
# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Verify installation
uv --version
```

#### Step 2: Analyze Current Poetry Configuration

Review the existing `pyproject.toml` to understand:

```bash
# Check Poetry-specific sections
grep -A 50 "\[tool.poetry\]" pyproject.toml

# List all dependency groups
grep -E "^\[tool\.poetry\.group\." pyproject.toml
```

**Key sections to identify:**
- `[tool.poetry]` - Package metadata
- `[tool.poetry.dependencies]` - Main dependencies
- `[tool.poetry.group.dev.dependencies]` - Dev dependencies
- `[tool.poetry.group.*.dependencies]` - Other groups
- `[tool.poetry.scripts]` - Entry points
- `[tool.poetry.plugins]` - Plugin definitions

#### Step 3: Convert pyproject.toml to PEP 621 Format

The biggest change is converting Poetry's proprietary format to PEP 621 standard.

**Before (Poetry format):**
```toml
[tool.poetry]
name = "my-exasol-project"
version = "1.0.0"
description = "An Exasol project"
authors = ["Author <author@example.com>"]
readme = "README.md"
packages = [{include = "my_package"}]

[tool.poetry.dependencies]
python = "^3.9"
pyexasol = "^0.26.0"
exasol-toolbox = "^1.13.0"

[tool.poetry.group.dev.dependencies]
pytest = "^7.0"
nox = "^2023.4.22"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
```

**After (PEP 621 + UV format):**
```toml
[project]
name = "my-exasol-project"
version = "1.0.0"
description = "An Exasol project"
authors = [{name = "Author", email = "author@example.com"}]
readme = "README.md"
requires-python = ">=3.9"
dependencies = [
    "pyexasol>=0.26.0",
    "exasol-toolbox>=1.13.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "nox>=2023.4.22",
]

[dependency-groups]
dev = [
    "pytest>=7.0",
    "nox>=2023.4.22",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["my_package"]
```

**AI Agent Prompt for Conversion:**
```
Convert this Poetry-based pyproject.toml to PEP 621 format compatible with UV:

<paste current pyproject.toml>

Requirements:
1. Convert [tool.poetry] to [project] section (PEP 621)
2. Convert poetry dependencies to PEP 508 format (>=X.Y instead of ^X.Y)
3. Convert dependency groups to [dependency-groups] (PEP 735)
4. Keep [project.optional-dependencies] for backward compatibility
5. Change build-system to hatchling
6. Preserve all tool.* sections (ruff, pytest, mypy, etc.)
7. Keep exasol-toolbox as a dependency for nox sessions
```

#### Step 4: Version Specifier Conversion

Poetry uses different version specifiers than PEP 508:

| Poetry | PEP 508 (UV) | Meaning |
|--------|--------------|---------|
| `^1.2.3` | `>=1.2.3,<2.0.0` | Compatible release |
| `~1.2.3` | `>=1.2.3,<1.3.0` | Approximately equivalent |
| `1.2.3` | `==1.2.3` | Exact version |
| `>=1.2.3` | `>=1.2.3` | Minimum version (same) |
| `*` | `>=0.0.0` | Any version |

**Simplified conversion:** For most cases, `^X.Y.Z` can be safely converted to `>=X.Y.Z` (UV will resolve compatible versions).

#### Step 5: Generate UV Lock File

```bash
# Remove Poetry virtual environment (optional, but recommended)
rm -rf .venv

# Generate new lock file with UV
uv sync

# This creates:
# - .venv/ directory with new virtualenv
# - uv.lock with resolved dependencies
```

#### Step 6: Verify Nox Sessions Still Work

Test that exasol-toolbox nox sessions work with UV:

```bash
# Test formatting
uv run nox -s format:check

# Test linting
uv run nox -s lint:code

# Test unit tests
uv run nox -s test:unit

# If any fail, check noxfile.py for Poetry-specific code
```

#### Step 7: Update noxfile.py (If Needed)

Most noxfiles should work unchanged. Check for Poetry-specific patterns:

**Before (Poetry-specific):**
```python
@nox.session
def tests(session):
    session.run("poetry", "install")
    session.run("poetry", "run", "pytest")
```

**After (UV-compatible):**
```python
from exasol.toolbox.nox.tasks import *  # Use toolbox sessions

# Or custom sessions:
@nox.session
def tests(session):
    session.run("uv", "sync", external=True)
    session.run("uv", "run", "pytest", external=True)
```

#### Step 8: Update GitHub Actions Workflows

Replace Poetry setup with UV setup in all workflow files:

**Before (Poetry):**
```yaml
- name: Install Poetry
  uses: snok/install-poetry@v1
  
- name: Install dependencies
  run: poetry install
  
- name: Run tests
  run: poetry run pytest
```

**After (UV):**
```yaml
- name: Setup uv
  uses: astral-sh/setup-uv@v5
  with:
    python-version: ${{ matrix.python-version }}

- name: Install dependencies
  run: uv sync

- name: Run tests
  run: uv run pytest
```

**AI Agent Prompt for Workflow Conversion:**
```
Convert this GitHub Actions workflow from Poetry to UV:

<paste workflow file>

Requirements:
1. Replace snok/install-poetry with astral-sh/setup-uv@v5
2. Replace 'poetry install' with 'uv sync'
3. Replace 'poetry run <cmd>' with 'uv run <cmd>'
4. Replace 'poetry build' with 'uv build'
5. Replace 'poetry publish' with 'uv publish'
6. Update any caching to use UV cache paths
7. Keep all existing job structure and matrix settings
```

#### Step 9: Update CI Scripts and Makefiles

Search for and update any Poetry references:

```bash
# Find Poetry references
grep -r "poetry" --include="*.sh" --include="Makefile" --include="*.mk" .

# Common replacements:
# poetry install    → uv sync
# poetry run        → uv run
# poetry build      → uv build
# poetry publish    → uv publish
# poetry add        → uv add
# poetry lock       → uv lock
```

#### Step 10: Update Documentation

Update README.md and other docs:

```markdown
## Before (Poetry)
poetry install
poetry run pytest

## After (UV)
uv sync
uv run pytest
```

#### Step 11: Clean Up

```bash
# Remove Poetry files (keep for reference initially)
# rm poetry.lock  # Remove after confirming migration works
# rm poetry.toml  # If exists

# Remove Poetry from dev dependencies if it was listed
# (It's no longer needed)

# Update .gitignore if needed
echo ".venv/" >> .gitignore  # UV creates local venv
```

#### Step 12: Final Verification

```bash
# Full test suite
uv run pytest

# All nox sessions
uv run nox -s format:check
uv run nox -s lint:code
uv run nox -s lint:typing
uv run nox -s test:unit -- --coverage

# Build package
uv build

# Verify package contents
ls dist/
```

### Migration Script

For automating the migration, use this script with an AI coding agent:

```bash
#!/bin/bash
# migrate-poetry-to-uv.sh

set -e

echo "=== Exasol Poetry to UV Migration ==="

# Step 1: Create migration branch
git checkout -b migrate-to-uv

# Step 2: Backup current state
cp pyproject.toml pyproject.toml.poetry-backup
cp poetry.lock poetry.lock.backup 2>/dev/null || true

# Step 3: Use AI agent to convert pyproject.toml
echo "Please run AI agent to convert pyproject.toml..."
echo "Prompt: Convert pyproject.toml from Poetry to PEP 621 format for UV"

# Step 4: Generate UV lock file
uv sync

# Step 5: Test nox sessions
echo "Testing nox sessions..."
uv run nox -s format:check || echo "format:check needs fixes"
uv run nox -s lint:code || echo "lint:code needs fixes"

# Step 6: Run tests
echo "Running tests..."
uv run pytest -x

echo "=== Migration complete - please review changes ==="
git status
```

### Common Migration Issues

#### Issue 1: Poetry Plugins Not Available

**Problem:** Project uses Poetry plugins (e.g., poetry-dynamic-versioning)

**Solution:** Find UV/hatch equivalents or implement differently:
```toml
# Instead of poetry-dynamic-versioning, use:
[tool.hatch.version]
source = "vcs"
```

#### Issue 2: Complex Dependency Groups

**Problem:** Multiple Poetry dependency groups with complex relationships

**Solution:** Map to PEP 735 dependency groups:
```toml
[dependency-groups]
dev = ["pytest>=7.0", "nox>=2023.4.22"]
docs = ["sphinx>=6.0", "furo>=2023.1.1"]
test = [{include-group = "dev"}, "coverage>=7.0"]
```

#### Issue 3: Private Package Repositories

**Problem:** Project uses private PyPI repositories configured in Poetry

**Solution:** Configure UV with the same repositories:
```toml
# In pyproject.toml
[[tool.uv.index]]
name = "private"
url = "https://private.pypi.example.com/simple"
```

Or via environment:
```bash
export UV_EXTRA_INDEX_URL="https://private.pypi.example.com/simple"
```

#### Issue 4: Build Scripts

**Problem:** Poetry build hooks or custom build scripts

**Solution:** Convert to hatchling build hooks:
```toml
[tool.hatch.build.hooks.custom]
path = "build_hooks.py"
```

#### Issue 5: Path Dependencies

**Problem:** Local path dependencies for monorepo setups

**Solution:** UV supports path dependencies:
```toml
[project]
dependencies = [
    "local-package @ file:///${PROJECT_ROOT}/../local-package",
]

# Or use UV workspaces for monorepos
[tool.uv.workspace]
members = ["packages/*"]
```

### Post-Migration Checklist

- [ ] All tests pass: `uv run pytest`
- [ ] All nox sessions work: `uv run nox -l` (list) and run each
- [ ] Package builds correctly: `uv build`
- [ ] CI/CD pipeline passes (create PR to test)
- [ ] Documentation updated
- [ ] Team notified of tooling change
- [ ] Old Poetry files removed (after confirmation period)
- [ ] Add this uv.md document to the project for reference

### Rollback Plan

If migration fails and you need to rollback:

```bash
# Restore Poetry files
mv pyproject.toml.poetry-backup pyproject.toml
mv poetry.lock.backup poetry.lock

# Remove UV files
rm -rf .venv uv.lock

# Reinstall with Poetry
poetry install

# Discard migration branch
git checkout main
git branch -D migrate-to-uv
```

## Troubleshooting

### Common Issues

**Issue: `uv: command not found`**
```bash
# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or via pipx
pipx install uv

# Or via homebrew (macOS)
brew install uv
```

**Issue: Lock file out of sync**
```bash
# Regenerate lock file
uv sync --upgrade
```

**Issue: Dependencies not resolving**
```bash
# Clear cache and retry
uv cache clean
uv sync
```

**Issue: Wrong Python version**
```bash
# UV respects requires-python in pyproject.toml
# Check current version
python --version

# Use specific Python version
uv sync --python 3.11
```

### Getting Help

- UV Documentation: https://docs.astral.sh/uv/
- UV GitHub: https://github.com/astral-sh/uv
- Report issues: https://github.com/tglunde/dbt-exasol/issues

## Automated Project Updates with AI Coding Agents

This section provides a detailed plan for using AI coding agents to automatically update and maintain UV-based projects, replacing the `tbx workflow update` functionality.

### Overview

AI coding agents (such as Claude, GPT-4, or specialized coding assistants) can be used to:
- Update GitHub Actions workflows to latest patterns
- Sync with Exasol toolbox best practices
- Apply security patches and improvements
- Migrate configurations when standards change

### Prerequisites

Before using AI coding agents for project updates:

1. **AI Coding Agent Access**
   - IDE-integrated agent (Cursor, GitHub Copilot, etc.)
   - CLI-based agent (Claude CLI, OpenCode, aider, etc.)
   - API access for automation scripts

2. **Reference Materials**
   - Exasol toolbox repository: `https://github.com/exasol/python-toolbox`
   - Exasol toolbox documentation: `https://exasol.github.io/python-toolbox/`
   - Current project workflows and configurations

3. **Project Context**
   - This `uv.md` document
   - Existing workflow files in `.github/workflows/`
   - Current `pyproject.toml` and `noxfile.py`

### Update Procedures

#### Procedure 1: Update CI Workflows

**When to run:** Monthly or when toolbox releases new workflow patterns

**AI Agent Prompt:**
```
Review the current CI workflow at .github/workflows/ci.yml and compare it against 
the latest Exasol python-toolbox workflow patterns at:
https://github.com/exasol/python-toolbox/tree/main/.github/workflows

Update our workflow to incorporate any improvements while maintaining UV compatibility:
- Keep using astral-sh/setup-uv@v5 instead of Poetry
- Keep using 'uv sync' and 'uv run' commands
- Apply any new job structures, caching strategies, or security improvements
- Update action versions to latest stable releases

Explain what changes you're making and why.
```

**Verification steps:**
1. Review the proposed changes
2. Run `uv run nox -s format:check` locally
3. Create a PR and verify CI passes
4. Merge after review

#### Procedure 2: Update Security Scanning

**When to run:** Quarterly or after security advisories

**AI Agent Prompt:**
```
Review our GitHub Actions workflows for security best practices:

1. Check .github/workflows/ for:
   - Pinned action versions (use SHA instead of tags where possible)
   - Minimal permissions (GITHUB_TOKEN scopes)
   - Secret handling best practices
   - Dependency scanning (Dependabot, CodeQL)

2. Compare against Exasol toolbox security patterns at:
   https://github.com/exasol/python-toolbox

3. Update workflows to address any security gaps while maintaining UV compatibility.

List all security improvements made.
```

#### Procedure 3: Update Nox Sessions

**When to run:** When exasol-toolbox releases new nox sessions

**AI Agent Prompt:**
```
Check the latest exasol-toolbox release for new or updated nox sessions:
https://github.com/exasol/python-toolbox/blob/main/exasol/toolbox/nox/tasks.py

Compare with our current noxfile.py and:
1. Identify any new sessions we should adopt
2. Check if existing session signatures have changed
3. Update noxconfig.py if configuration options changed
4. Ensure all sessions work with 'uv run nox -s <session>'

Document any new sessions added and their purpose.
```

#### Procedure 4: Update Dependencies

**When to run:** Weekly or after security advisories

**AI Agent Prompt:**
```
Review and update project dependencies:

1. Run 'uv sync --upgrade' to update all dependencies
2. Check for any breaking changes in updated packages
3. Review the diff in uv.lock for significant version jumps
4. Run the test suite: 'uv run pytest -n4'
5. Fix any compatibility issues

If there are breaking changes, document them and propose fixes.
```

#### Procedure 5: Full Project Sync with Toolbox Standards

**When to run:** Quarterly or before major releases

**AI Agent Prompt:**
```
Perform a comprehensive sync of this project with Exasol python-toolbox standards:

Reference repositories:
- https://github.com/exasol/python-toolbox
- https://github.com/exasol/pyexasol (for Poetry-based comparison)

Review and update:
1. GitHub Actions workflows - apply latest patterns (keep UV)
2. noxfile.py and noxconfig.py - sync with toolbox conventions
3. pyproject.toml - ensure PEP 621 compliance and best practices
4. Pre-commit hooks - update to latest versions
5. Documentation structure - align with Exasol standards where applicable

For each change:
- Explain what's being updated
- Note any Exasol conventions we're intentionally skipping (due to UV)
- Verify the change works with UV tooling

Create a summary of all updates made.
```

### Automation Script

For teams wanting to automate regular updates, here's a script pattern:

```bash
#!/bin/bash
# update-project.sh - Run with AI coding agent CLI

# Example using Claude CLI (adjust for your agent)
AGENT_CMD="claude"  # or "opencode", "aider", etc.

# Monthly CI workflow update
$AGENT_CMD "Review and update .github/workflows/ci.yml against latest 
Exasol toolbox patterns. Maintain UV compatibility. Create a commit 
with changes if any updates are needed."

# Run verification
uv run nox -s format:check
uv run nox -s lint:code
uv run pytest -n4

# If all pass, the agent's changes are ready for review
git status
```

### Tracking Updates

Maintain an update log to track AI-assisted changes:

| Date | Update Type | Agent Used | Changes Made | Verified By |
|------|-------------|------------|--------------|-------------|
| 2026-01 | CI Workflow | Claude | Updated action versions | CI pipeline |
| 2026-01 | Security | Claude | Added CodeQL scanning | Security team |

### Best Practices for AI-Assisted Updates

1. **Always review AI-generated changes** - Don't blindly accept updates
2. **Run full test suite** - Verify changes don't break functionality
3. **Use version control** - Create branches for update PRs
4. **Document deviations** - Note when we intentionally skip toolbox patterns
5. **Keep context files updated** - Maintain this uv.md as the source of truth
6. **Batch related updates** - Group workflow updates in single PRs
7. **Test in CI first** - Let GitHub Actions validate before merging

### Comparison: AI Agents vs tbx CLI

| Aspect | `tbx workflow update` | AI Coding Agent |
|--------|----------------------|-----------------|
| **Automation** | Fully automated | Semi-automated (requires prompts) |
| **Flexibility** | Template-based only | Can apply custom requirements |
| **Context awareness** | None (applies templates) | Understands project specifics |
| **Explanation** | None | Can explain rationale |
| **Adaptation** | Copy templates exactly | Can adapt patterns intelligently |
| **UV compatibility** | No (Poetry only) | Yes (can maintain UV tooling) |
| **Learning** | Static | Improves with better prompts |
| **Cost** | Free | API costs (if applicable) |

**Conclusion:** AI coding agents provide a more flexible and powerful alternative to `tbx workflow update`, with the added benefit of maintaining UV compatibility and providing explanations for changes.

## Future Considerations

This decision may be reconsidered if:

1. **Exasol mandates Poetry organization-wide** for consistency across all projects
2. **UV development stalls** or the project becomes unmaintained
3. **Critical toolbox features** become available that require Poetry integration
4. **UV compatibility issues** arise that cannot be resolved
5. **Team consensus shifts** toward preferring Poetry despite performance trade-offs
6. **AI coding agents become unavailable** or ineffective for workflow maintenance

For now, UV provides the best developer experience and CI/CD performance for this project, with AI coding agents effectively mitigating the workflow automation gap.

## References

- [UV Documentation](https://docs.astral.sh/uv/)
- [Exasol Python-Toolbox](https://github.com/exasol/python-toolbox)
- [Exasol Toolbox Documentation](https://exasol.github.io/python-toolbox/)
- [PEP 621 - Python Project Metadata](https://peps.python.org/pep-0621/)
- [PEP 735 - Dependency Groups](https://peps.python.org/pep-0735/)

---

**Last Updated:** January 2026  
**Decision Owner:** dbt-exasol maintainers
