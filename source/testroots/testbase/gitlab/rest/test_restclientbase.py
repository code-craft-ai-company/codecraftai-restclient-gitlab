"""
    Wire-level tests for :class:`ccai.gitlab.rest.restclientbase.RestClientBase`:
    ``perform_call`` under each action pattern, session acquisition,
    authentication and path formatting.  Every call goes to a
    :class:`FakeSession`; nothing touches the network.
"""

from typing import List

import logging

from base64 import b64encode
from urllib.parse import quote, unquote

from unittest.mock import patch

from requests.exceptions import ConnectionError as RequestsConnectionError

from ccai.errors.exceptions import HttpForbiddenError, HttpNotFoundError, HttpInternalServerError

from ccai.testbase.properties import run_property
from ccai.testbase.properties import strategies as st

import ccai.gitlab.rest.restclientbase as restclientbase_module

from ccai.gitlab.rest.aspectsrest import ActionPattern, AspectsRest
from ccai.gitlab.rest.restclientbase import RestClientBase

from testbase.testshared.clientfactory import make_gitlab_client, TEST_HOST, TEST_PASSWORD, TEST_USERNAME
from testbase.testshared.fakesession import FakeSession


class _RecordingHandler(logging.Handler):
    """
        A logging handler that keeps the records it receives so a test can
        check what the client logged.
    """

    def __init__(self) -> None:
        super().__init__(level=logging.DEBUG)
        self.records: List[logging.LogRecord] = []
        return

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)
        return


def _fast_aspects(action_pattern: ActionPattern, **overrides) -> AspectsRest:
    """
        Aspects that never sleep and give up immediately on timeout unless a
        test overrides the timeout, so a scripted failure cannot stall the run.
    """

    settings = dict(action_pattern=action_pattern, completion_timeout=0, completion_interval=0)
    settings.update(overrides)

    aspects = AspectsRest(**settings)

    return aspects


# ---------------------------------------------------------------------------
# ActionPattern.SINGLE_CALL
# ---------------------------------------------------------------------------

def test_perform_call_single_call_returns_response_for_expected_status() -> None:
    """
        A single call whose status is expected returns the session's response
        untouched, with the JSON body available to the caller.
    """
    session = FakeSession([(200, {"id": 7, "name": "ci"}, None)])
    client = make_gitlab_client(session)

    resp = client.perform_call(leaf="/projects/7", method="GET", params=None, body=None,
                               exp_status=200, aspects=None)

    assert resp.status_code == 200
    assert resp.json() == {"id": 7, "name": "ci"}
    assert session.call_count == 1

    return


def test_perform_call_single_call_sends_method_url_params_headers_and_body() -> None:
    """
        The call is prepared with the method, host URL plus leaf, query
        parameters, headers and form body handed to ``perform_call``.
    """
    session = FakeSession([(201, {"id": 1}, None)])
    client = make_gitlab_client(session, port=8443)

    client.perform_call(leaf="/projects/7/badges", method="POST", params={"page": "2"},
                        body={"link_url": "https://ci.example/%{project_path}", "image_url": "https://ci.example/badge.svg"},
                        exp_status=[201], headers={"PRIVATE-TOKEN": "abc"}, aspects=None)

    call = session.last_call

    assert call.method == "POST"
    assert call.url.startswith(f"https://{TEST_HOST}:8443/projects/7/badges?")
    assert call.params == {"page": "2"}
    assert call.headers["PRIVATE-TOKEN"] == "abc"
    assert call.form == {"link_url": "https://ci.example/%{project_path}", "image_url": "https://ci.example/badge.svg"}
    assert call.verify is False

    return


def test_perform_call_single_call_passes_connection_and_inactivity_timeouts() -> None:
    """
        The aspects' connection and inactivity timeouts are handed to the
        session as the ``timeout`` pair.
    """
    session = FakeSession([(200, None, None)])
    aspects = AspectsRest(connection_timeout=3, inactivity_timeout=9)
    client = make_gitlab_client(session)

    client.perform_call(leaf="/version", method="GET", params=None, body=None,
                        exp_status=200, aspects=aspects)

    assert session.last_call.timeout == (3, 9)

    return


def test_perform_call_single_call_unexpected_status_raises_mapped_http_error() -> None:
    """
        A status outside ``exp_status`` raises the exception mapped to that
        status (a 404 raises :class:`HttpNotFoundError`), not a logging error,
        even though the default aspects carry no logger.
    """
    session = FakeSession([(404, {"message": "404 Project Not Found"}, None)])
    client = make_gitlab_client(session)

    raised = None
    try:
        client.perform_call(leaf="/projects/999", method="GET", params=None, body=None,
                            exp_status=200, aspects=None)
    except HttpNotFoundError as err:
        raised = err

    assert raised is not None
    assert "/projects/999" in str(raised)

    return


