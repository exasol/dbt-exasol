"""Upstream `dbt clone` parity tests.

Exasol has no native zero-copy clone, so `can_clone_table` returns the base default
(`False`) and clones are materialised as views. These subclasses exercise the
upstream 1.11 clone contract (see the README parity matrix entry for `dbt clone`,
marked ⚠️ Conditional).

One of the three upstream classes assumes capabilities Exasol does not have and is
skipped with a documented reason rather than contorted into a spurious pass:

* ``BaseCloneSameSourceAndTarget`` asserts the zero-copy "skipping clone for
  relation" log line, which dbt-core only emits on the ``can_clone_table == True``
  path. Exasol uses clone-as-view (``can_clone_table == False``), so that branch is
  never taken and the assertion does not apply.

``BaseCloneNotPossible`` (clone into a second target via ``--target otherschema``)
now passes: the connection manager lazily acquires a pooled connection for threads
that have no bound connection, so the post-clone ``list_relations`` call on an
unbound thread no longer raises ``InvalidConnectionError``.

``BaseCloneSameTargetAndState`` (state/target collision warning) is platform-neutral
and runs unchanged.
"""

import pytest
from dbt.tests.adapter.dbt_clone.test_dbt_clone import (
    BaseCloneNotPossible,
    BaseCloneSameSourceAndTarget,
    BaseCloneSameTargetAndState,
)


class TestExasolCloneNotPossible(BaseCloneNotPossible):
    """Clone into a second target (--target otherschema) using clone-as-view.

    The connection manager lazily acquires a pooled connection for unbound
    threads, so the post-clone list_relations call succeeds without raising
    InvalidConnectionError.
    """


@pytest.mark.skip(
    reason="Upstream asserts the zero-copy 'skipping clone for relation' log line, "
    "emitted only when can_clone_table is True. Exasol clones as views "
    "(can_clone_table False), so that branch is never taken."
)
class TestExasolCloneSameSourceAndTarget(BaseCloneSameSourceAndTarget):
    pass


class TestExasolCloneSameTargetAndState(BaseCloneSameTargetAndState):
    pass
