# dbt-exasol

![CI](https://github.com/tglunde/dbt-exasol/actions/workflows/ci.yml/badge.svg)

**[dbt](https://www.getdbt.com/)** enables data analysts and engineers to transform their data using the same practices that software engineers use to build applications.

Please see the dbt documentation on **[Exasol setup](https://docs.getdbt.com/reference/warehouse-setups/exasol-setup)** for more information on how to start using the Exasol adapter.

## Version Compatibility

| dbt-exasol | dbt-core | Python | Exasol |
|------------|----------|--------|--------|
| 1.10.x     | 1.10.x   | 3.10-3.13 | 7.x, 8.x |
| 1.8.x      | 1.8.x    | 3.9-3.12 | 7.x, 8.x |
| 1.7.x      | 1.7.x    | 3.8-3.11 | 7.x, 8.x |

## Development Setup

This project uses [mise-en-place](https://mise.jdx.dev/) for managing development tools and environment.

### Prerequisites

1. Install mise: [mise.jdx.dev/installing-mise](https://mise.jdx.dev/installing-mise.html)
2. Add shell activation to your rc file:

   ```bash
   # For bash (~/.bashrc)
   eval "$(mise activate bash)"

   # For zsh (~/.zshrc)
   eval "$(mise activate zsh)"

   # For fish (~/.config/fish/config.fish)
   mise activate fish | source
   ```

### Getting Started

```bash
# Trust the project configuration (one-time)
mise trust

# Install development tools (uv, gh, bun, usage)
mise install

# Sync Python dependencies
mise run sync
```

### Available Tasks

| Command | Description |
|---------|-------------|
| `mise run test` | Run all tests with coverage (nox -s test:coverage) |
| `mise run test:unit` | Run unit tests only |
| `mise run test:integration` | Run integration tests only |
| `mise run format` | Auto-format code (nox -s format:fix) |
| `mise run format-check` | Check code formatting without changes |
| `mise run lint` | Run all linters (code + security) |
| `mise run check` | Run all checks (format, lint, type) |
| `mise run sync` | Sync dependencies using uv |
| `mise run nox` | Run nox sessions directly |
| `mise run tunnel-start` | Start SSH tunnel to remote Docker host |
| `mise run tunnel-stop` | Stop SSH tunnel |
| `mise run tunnel-status` | Check SSH tunnel status |
| `mise run tunnel-restart` | Restart SSH tunnel |

Arguments can be passed to tasks: `mise run nox -- -s test:unit`

### Environment Configuration

See @mise.toml [env] section for environment variables with default values.

- `.env` - Local overrides (gitignored)
- Required environment variables (`DBT_DSN`, `DBT_USER`, `DBT_PASS`, etc. as described in @mise.toml)
- `mise.local.toml` - Developer-specific mise overrides (gitignored)

### Docker SSH Tunnel

To use a remote Docker host via SSH:

1. **Configure the connection** in `.env`:

   ```bash
   DOCKER_HOST=ssh://user@remote-host
   ```

2. **Manage the SSH tunnel** using mise tasks:

   ```bash
   # Start the SSH tunnel
   mise run tunnel-start

   # Check tunnel status
   mise run tunnel-status

   # Stop the tunnel
   mise run tunnel-stop

   # Restart the tunnel
   mise run tunnel-restart
   ```

The tunnel manager creates a persistent SSH connection that Docker can use for remote operations. It handles:

- Background SSH master connection with control sockets
- Automatic PID tracking
- Graceful shutdown and cleanup
- Connection keepalive (60s intervals)

**Requirements:**

- SSH access to the remote host with key-based authentication
- SSH keys available in `~/.ssh/` or SSH agent
- Docker installed on the remote host

**Troubleshooting:**

```bash
# Check detailed status
mise run tunnel-status

# View tunnel process
ps aux | grep ssh

# Test Docker connection
docker -H ssh://user@remote-host ps
```

# Current profile.yml settings

<File name='profiles.yml'>

```yaml
dbt-exasol:
  target: dev
  outputs:
    dev:
      type: exasol
      threads: 1
      dsn: HOST:PORT
      user: USERNAME
      password: PASSWORD
      dbname: db
      schema: SCHEMA
```

## Optional login credentials using OpenID for Exasol SaaS

OpenID login through access_token or refresh_token instead of user+password

## Optional parameters

<ul>
  <li><strong>connection_timeout</strong>: defaults to pyexasol default</li>
  <li><strong>socket_timeout</strong>: defaults to pyexasol default</li>
  <li><strong>query_timeout</strong>: defaults to pyexasol default</li>
  <li><strong>compression</strong>: default: False</li>
  <li><strong>encryption</strong>: default: True</li>
  <li><strong>validate_server_certificate</strong>: default: True (requires valid SSL certificate when encryption=True)</li>
  <li><strong>protocol_version</strong>: default: v3</li>
  <li><strong>row_separator</strong>: default: CRLF for windows - LF otherwise</li>
  <li><strong>timestamp_format</strong>: default: YYYY-MM-DDTHH:MI:SS.FF6</li>
</ul>

# Known isues

## >=1.8.1 additional parameters

As of dbt-exasol 1.8.1 it is possible to add new model config parameters for models materialized as table or incremental.

<ul>
<li><strong>partition_by_config</strong></li>
<li><strong>distribute_by_config</strong></li>
<li><strong>primary_key_config</strong></li>
</ul>

- Example table materialization config

```yaml
{{
    config(
        materialized='table',
        primary_key_config=['<column>','<column2>'],
        partition_by_config='<column>',
        distribute_by_config='<column>'
    )
}}
```

---

**NOTE**
In case more than one column is used, put them in a list.

---

## >=1.8 license change

As of dbt-exasol version 1.8 we have decided to switch to Apache License from GPLv3 - to be equal to dbt-core licensing.

## setuptools breaking change

Due to a breaking change in setuptools and a infected dependency from dbt-core, we need to use the following [workaround for poetry install](https://github.com/pypa/setuptools/issues/4519#issuecomment-2255446798).

## Using encryption in Exasol 7 vs. 8

Starting from Exasol 8, encryption is enforced by default. If you are still using Exasol 7 and have trouble connecting, you can disable encryption in profiles.yaml (see optional parameters).

## SSL/TLS Certificate Validation

By default, dbt-exasol validates SSL/TLS certificates when `encryption=True` (which is the default). This provides secure connections and suppresses PyExasol warnings about certificate validation behavior.

**Default behavior (recommended for production):**

```yaml
outputs:
  prod:
    type: exasol
    encryption: true  # default
    validate_server_certificate: true  # default
    # ... other settings
```

**For development/testing with self-signed certificates:**

```yaml
outputs:
  dev:
    type: exasol
    encryption: true
    validate_server_certificate: false  # Skip cert validation (not recommended for production)
    # ... other settings
```

**Alternative for self-signed certificates:** Use the `nocertcheck` fingerprint in the DSN:

```yaml
outputs:
  dev:
    type: exasol
    dsn: myhost/nocertcheck:8563
    # ... other settings
```

For more information about SSL configuration, see the [PyExasol security documentation](https://exasol.github.io/pyexasol/master/user_guide/configuration/security.html).

## Materialized View & Clone operations

In Exasol materialized views and clone operations are not suported. Default behaviour from dbt-core will fail accordingly.

## Null handling in test_utils null safe handling

In Exasol empty string are NULL. Due to this behaviour and as of [this pull request 7776 published in dbt-core 1.6](https://github.com/dbt-labs/dbt-core/pull/7776),
seeds in tests that use EMPTY literal to simulate empty string have to be handled with special behaviour in exasol.
See fixture for csv in exasol**seeds**data_hash_csv for tests/functional/adapter/utils/test_utils.py::TestHashExasol.

## Model contracts

The following database constraints are implemented for Exasol:

| Constraint Type | Status        |
| --------------- | ------------- |
| check           | NOT supported |
| not null        | enforced      |
| unique          | NOT supported |
| primary key     | enforced      |
| foreign key     | enforced      |

## >=1.5 Incremental model update

Fallback to dbt-core implementation and supporting strategies:

- `append` - Insert new rows
- `merge` - Update existing rows, insert new rows
- `delete+insert` - Delete matching rows, insert all rows
- `microbatch` (new in 1.10) - Process data in time-based batches

### Microbatch Strategy

The microbatch strategy processes data in time-based batches, enabling:

- Efficient processing of large datasets
- Support for late-arriving data via `lookback`
- Sample mode (`--sample`) for development

**Example configuration:**

```sql
{{ config(
    materialized='incremental',
    incremental_strategy='microbatch',
    event_time='created_at',
    begin='2024-01-01',
    batch_size='day',
    lookback=2
) }}
select * from {{ ref('source_table') }}
```

**Configuration options:**

| Option | Required | Description |
|--------|----------|-------------|
| `event_time` | Yes | Column used for time-based filtering |
| `begin` | Yes | Start date for initial backfill (YYYY-MM-DD) |
| `batch_size` | Yes | Size of each batch: `hour`, `day`, `month`, `year` |
| `lookback` | No | Number of previous batches to reprocess |

See [dbt Microbatch Documentation](https://docs.getdbt.com/docs/build/incremental-microbatch) for more details.

### Sample Mode

Sample mode (`--sample` flag) runs dbt in "small-data" mode, building only the N most recent time-based slices of microbatch models. This is useful for:

- Development and testing with representative data
- Quick iteration without processing full history

**Example usage:**

```bash
# Process only 2 most recent days
dbt run --sample="2 days"

# Process most recent week
dbt run --sample="1 week"
```

**Requirements:**

- Models using `incremental_strategy='microbatch'`
- dbt-core 1.10 or later

See [Sample Mode Documentation](https://docs.getdbt.com/docs/build/sample-flag) for more details.

### Microbatch/Sample Mode Notes (Exasol-specific)

**Timestamp Format:** Exasol requires timestamps without timezone suffix in model definitions:

```sql
-- Correct (Exasol compatible)
TIMESTAMP '2024-01-01 10:00:00'

-- Incorrect (will cause parse errors)
TIMESTAMP '2024-01-01 10:00:00-0'
```

The dbt-exasol adapter automatically handles timestamp formatting for microbatch boundaries.

**Batch Processing:**

- Microbatch uses DELETE + INSERT pattern for batch replacement
- Each batch window is processed as a separate transaction
- For large datasets, consider `batch_size='day'` over `batch_size='hour'`

## >=1.3 Python model not yet supported - WIP

- Please follow [this pull request](https://github.com/tglunde/dbt-exasol/pull/59)

## Breaking changes with release 1.2.2

- Timestamp format defaults to YYYY-MM-DDTHH:MI:SS.FF6

## SQL functions compatibility

### split_part

There is no equivalent SQL function in Exasol for split_part.

### listagg part_num

The SQL function listagg in Exasol does not support the num_part parameter.

## Utilities shim package

In order to support packages like dbt-utils and dbt-audit-helper, we needed to create the [shim package exasol-utils](https://github.com/exasol/dbt-exasol-utils).

# Development

## CI/CD

This project uses GitHub Actions for continuous integration and deployment:

- **CI Workflow**: Runs on pull requests, pushes to main/master, scheduled nightly, and manual dispatch
  - **Smart Integration Testing**: Only runs integration tests when relevant files change (on PRs)
  - **Python Matrix**: Tests across Python 3.10, 3.11, 3.12, and 3.13
  - **Checks Job** (runs for all Python versions):
    - Format checking (`nox -s format:check`)
    - Linting (`nox -s lint:code`)
    - Security checks (`nox -s lint:security`)
    - Type checking (`nox -s lint:typing`)
    - Unit tests with coverage reporting (`nox -s test:unit`)
  - **Integration Job** (parallel execution with 8 workers):
    - Functional tests against Exasol database (`nox -s test:integration`)
    - Conditional execution based on file changes
  - **Report Job**:
    - Combines coverage from all jobs
    - SonarCloud integration for quality gates and coverage reporting
  - **Concurrency Control**: Cancels redundant runs on the same branch

- **Release Workflow**: Triggered by version tags
  - Builds package using `uv build`
  - Publishes to PyPI
  - Creates GitHub Release

## Local Development Commands

The following commands are available via mise:

```bash
# Run format check
mise run format-check

# Auto-format code
mise run format

# Run all linters
mise run lint

# Run unit tests
mise run test:unit

# Run integration tests
mise run test:integration

# Run all tests with coverage
mise run test

# Run all checks (format, lint, type)
mise run check

# Run specific nox sessions
mise run nox -- -s test:unit
mise run nox -- -s lint:security
```

## Branch Protection

Maintainers should configure the following branch protection rules on the `main` branch:

1. Go to Settings > Branches > Add rule
2. Branch name pattern: `main`
3. Enable:
   - Require a pull request before merging
   - Require status checks to pass before merging
   - Select "test" as required status check
   - Require branches to be up to date before merging

## Release Process

To create a new release:

1. Update version in `pyproject.toml`
2. Commit the change
3. Create and push a version tag with `v` prefix:

   ```bash
   git tag v1.10.2
   git push origin v1.10.2
   ```

4. GitHub Actions will automatically:
   - Build the package
   - Publish to PyPI
   - Create a GitHub Release

**Note**: Only semantic version tags with `v` prefix (e.g., `v1.10.2`) trigger releases.

## Code Quality Requirements

- All code must pass format checks (`ruff check`)
- All code must pass linting (`nox -s lint:code`)
- Unit test coverage must be >= 80%
- All tests must pass before merging

# Reporting bugs and contributing code

- Please report bugs using the issues
- All changes to main must go through pull requests with CI checks passing

# Releases

[GitHub Releases](https://github.com/tglunde/dbt-exasol/releases)