def test_perform_call_single_call_logs_error_to_aspects_logger() -> None:
    """
        When the aspects carry a logger, the unexpected-status message is
        logged through it before the HTTP error is raised.
    """
    handler = _RecordingHandler()
    logger = logging.getLogger("testbase.gitlab.test_restclientbase.aspects_logger")
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    session = FakeSession([(500, {"message": "boom"}, None)])
    client = make_gitlab_client(session)
    aspects = AspectsRest(logger=logger)

    try:
        try:
            client.perform_call(leaf="/projects/1", method="GET", params=None, body=None,
                                exp_status=200, aspects=aspects)
        except HttpInternalServerError:
            # The 500 error is the expected outcome of the call; this test only
            # verifies what was logged to the aspects logger before it was raised.
            pass
    finally:
        logger.removeHandler(handler)

    error_records = [rec for rec in handler.records if rec.levelno == logging.ERROR]

    assert len(error_records) == 1
    assert "/projects/1" in error_records[0].getMessage()

    return


def test_perform_call_single_call_reauthenticates_once_after_forbidden() -> None:
    """
        An authentication failure on the first attempt drops the session,
        authenticates once more and repeats the call on the new session.
    """
    first_session = FakeSession([HttpForbiddenError("token expired")])
    second_session = FakeSession([(200, {"ok": True}, None)])
    client = make_gitlab_client(first_session)

    def install_second_session() -> None:
        client._session = second_session
        return

    with patch.object(client, "authenticate", side_effect=install_second_session) as authenticate:
        resp = client.perform_call(leaf="/user", method="GET", params=None, body=None,
                                   exp_status=200, aspects=None)

    assert resp.json() == {"ok": True}
    assert authenticate.call_count == 1
    assert first_session.call_count == 1
    assert second_session.call_count == 1

    return


def test_perform_call_single_call_second_forbidden_bubbles() -> None:
    """
        Only one re-authentication is attempted; a second authentication
        failure is raised to the caller.
    """
    first_session = FakeSession([HttpForbiddenError("first")])
    second_session = FakeSession([HttpForbiddenError("second")])
    client = make_gitlab_client(first_session)

    def install_second_session() -> None:
        client._session = second_session
        return

    raised = None
    with patch.object(client, "authenticate", side_effect=install_second_session) as authenticate:
        try:
            client.perform_call(leaf="/user", method="GET", params=None, body=None,
                                exp_status=200, aspects=None)
        except HttpForbiddenError as err:
            raised = err

    assert raised is not None
    assert str(raised) == "second"
    assert authenticate.call_count == 1

    return


def test_perform_call_uses_client_default_aspects_when_none_given() -> None:
    """
        ``aspects=None`` falls back to the aspects the client was constructed
        with; those aspects' session takes precedence over the client's own.
    """
    aspects_session = FakeSession([(200, {"from": "aspects"}, None)])
    client_session = FakeSession([(200, {"from": "client"}, None)])
    client = make_gitlab_client(client_session, aspects=AspectsRest(session=aspects_session))

    resp = client.perform_call(leaf="/version", method="GET", params=None, body=None,
                               exp_status=200, aspects=None)

    assert resp.json() == {"from": "aspects"}
    assert aspects_session.call_count == 1
    assert client_session.call_count == 0

    return


def test_perform_call_unsupported_action_pattern_raises_runtime_error() -> None:
    """
        An action pattern the client does not implement is reported as a
        :class:`RuntimeError` naming the pattern.
    """
    session = FakeSession([(200, None, None)])
    client = make_gitlab_client(session)
    aspects = AspectsRest(action_pattern=99)

    raised = None
    try:
        client.perform_call(leaf="/version", method="GET", params=None, body=None,
                            exp_status=200, aspects=aspects)
    except RuntimeError as err:
        raised = err

    assert raised is not None
    assert "99" in str(raised)
    assert session.call_count == 0

    return


# ---------------------------------------------------------------------------
# ActionPattern.SINGLE_CONNECTED_CALL
# ---------------------------------------------------------------------------

