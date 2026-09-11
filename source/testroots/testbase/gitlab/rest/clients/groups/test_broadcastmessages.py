"""
    Wire tests for
    :class:`ccai.gitlab.rest.clients.groups.broadcastmessages.BroadcastMessagesApiGroup`
    over a :class:`FakeSession`.  This group has instance-wide endpoints with
    no path parameters, so the leaf must pass through untouched.
"""

from ccai.gitlab.rest.clients.parameters import broadcastmessages as parameters

from testbase.testshared.clientfactory import make_gitlab_client
from testbase.testshared.fakesession import FakeSession, assert_call_path


def test_broadcast_messages_list_hits_get_broadcast_messages() -> None:
    """
        ``getapiv4broadcastmessages()`` with default parameters hits
        ``GET /broadcast_messages`` with no path substitution.
    """
    messages = [{"id": 1, "message": "Maintenance at 22:00"}]
    session = FakeSession([(200, messages, None)])
    client = make_gitlab_client(session)

    result = client.broadcast_messages.getapiv4broadcastmessages()

    assert_call_path(session.last_call, "GET", "/broadcast_messages")
    assert result.data == messages

    return


def test_broadcast_messages_get_hits_get_broadcast_messages_id() -> None:
    """
        ``getapiv4broadcastmessagesid(id)`` hits ``GET /broadcast_messages/{id}``.
    """
    session = FakeSession([(200, {"id": 12, "message": "hello"}, None)])
    client = make_gitlab_client(session)

    params = parameters.BroadcastMessagesGetapiv4broadcastmessagesidParams(id=12)
    result = client.broadcast_messages.getapiv4broadcastmessagesid(params)

    assert_call_path(session.last_call, "GET", "/broadcast_messages/{id}", id=12)
    assert result.data["message"] == "hello"

    return


def test_broadcast_messages_create_posts_body_and_accepts_created() -> None:
    """
        ``postapiv4broadcastmessages(body)`` hits ``POST /broadcast_messages``
        with the body as form fields and accepts a 201.
    """
    body = {"message": "Deploy window", "color": "#ff0000"}
    session = FakeSession([(201, {"id": 13, "message": "Deploy window"}, None)])
    client = make_gitlab_client(session)

    params = parameters.BroadcastMessagesPostapiv4broadcastmessagesParams(body=body)
    result = client.broadcast_messages.postapiv4broadcastmessages(params)

    assert_call_path(session.last_call, "POST", "/broadcast_messages")
    assert session.last_call.form == body
    assert result.status_code == 201

    return
