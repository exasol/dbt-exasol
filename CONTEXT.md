# dbt-exasol Build & CI/CD Context

The development, automated testing, and release pipeline infrastructure for the dbt-exasol adapter.

## Language

**Build Matrix**:
A multi-dimensional set of runtime environment combinations (such as Python versions and Exasol database versions) executed by CI/CD to validate adapter compatibility.
_Avoid_: Test grid, environment list

**Matrix Dimension**:
A discrete configuration axis (such as Python version or Exasol version) declared on the project configuration model and consumed by matrix generators.
_Avoid_: Matrix variable, matrix parameter

**Toolbox Hybrid Architecture**:
The integration approach combining uv and mise for fast local package execution with exasol-toolbox for standardized Nox tasks and matrix generation.
_Avoid_: Poetry workflow, vanilla toolbox setup

**Fast Matrix**:
A reduced, single-combination execution strategy running on pull requests to provide rapid developer feedback while conserving CI runner resources.
_Avoid_: PR matrix, light build

**Full Matrix**:
The complete Cartesian product of all supported Python and Exasol versions executed on nightly schedules and main branch pushes for exhaustive compatibility verification.
_Avoid_: Nightly matrix, release matrix

**Workflow Security Audit**:
Automated static analysis of GitHub Actions workflows and composite actions using zizmor to detect security vulnerabilities, secret leakage, and unpinned action risks.
_Avoid_: YAML lint, action validator