def test_perform_call_single_connected_call_retries_connection_until_connected() -> None:
    """
        A connection failure is retried until the call connects, and the
        response of the connected attempt is returned.
    """
    session = FakeSession([RequestsConnectionError("refused"), (200, {"ok": True}, None)])
    client = make_gitlab_client(session)
    aspects = _fast_aspects(ActionPattern.SINGLE_CONNECTED_CALL, completion_timeout=30)

    resp = client.perform_call(leaf="/version", method="GET", params=None, body=None,
                               exp_status=200, aspects=aspects)

    assert resp.json() == {"ok": True}
    assert session.call_count == 2

    return


def test_perform_call_single_connected_call_times_out_when_never_connected() -> None:
    """
        When the completion timeout elapses without a connection, a
        :class:`TimeoutError` chained to the connection failure is raised.
    """
    session = FakeSession([RequestsConnectionError("refused")])
    client = make_gitlab_client(session)
    aspects = _fast_aspects(ActionPattern.SINGLE_CONNECTED_CALL)

    raised = None
    try:
        client.perform_call(leaf="/version", method="GET", params=None, body=None,
                            exp_status=200, aspects=aspects)
    except TimeoutError as err:
        raised = err

    assert raised is not None
    assert isinstance(raised.__cause__, RequestsConnectionError)
    assert session.call_count == 1

    return


def test_perform_call_single_connected_call_unexpected_status_raises() -> None:
    """
        Once connected the call is made only once; an unexpected status raises
        the mapped HTTP error instead of retrying.
    """
    session = FakeSession([(404, {"message": "missing"}, None), (200, None, None)])
    client = make_gitlab_client(session)
    aspects = _fast_aspects(ActionPattern.SINGLE_CONNECTED_CALL, completion_timeout=30)

    raised = None
    try:
        client.perform_call(leaf="/projects/1", method="GET", params=None, body=None,
                            exp_status=200, aspects=aspects)
    except HttpNotFoundError as err:
        raised = err

    assert raised is not None
    assert session.call_count == 1
    assert session.remaining == 1

    return


# ---------------------------------------------------------------------------
# ActionPattern.DO_UNTIL_SUCCESS
# ---------------------------------------------------------------------------

def test_perform_call_until_success_retries_after_connection_error() -> None:
    """
        A session whose first call raises a connection error and whose second
        call succeeds yields the successful response after two attempts.
    """
    session = FakeSession([RequestsConnectionError("reset"), (200, {"state": "ready"}, None)])
    client = make_gitlab_client(session)
    aspects = _fast_aspects(ActionPattern.DO_UNTIL_SUCCESS, completion_timeout=30)

    resp = client.perform_call(leaf="/projects/1/jobs/5", method="GET", params=None, body=None,
                               exp_status=200, aspects=aspects)

    assert resp.json() == {"state": "ready"}
    assert session.call_count == 2

    return


def test_perform_call_until_success_retries_allowed_error_code() -> None:
    """
        A status listed in ``allowed_error_codes`` is not an error; the call is
        repeated until an expected status arrives.
    """
    session = FakeSession([(503, {"message": "warming up"}, None), (200, {"state": "ready"}, None)])
    client = make_gitlab_client(session)
    aspects = _fast_aspects(ActionPattern.DO_UNTIL_SUCCESS, completion_timeout=30, allowed_error_codes=[503])

    resp = client.perform_call(leaf="/version", method="GET", params=None, body=None,
                               exp_status=200, aspects=aspects)

    assert resp.status_code == 200
    assert session.call_count == 2

    return


def test_perform_call_until_success_unexpected_status_raises() -> None:
    """
        A status that is neither expected nor allowed stops the retry loop with
        the mapped HTTP error.
    """
    session = FakeSession([(500, {"message": "boom"}, None), (200, None, None)])
    client = make_gitlab_client(session)
    aspects = _fast_aspects(ActionPattern.DO_UNTIL_SUCCESS, completion_timeout=30)

    raised = None
    try:
        client.perform_call(leaf="/version", method="GET", params=None, body=None,
                            exp_status=200, aspects=aspects)
    except HttpInternalServerError as err:
        raised = err

    assert raised is not None
    assert session.call_count == 1

    return


def test_perform_call_until_success_times_out() -> None:
    """
        When no attempt succeeds before the completion timeout, a
        :class:`TimeoutError` is raised.
    """
    session = FakeSession([RequestsConnectionError("reset")])
    client = make_gitlab_client(session)
    aspects = _fast_aspects(ActionPattern.DO_UNTIL_SUCCESS)

    raised = None
    try:
        client.perform_call(leaf="/version", method="GET", params=None, body=None,
                            exp_status=200, aspects=aspects)
    except TimeoutError as err:
        raised = err

    assert raised is not None
    assert session.call_count == 1

    return


