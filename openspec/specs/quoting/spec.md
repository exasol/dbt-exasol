# quoting Specification

## Purpose

Defines identifier quoting behavior in dbt-exasol. Covers how the adapter respects `quoting` configuration from sources, models, and `dbt_project.yml`, and how `ExasolRelation` renders quoted or unquoted schema and identifier components.
## Requirements
### Requirement: Respect Source and Model Quoting Configuration
The adapter MUST respect `quoting` configurations defined in sources and models.
If `quoting` is set to `true` for `database`, `schema`, or `identifier`, the generated SQL MUST use double quotes for those components.

#### Scenario: Source Quoting Enabled
- **WHEN** a source is defined with `quoting: {schema: true, identifier: true}`
- **AND** the source schema is `TEST` and table is `order`
- **THEN** the generated SQL selects from `"TEST"."order"` (quoted) instead of `TEST.order` (unquoted).

#### Scenario: Table Quoting Overwrite
- **WHEN** a table config overwrites quoting (e.g., `quoting: {identifier: true}`)
- **THEN** the identifier MUST be quoted in the generated SQL.

#### Scenario: Partial Quoting Override
- **WHEN** a source defines `quoting: {schema: true, identifier: true}`
- **AND** a table within that source overrides with `quoting: {identifier: false}`
- **THEN** the schema MUST remain quoted (inherited)
- **AND** the identifier MUST NOT be quoted (overridden).

#### Scenario: Quoting Disabled
- **WHEN** quoting is disabled or not configured for schema and identifier
- **THEN** the generated SQL MUST NOT contain quotes around schema and identifier.

### Requirement: Unit Test Coverage for Quoting Behavior
Unit tests MUST verify quoting behavior without requiring external database connections.

#### Scenario: Quote Policy as Dictionary
- **WHEN** `ExasolRelation.create()` is called with `quote_policy` as a dict
- **THEN** the relation MUST correctly apply the quoting configuration.

#### Scenario: Quote Policy as ExasolQuotePolicy Object
- **WHEN** `ExasolRelation.create()` is called with `quote_policy` as an `ExasolQuotePolicy` instance
- **THEN** the relation MUST correctly apply the quoting configuration.

#### Scenario: Render with All Components Quoted
- **WHEN** a relation is created with `quote_policy: {database: true, schema: true, identifier: true}`
- **THEN** `str(relation)` MUST include double quotes around schema and identifier.

#### Scenario: Render with Quoting Disabled
- **WHEN** a relation is created with `quote_policy: {schema: false, identifier: false}`
- **THEN** `str(relation)` MUST NOT include double quotes around schema and identifier.

#### Scenario: Reserved Keywords as Identifiers
- **WHEN** an identifier is a SQL reserved keyword (e.g., `order`, `select`, `from`)
- **AND** quoting is enabled for identifier
- **THEN** the identifier MUST be rendered with double quotes.

### Requirement: DDL and Ref Render Consistency
The adapter SHALL render the same relation identifier consistently across DDL statements (`CREATE TABLE`, `CREATE VIEW`, `DROP`, `TRUNCATE`, `RENAME`) and query references (`ref()`, `source()`). If a `quote_policy` results in a quoted identifier in a `SELECT` from `ref()`, the DDL that materializes that same model MUST also quote the identifier so both resolve to the same physical object.

#### Scenario: DDL and ref agree under default quote policy
- **WHEN** the project has no `quoting:` configuration (default `ExasolQuotePolicy` with all fields `False`)
- **AND** a model named `stg_orders` is materialized as a table
- **THEN** the `CREATE TABLE` DDL SHALL render `stg_orders` unquoted
- **AND** `ref('stg_orders')` SHALL also render `stg_orders` unquoted
- **AND** both resolve to the same Exasol physical object.

#### Scenario: DDL and ref agree under project quoting config
- **WHEN** `dbt_project.yml` sets `quoting: {identifier: true}`
- **AND** a model named `stg_orders` is materialized as a table
- **THEN** the `CREATE TABLE` DDL SHALL render the identifier as `"stg_orders"` quoted
- **AND** `ref('stg_orders')` SHALL render the identifier identically
- **AND** both resolve to the same case-sensitive physical object `stg_orders`.

#### Scenario: TRUNCATE respects quoting config
- **WHEN** `dbt_project.yml` sets `quoting: {identifier: true}`
- **AND** a seed or table relation is truncated
- **THEN** the `TRUNCATE TABLE` DDL SHALL render the identifier quoted
- **AND** this SHALL match the same physical object as `CREATE TABLE` and `ref()`.

