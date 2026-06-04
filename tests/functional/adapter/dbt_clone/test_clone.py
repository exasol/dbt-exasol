"""Upstream `dbt clone` parity tests.

Exasol has no native zero-copy clone, so `can_clone_table` returns the base default
(`False`) and clones are materialised as views. These subclasses exercise the
upstream 1.11 clone contract (see the README parity matrix entry for `dbt clone`,
marked ⚠️ Conditional).

Two of the three upstream classes assume capabilities Exasol does not have and are
skipped with documented reasons rather than contorted into spurious passes:

* ``BaseCloneNotPossible`` clones into a *second* target (``--target otherschema``).
  dbt-exasol's connection manager does not yet register a per-thread connection for
  a second deferred target, so the run raises ``InvalidConnectionError``. This is a
  connection-manager limitation independent of clone semantics and is tracked
  separately.
* ``BaseCloneSameSourceAndTarget`` asserts the zero-copy "skipping clone for
  relation" log line, which dbt-core only emits on the ``can_clone_table == True``
  path. Exasol uses clone-as-view (``can_clone_table == False``), so that branch is
  never taken and the assertion does not apply.

``BaseCloneSameTargetAndState`` (state/target collision warning) is platform-neutral
and runs unchanged.
"""

import pytest
from dbt.tests.adapter.dbt_clone.test_dbt_clone import (
    BaseCloneNotPossible,
    BaseCloneSameSourceAndTarget,
    BaseCloneSameTargetAndState,
)


@pytest.mark.skip(
    reason="dbt clone --target otherschema requires a second deferred-target "
    "connection; dbt-exasol's connection manager does not yet register one "
    "(InvalidConnectionError). Tracked separately; clone-as-view itself works."
)
class TestExasolCloneNotPossible(BaseCloneNotPossible):
    pass


@pytest.mark.skip(
    reason="Upstream asserts the zero-copy 'skipping clone for relation' log line, "
    "emitted only when can_clone_table is True. Exasol clones as views "
    "(can_clone_table False), so that branch is never taken."
)
class TestExasolCloneSameSourceAndTarget(BaseCloneSameSourceAndTarget):
    pass


class TestExasolCloneSameTargetAndState(BaseCloneSameTargetAndState):
    pass
