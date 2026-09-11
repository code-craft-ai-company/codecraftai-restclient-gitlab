"""
    Tests for :class:`ccai.gitlab.rest.clients.gitlabrestclient.GitLabRestClient`:
    the generated client exposes every endpoint group bound to itself.
"""

from ccai.gitlab.rest.restapigroup import RestApiGroup

from ccai.gitlab.rest.clients.groups.badges import BadgesApiGroup
from ccai.gitlab.rest.clients.groups.branches import BranchesApiGroup
from ccai.gitlab.rest.clients.groups.broadcastmessages import BroadcastMessagesApiGroup
from ccai.gitlab.rest.clients.groups.jobs import JobsApiGroup

from testbase.testshared.clientfactory import make_gitlab_client, TEST_HOST, TEST_USERNAME


EXPECTED_GROUPS = {
    "access_requests", "admin", "alert_management", "application", "applications", "avatar",
    "badges", "batched_background_migrations", "branches", "broadcast_messages", "bulk_imports",
    "clusters", "jobs", "metadata", "migrations", "pipeline_composition", "plan_limits",
}


def test_client_exposes_every_generated_group_as_restapigroup() -> None:
    """
        Every group property on the client returns a :class:`RestApiGroup`.
    """
    client = make_gitlab_client(None)

    missing = [name for name in EXPECTED_GROUPS if not isinstance(getattr(client, name), RestApiGroup)]

    assert missing == []

    return


def test_client_groups_are_bound_to_the_client() -> None:
    """
        Each group's ``client`` back-reference is the client that owns it.
    """
    client = make_gitlab_client(None)

    unbound = [name for name in EXPECTED_GROUPS if getattr(client, name).client is not client]

    assert unbound == []

    return


def test_client_group_properties_return_typed_groups() -> None:
    """
        The group properties exercised by the wire tests return their
        generated types.
    """
    client = make_gitlab_client(None)

    assert isinstance(client.badges, BadgesApiGroup)
    assert isinstance(client.branches, BranchesApiGroup)
    assert isinstance(client.broadcast_messages, BroadcastMessagesApiGroup)
    assert isinstance(client.jobs, JobsApiGroup)

    return


def test_client_exposes_host_and_credential() -> None:
    """
        The host and credential passed at construction are readable back.
    """
    client = make_gitlab_client(None)

    assert client.host == TEST_HOST
    assert client.credential.username == TEST_USERNAME

    return