def test_perform_call_until_success_must_connect_bubbles_connection_error() -> None:
    """
        With ``must_connect`` set, a connection failure is not retried but
        raised to the caller.
    """
    session = FakeSession([RequestsConnectionError("reset"), (200, None, None)])
    client = make_gitlab_client(session)
    aspects = _fast_aspects(ActionPattern.DO_UNTIL_SUCCESS, completion_timeout=30, must_connect=True)

    raised = None
    try:
        client.perform_call(leaf="/version", method="GET", params=None, body=None,
                            exp_status=200, aspects=aspects)
    except RequestsConnectionError as err:
        raised = err

    assert raised is not None
    assert session.call_count == 1

    return


# ---------------------------------------------------------------------------
# ActionPattern.DO_WHILE_SUCCESS
# ---------------------------------------------------------------------------

def test_perform_call_while_success_returns_last_response_before_connection_failure() -> None:
    """
        Calls repeat while they succeed; the response before the connection
        failure is returned.
    """
    session = FakeSession([(200, {"n": 1}, None), (200, {"n": 2}, None), RequestsConnectionError("gone")])
    client = make_gitlab_client(session)
    aspects = _fast_aspects(ActionPattern.DO_WHILE_SUCCESS, completion_timeout=30)

    resp = client.perform_call(leaf="/version", method="GET", params=None, body=None,
                               exp_status=200, aspects=aspects)

    assert resp.json() == {"n": 2}
    assert session.call_count == 3

    return


def test_perform_call_while_success_stops_on_allowed_error_code() -> None:
    """
        An allowed error status ends the loop without raising, and that
        response is the one returned.
    """
    session = FakeSession([(200, {"n": 1}, None), (404, {"message": "gone"}, None), (200, {"n": 3}, None)])
    client = make_gitlab_client(session)
    aspects = _fast_aspects(ActionPattern.DO_WHILE_SUCCESS, completion_timeout=30, allowed_error_codes=[404])

    resp = client.perform_call(leaf="/projects/1", method="GET", params=None, body=None,
                               exp_status=200, aspects=aspects)

    assert resp.status_code == 404
    assert session.call_count == 2

    return


def test_perform_call_while_success_unexpected_status_raises() -> None:
    """
        An unexpected status that is not allowed raises the mapped HTTP error.
    """
    session = FakeSession([(200, {"n": 1}, None), (500, {"message": "boom"}, None)])
    client = make_gitlab_client(session)
    aspects = _fast_aspects(ActionPattern.DO_WHILE_SUCCESS, completion_timeout=30)

    raised = None
    try:
        client.perform_call(leaf="/version", method="GET", params=None, body=None,
                            exp_status=200, aspects=aspects)
    except HttpInternalServerError as err:
        raised = err

    assert raised is not None
    assert session.call_count == 2

    return


def test_perform_call_while_success_times_out() -> None:
    """
        When calls keep succeeding past the completion timeout, a
        :class:`TimeoutError` is raised.
    """
    session = FakeSession([(200, {"n": 1}, None)])
    client = make_gitlab_client(session)
    aspects = _fast_aspects(ActionPattern.DO_WHILE_SUCCESS)

    raised = None
    try:
        client.perform_call(leaf="/version", method="GET", params=None, body=None,
                            exp_status=200, aspects=aspects)
    except TimeoutError as err:
        raised = err

    assert raised is not None
    assert session.call_count == 1

    return


# ---------------------------------------------------------------------------
# ActionPattern.DO_UNTIL_CONNECTION_FAILURE
# ---------------------------------------------------------------------------

def test_perform_call_until_connection_failure_returns_last_response() -> None:
    """
        Calls repeat until the connection fails; the last response received
        before the failure is returned.
    """
    session = FakeSession([(200, {"n": 1}, None), (200, {"n": 2}, None), RequestsConnectionError("gone")])
    client = make_gitlab_client(session)
    aspects = _fast_aspects(ActionPattern.DO_UNTIL_CONNECTION_FAILURE, completion_timeout=30)

    resp = client.perform_call(leaf="/version", method="GET", params=None, body=None,
                               exp_status=200, aspects=aspects)

    assert resp.json() == {"n": 2}
    assert session.call_count == 3

    return


def test_perform_call_until_connection_failure_times_out() -> None:
    """
        When the connection never fails before the completion timeout, a
        :class:`TimeoutError` is raised.
    """
    session = FakeSession([(200, {"n": 1}, None)])
    client = make_gitlab_client(session)
    aspects = _fast_aspects(ActionPattern.DO_UNTIL_CONNECTION_FAILURE)

    raised = None
    try:
        client.perform_call(leaf="/version", method="GET", params=None, body=None,
                            exp_status=200, aspects=aspects)
    except TimeoutError as err:
        raised = err

    assert raised is not None
    assert session.call_count == 1

    return


