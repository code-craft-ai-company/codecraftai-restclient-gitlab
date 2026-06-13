"""
    Smoke tests for the GitLab REST client.

    These verify that the auto-generated client package imports cleanly (all
    API-group modules and their parameter/response modules resolve) and that the
    :meth:`RestClientBase.format_path` path-templating helper substitutes and
    URL-encodes path parameters correctly.
"""

from ccai.gitlab.rest.clients.gitlabrestclient import GitLabRestClient
from ccai.gitlab.rest.restclientbase import RestClientBase


def test_client_imports_and_subclasses_base() -> None:
    """
        The generated client must import without error and derive from
        :class:`RestClientBase`.
    """
    is_subclass = issubclass(GitLabRestClient, RestClientBase)

    assert is_subclass

    return


def test_format_path_substitutes_named_parameters() -> None:
    """
        ``format_path`` must replace each ``{name}`` placeholder with its value.
    """
    client = RestClientBase.__new__(RestClientBase)
    leaf = "/projects/{id}/repository/branches/{branch}"
    path_params = {"id": "42", "branch": "main"}

    result = client.format_path(leaf, path_params)

    assert result == "/projects/42/repository/branches/main"

    return


def test_format_path_url_encodes_reserved_characters() -> None:
    """
        A value containing a reserved character (such as ``/`` in a branch
        name) must be percent-encoded so it cannot escape its path segment.
    """
    client = RestClientBase.__new__(RestClientBase)
    leaf = "/projects/{id}/repository/branches/{branch}"
    path_params = {"id": "42", "branch": "feature/login"}

    result = client.format_path(leaf, path_params)

    assert result == "/projects/42/repository/branches/feature%2Flogin"

    return


def test_format_path_leaves_unmatched_template_unchanged() -> None:
    """
        With no path parameters the leaf must be returned unchanged.
    """
    client = RestClientBase.__new__(RestClientBase)
    leaf = "/projects/{id}/repository/branches"
    path_params = {}

    result = client.format_path(leaf, path_params)

    assert result == "/projects/{id}/repository/branches"

    return