### Requirement: Source Quoting Is Configured Per Source
Source quoting SHALL be configured on the source (or source table), not through the project-level `quoting:` block. dbt-core deliberately ignores project-level `quoting:` when resolving sources, so the adapter MUST honor the source-level configuration and MUST NOT require the undocumented workaround of embedding literal quote characters in `identifier:`.

#### Scenario: Source-level quoting renders a case-sensitive identifier
- **GIVEN** an object created outside dbt as lowercase-and-quoted, e.g. `"orders"`
- **WHEN** a source YAML sets `quoting: {identifier: true}` on the source
- **AND** the source table is declared as `- name: orders`
- **THEN** `source()` SHALL render `"orders"` quoted
- **AND** a model selecting from that source SHALL resolve the object successfully.

#### Scenario: Project-level quoting does not apply to sources
- **WHEN** `dbt_project.yml` sets `quoting: {identifier: true}`
- **AND** a source declares no `quoting:` of its own
- **THEN** `source()` SHALL render the identifier unquoted
- **AND** this SHALL match dbt-core's documented behavior rather than being treated as an adapter defect.

### Requirement: Quoting Applies Across Every Materialization Path
A project that enables `quoting: {identifier: true}` SHALL work end-to-end for every supported materialization and command, not only for the initial `CREATE`. Seeds, incremental models, full refreshes, snapshots, and enforced contracts MUST all target the same physical object that the initial DDL created.

#### Scenario: Seed IMPORT targets the created object
- **WHEN** `quoting: {identifier: true}` is set
- **AND** a seed named `my_seed` is loaded
- **THEN** the `IMPORT INTO` target SHALL resolve to the object created by the seed's `CREATE TABLE`
- **AND** the load SHALL NOT fail with a pyexasol "not a safe identifier" error.

#### Scenario: Relation lookup succeeds on a second run
- **WHEN** `quoting: {identifier: true}` is set
- **AND** `dbt run` is executed a second time against existing relations
- **THEN** each existing relation SHALL be found in the cache
- **AND** no `ApproximateMatchError` SHALL be raised.

#### Scenario: Full refresh renames the correct object
- **WHEN** `quoting: {identifier: true}` is set
- **AND** an incremental model whose name is ALL_CAPS is run with `--full-refresh`
- **THEN** the intermediate-to-target `RENAME` SHALL name the object using its stored case
- **AND** the run SHALL succeed.

#### Scenario: Repeated snapshot merges into the existing snapshot table
- **WHEN** `quoting: {identifier: true}` is set
- **AND** `dbt snapshot` is executed a second time
- **THEN** the snapshot SQL SHALL NOT upper-case a rendered (quoted) relation
- **AND** the merge SHALL resolve the existing snapshot table.

#### Scenario: Contract primary-key constraint name is a valid identifier
- **WHEN** `quoting: {identifier: true}` is set
- **AND** a model with an enforced contract declares a `primary_key` constraint
- **THEN** the generated constraint name SHALL NOT embed double-quote characters
- **AND** the `ALTER TABLE ... ADD CONSTRAINT` statement SHALL be accepted by Exasol.

### Requirement: Non-Breaking Default Behavior
Routing DDL through `render()` SHALL NOT change the physical objects that existing projects resolve to when no `quoting:` block is configured. Under the default `ExasolQuotePolicy` (all fields `False`), `{{ relation }}` and `{{ relation.schema }}.{{ relation.identifier }}` MUST produce equivalent output.

#### Scenario: Default policy produces unchanged DDL
- **WHEN** no project-level `quoting:` config exists
- **AND** a full project lifecycle is executed (seed, run, re-run, full refresh, snapshot)
- **THEN** the materialized statements SHALL be identical to those produced before this change, except for identifier case in unquoted positions, which Exasol folds identically
- **AND** no existing project SHALL require a `--full-refresh` as a result of this change.

### Requirement: Case-Insensitive Relation Matching For Unquoted Relations
The adapter SHALL match unquoted relations from the system catalog case-insensitively, and quoted relations exactly. The catalog query returns identifiers as stored; relations built from it MUST be marked as dbt-created so that unquoted matching remains case-insensitive.

#### Scenario: Unquoted relation lookup ignores case
- **WHEN** `get_relation()` is called with identifier `stg_orders`
- **AND** the system catalog stores the object as `STG_ORDERS`
- **AND** `quote_policy.identifier` is `False`
- **THEN** the match SHALL succeed.

#### Scenario: Quoted relation lookup respects case
- **WHEN** `quote_policy.identifier` is `True`
- **AND** the system catalog stores the object as `stg_orders`
- **THEN** the match SHALL succeed for `stg_orders`
- **AND** the relation rendered for DDL SHALL use that stored case.