# ---------------------------------------------------------------------------
# Session acquisition and authentication
# ---------------------------------------------------------------------------

def test_get_session_prefers_session_carried_by_aspects() -> None:
    """
        A session supplied on the aspects is used without authenticating.
    """
    aspects_session = FakeSession()
    client = make_gitlab_client(None, aspects=AspectsRest())

    with patch.object(client, "authenticate") as authenticate:
        session = client._get_session(AspectsRest(session=aspects_session))

    assert session is aspects_session
    assert authenticate.call_count == 0

    return


def test_get_session_authenticates_once_and_reuses_session() -> None:
    """
        Without a session, the first acquisition authenticates and later
        acquisitions reuse the same session without authenticating again.
    """
    established = FakeSession()
    client = make_gitlab_client(None)

    def install_session() -> None:
        client._session = established
        return

    with patch.object(client, "authenticate", side_effect=install_session) as authenticate:
        first = client._get_session(AspectsRest())
        second = client._get_session(AspectsRest())

    assert first is established
    assert second is established
    assert authenticate.call_count == 1

    return


def test_authenticate_posts_basic_credentials_and_stores_session() -> None:
    """
        ``authenticate`` posts a Basic authorization header built from the
        credential to the auth URL over a fresh session and keeps that session.
    """
    auth_session = FakeSession([(200, {"token": "x"}, None)])
    client = make_gitlab_client(None)

    with patch.object(restclientbase_module, "Session", return_value=auth_session):
        client.authenticate()

    expected_auth = b64encode(f"{TEST_USERNAME}:{TEST_PASSWORD}".encode("utf-8")).decode("utf-8")
    call = auth_session.last_call

    assert client._session is auth_session
    assert auth_session.verify is False
    assert call.method == "POST"
    assert call.url == f"https://{TEST_HOST}/"
    assert call.headers["Authorization"] == f"Basic {expected_auth}"
    assert call.headers["Content-Type"] == "application/json"

    return


def test_authenticate_rejects_non_ok_status_with_forbidden_error() -> None:
    """
        A non-200 authentication response raises :class:`HttpForbiddenError`
        whose message carries the status and the response body.
    """
    auth_session = FakeSession([(401, {"message": "401 Unauthorized"}, None)])
    client = make_gitlab_client(None)

    raised = None
    with patch.object(restclientbase_module, "Session", return_value=auth_session):
        try:
            client.authenticate()
        except HttpForbiddenError as err:
            raised = err

    assert raised is not None
    assert "STATUS: 401" in str(raised)
    assert "401 Unauthorized" in str(raised)
    assert client._session is None

    return


# ---------------------------------------------------------------------------
# URL and path formatting
# ---------------------------------------------------------------------------

def test_format_call_url_joins_scheme_host_port_and_leaf() -> None:
    """
        The call URL is the scheme, host and port from construction followed
        by the leaf verbatim.
    """
    client = make_gitlab_client(None, host="gitlab.internal", port=8080, scheme="http")

    call_url = client._format_call_url("/api/v4/version")

    assert call_url == "http://gitlab.internal:8080/api/v4/version"

    return


def test_format_path_property_round_trips_and_isolates_segments() -> None:
    """
        For any parameter name and any value drawn from letters plus URL
        reserved characters, substituting into ``/projects/{name}/branches``
        keeps the value inside its own segment (no ``/``, ``?`` or ``#`` leaks
        through), leaves the surrounding segments untouched, and the encoded
        segment decodes back to the original value.
    """
    reserved = " /?#&=%+;:@[]{}!$'()*,\""
    letters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

    client = RestClientBase.__new__(RestClientBase)

    def check(name: str, value: str) -> None:
        leaf = "/projects/{" + name + "}/branches"

        result = client.format_path(leaf, {name: value})

        segments = result.split("/")

        assert len(segments) == 4, f"value {value!r} escaped its segment: {result!r}"
        assert segments[0] == ""
        assert segments[1] == "projects"
        assert segments[3] == "branches"
        assert "?" not in segments[2]
        assert "#" not in segments[2]
        assert unquote(segments[2]) == value
        assert segments[2] == quote(value, safe="")
        return

    examples = run_property(
        check,
        max_examples=200,
        name=st.text(alphabet=letters + "_", min_size=1, max_size=12),
        value=st.text(alphabet=letters + reserved, min_size=0, max_size=24),
    )

    assert examples == 200

    return
