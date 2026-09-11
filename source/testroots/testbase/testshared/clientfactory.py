"""
    .. module:: clientfactory
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Builders for GitLab REST clients wired to a :class:`FakeSession`.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Code Craft AI LLC"
__credits__ = []


from typing import Optional

from ccai.credentials.basiccredential import BasicCredential

from ccai.gitlab.rest.aspectsrest import AspectsRest, DEFAULT_REST_ASPECTS
from ccai.gitlab.rest.clients.gitlabrestclient import GitLabRestClient

from testbase.testshared.fakesession import FakeSession


TEST_HOST = "gitlab.example"
TEST_USERNAME = "automation"
TEST_PASSWORD = "secret-token"


def make_test_credential() -> BasicCredential:
    """
        Build the basic credential the test clients authenticate with.

        :returns: A :class:`BasicCredential` with known username and password.
    """

    credential = BasicCredential(identifier="gitlab-test", categories=["basic"],
                                 username=TEST_USERNAME, password=TEST_PASSWORD)

    return credential


def make_gitlab_client(session: Optional[FakeSession] = None, *, host: str = TEST_HOST,
                       port: Optional[int] = None, scheme: str = "https",
                       aspects: AspectsRest = DEFAULT_REST_ASPECTS) -> GitLabRestClient:
    """
        Build a :class:`GitLabRestClient` whose session is already established,
        so no authentication round trip happens and every call goes to
        ``session``.

        :param session: The fake session to install; when ``None`` the client is
                        left unauthenticated.
        :param host: The host name for the client.
        :param port: Optional port for the client.
        :param scheme: URL scheme for the client.
        :param aspects: Default aspects for the client.

        :returns: The configured client.
    """

    credential = make_test_credential()

    client = GitLabRestClient(host, credential, port=port, scheme=scheme, aspects=aspects)

    if session is not None:
        client._session = session

    return client
