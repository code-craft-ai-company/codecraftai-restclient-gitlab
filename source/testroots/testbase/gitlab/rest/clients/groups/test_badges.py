"""
    Wire tests for :class:`ccai.gitlab.rest.clients.groups.badges.BadgesApiGroup`
    over a :class:`FakeSession`: each generated method hits the path from its
    template with the right method, query and body, and wraps the response.
"""

from ccai.errors.exceptions import HttpNotFoundError

from ccai.gitlab.rest.clients.parameters import badges as parameters

from testbase.testshared.clientfactory import make_gitlab_client
from testbase.testshared.fakesession import FakeSession, assert_call_path


def test_badges_list_group_badges_hits_get_groups_id_badges_with_query() -> None:
    """
        ``getapiv4groupsidbadges(id, page, per_page, name)`` hits
        ``GET /groups/{id}/badges`` with the query parameters and exposes the
        JSON list as ``data``.
    """
    badges = [{"id": 1, "name": "coverage"}, {"id": 2, "name": "pipeline"}]
    session = FakeSession([(200, badges, None)])
    client = make_gitlab_client(session)

    params = parameters.BadgesGetapiv4groupsidbadgesParams(id="my-org/tools", page=2, per_page=50, name="cov")
    result = client.badges.getapiv4groupsidbadges(params)

    assert_call_path(session.last_call, "GET", "/groups/{id}/badges", id="my-org/tools")
    assert session.last_call.params == {"page": "2", "per_page": "50", "name": "cov"}
    assert result.ok is True
    assert result.data == badges

    return


def test_badges_get_project_badge_hits_get_projects_id_badges_badge_id() -> None:
    """
        ``getapiv4projectsidbadgesbadgeid(id, badge_id)`` hits
        ``GET /projects/{id}/badges/{badge_id}`` with both path values encoded.
    """
    session = FakeSession([(200, {"id": 9, "kind": "project"}, None)])
    client = make_gitlab_client(session)

    params = parameters.BadgesGetapiv4projectsidbadgesbadgeidParams(id="42", badge_id=9)
    result = client.badges.getapiv4projectsidbadgesbadgeid(params)

    assert_call_path(session.last_call, "GET", "/projects/{id}/badges/{badge_id}", id="42", badge_id=9)
    assert session.last_call.params == {}
    assert result.status_code == 200
    assert result.data["kind"] == "project"

    return


def test_badges_add_project_badge_posts_body_fields() -> None:
    """
        ``postapiv4projectsidbadges(id, body)`` hits ``POST /projects/{id}/badges``
        sending the body fields as form data and accepts a 201.
    """
    body = {"link_url": "https://ci.example/%{project_path}", "image_url": "https://ci.example/badge.svg", "name": "ci"}
    session = FakeSession([(201, {"id": 3, "name": "ci"}, None)])
    client = make_gitlab_client(session)

    params = parameters.BadgesPostapiv4projectsidbadgesParams(id="42", body=body)
    result = client.badges.postapiv4projectsidbadges(params)

    assert_call_path(session.last_call, "POST", "/projects/{id}/badges", id="42")
    assert session.last_call.form == body
    assert result.ok is True
    assert result.data["id"] == 3

    return


def test_badges_delete_group_badge_accepts_no_content() -> None:
    """
        ``deleteapiv4groupsidbadgesbadgeid(id, badge_id)`` hits
        ``DELETE /groups/{id}/badges/{badge_id}`` and treats the empty 204
        body as raw content.
    """
    session = FakeSession([(204, None, None)])
    client = make_gitlab_client(session)

    params = parameters.BadgesDeleteapiv4groupsidbadgesbadgeidParams(id="my-org", badge_id=5)
    result = client.badges.deleteapiv4groupsidbadgesbadgeid(params)

    assert_call_path(session.last_call, "DELETE", "/groups/{id}/badges/{badge_id}", id="my-org", badge_id=5)
    assert result.ok is True
    assert result.status_code == 204
    assert result.data == b""

    return


def test_badges_get_missing_badge_raises_not_found() -> None:
    """
        A 404 from the server surfaces as :class:`HttpNotFoundError` from the
        group method.
    """
    session = FakeSession([(404, {"message": "404 Badge Not Found"}, None)])
    client = make_gitlab_client(session)

    params = parameters.BadgesGetapiv4groupsidbadgesbadgeidParams(id="my-org", badge_id=77)

    raised = None
    try:
        client.badges.getapiv4groupsidbadgesbadgeid(params)
    except HttpNotFoundError as err:
        raised = err

    assert raised is not None
    assert_call_path(session.last_call, "GET", "/groups/{id}/badges/{badge_id}", id="my-org", badge_id=77)

    return
