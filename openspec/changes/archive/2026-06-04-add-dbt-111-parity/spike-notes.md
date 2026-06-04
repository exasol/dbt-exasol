# Spike notes: microbatch concurrency on Exasol

## Question

dbt-core's microbatch strategy materialises each batch as `DELETE` (of the batch
window) + `INSERT` against the same target relation. Declaring
`Capability.MicrobatchConcurrency: Support.Full` makes dbt-core run those batches
concurrently across threads. Is that safe on Exasol?

## Method

`scripts/spikes/microbatch_concurrency.py` opens two `pyexasol` connections with
`autocommit=False`, seeds a shared target table with two disjoint day windows,
then — synchronised on a `threading.Barrier` — has each connection run a
`DELETE … WHERE event_day = N` + `INSERT` for its own (disjoint) window and hold
the transaction open briefly before `COMMIT`.

Run with a live instance:

```bash
EXASOL_DSN=host:8563 EXASOL_USER=sys EXASOL_PASSWORD=exasol \
    uv run python scripts/spikes/microbatch_concurrency.py
```

## Observed outcome

Exasol uses **optimistic, table-granularity transaction-conflict detection**. Two
concurrent write transactions touching the same target table — even on disjoint
row sets — are detected as a write-write conflict: one transaction commits and the
other aborts with `transaction conflict for transaction <id>` (WAIT/ABORT
semantics). This matches Exasol's documented MVCC model, where conflict detection
is at object (table) level, not row level.

This is materially different from Snowflake, whose microbatch DELETE+INSERT runs
as a single auto-committed statement under snapshot isolation, so concurrent
batches against the same table do not abort each other.

## Decision

Per design decision **D3**, keep `Capability.MicrobatchConcurrency:
CapabilitySupport(support=Support.Unsupported)`. Microbatch batches therefore run
**sequentially** on Exasol regardless of the project's thread count, which is
dbt-core's built-in behaviour for adapters that do not declare concurrency
support. An inline comment in `dbt/adapters/exasol/impl.py` records the
transaction-conflict rationale so future contributors read the "why" before
attempting to enable it.

No scope change required (the no-conflict branch — which would have required
escalation to the user — was not reached).
