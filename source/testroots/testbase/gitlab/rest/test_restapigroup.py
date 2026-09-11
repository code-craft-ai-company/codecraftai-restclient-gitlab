"""
    Tests for :class:`ccai.gitlab.rest.restapigroup.RestApiGroup`, the base of
    every generated endpoint group.
"""

import gc

from ccai.gitlab.rest.restapigroup import RestApiGroup

from testbase.testshared.clientfactory import make_gitlab_client


def test_restapigroup_client_property_returns_owning_client() -> None:
    """
        The ``client`` property dereferences to the client the group was
        constructed with.
    """
    client = make_gitlab_client(None)

    group = RestApiGroup(client)

    assert group.client is client

    return


def test_restapigroup_holds_client_weakly() -> None:
    """
        The group does not keep its client alive: once the client is gone the
        ``client`` property yields ``None``.
    """
    client = make_gitlab_client(None)
    group = RestApiGroup(client)

    del client
    gc.collect()

    assert group.client is None

    return
