"""
    Wire tests for :class:`ccai.gitlab.rest.clients.groups.branches.BranchesApiGroup`
    over a :class:`FakeSession`.
"""

from ccai.gitlab.rest.clients.parameters import branches as parameters

from testbase.testshared.clientfactory import make_gitlab_client
from testbase.testshared.fakesession import FakeSession, assert_call_path


def test_branches_list_hits_get_projects_id_repository_branches() -> None:
    """
        ``getapiv4projectsidrepositorybranches(id)`` hits
        ``GET /projects/{id}/repository/branches`` and returns the JSON list.
    """
    branches = [{"name": "main"}, {"name": "develop"}]
    session = FakeSession([(200, branches, None)])
    client = make_gitlab_client(session)

    params = parameters.BranchesGetapiv4projectsidrepositorybranchesParams(id="group/project")
    result = client.branches.getapiv4projectsidrepositorybranches(params)

    assert_call_path(session.last_call, "GET", "/projects/{id}/repository/branches", id="group/project")
    assert result.ok is True
    assert result.data == branches

    return


def test_branches_get_encodes_slash_in_branch_name() -> None:
    """
        ``getapiv4projectsidrepositorybranchesbranch(id, branch)`` keeps a
        branch name containing ``/`` inside one path segment.
    """
    session = FakeSession([(200, {"name": "feature/login"}, None)])
    client = make_gitlab_client(session)

    params = parameters.BranchesGetapiv4projectsidrepositorybranchesbranchParams(id="42", branch="feature/login")
    result = client.branches.getapiv4projectsidrepositorybranchesbranch(params)

    assert_call_path(session.last_call, "GET", "/projects/{id}/repository/branches/{branch}",
                     id="42", branch="feature/login")
    assert session.last_call.path == "/projects/42/repository/branches/feature%2Flogin"
    assert result.data["name"] == "feature/login"

    return


def test_branches_create_posts_branch_and_ref_as_query() -> None:
    """
        ``postapiv4projectsidrepositorybranches(id, branch, ref)`` hits
        ``POST /projects/{id}/repository/branches`` carrying ``branch`` and
        ``ref`` as query parameters and accepts a 201.
    """
    session = FakeSession([(201, {"name": "release/1.0"}, None)])
    client = make_gitlab_client(session)

    params = parameters.BranchesPostapiv4projectsidrepositorybranchesParams(id="42", branch="release/1.0", ref="main")
    result = client.branches.postapiv4projectsidrepositorybranches(params)

    assert_call_path(session.last_call, "POST", "/projects/{id}/repository/branches", id="42")
    assert session.last_call.params == {"branch": "release/1.0", "ref": "main"}
    assert result.status_code == 201

    return


def test_branches_delete_accepts_no_content() -> None:
    """
        ``deleteapiv4projectsidrepositorybranchesbranch(id, branch)`` hits
        ``DELETE /projects/{id}/repository/branches/{branch}`` and accepts 204.
    """
    session = FakeSession([(204, None, None)])
    client = make_gitlab_client(session)

    params = parameters.BranchesDeleteapiv4projectsidrepositorybranchesbranchParams(id="42", branch="stale")
    result = client.branches.deleteapiv4projectsidrepositorybranchesbranch(params)

    assert_call_path(session.last_call, "DELETE", "/projects/{id}/repository/branches/{branch}",
                     id="42", branch="stale")
    assert result.ok is True

    return
