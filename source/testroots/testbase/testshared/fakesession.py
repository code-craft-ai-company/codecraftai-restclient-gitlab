"""
    .. module:: fakesession
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: A canned-response stand-in for :class:`requests.Session` used by the
               GitLab REST client tests.  Adapted from the shared helper described in
               the test coverage roadmap (Phase 1a) for the GitLab client's own
               :class:`ccai.gitlab.rest.restclientbase.RestClientBase`.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Code Craft AI LLC"
__credits__ = []


from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import json

from urllib.parse import parse_qs, quote, urlsplit

from requests import PreparedRequest, Response
from requests.structures import CaseInsensitiveDict


CannedResponse = Tuple[int, Any, Optional[Dict[str, str]]]
"""
    A canned response is a ``(status, json, headers)`` tuple.  ``json`` is
    serialized as the response body when it is not ``None``; ``headers`` may
    be ``None`` for no headers.
"""


class FakeSessionExhaustedError(AssertionError):
    """
        Raised when a call is made against a :class:`FakeSession` that has no
        canned responses left.  It derives from :class:`AssertionError` so a
        test that makes more calls than it programmed reports as a failure.
    """


class RecordedCall:
    """
        The details of one call made against a :class:`FakeSession`.
    """

    def __init__(self, *, method: str, url: str, headers: Dict[str, str], body: Any,
                 timeout: Any = None, verify: Any = None):
        """
            :param method: The HTTP method of the call.
            :param url: The full URL of the call, including any query string.
            :param headers: The headers sent with the call.
            :param body: The raw body sent with the call, ``None`` when there was none.
            :param timeout: The ``timeout`` keyword the client passed to the session.
            :param verify: The ``verify`` keyword the client passed to the session.
        """

        self.method = method
        self.url = url
        self.headers = dict(headers)
        self.body = body
        self.timeout = timeout
        self.verify = verify

        parts = urlsplit(url)
        self.path = parts.path

        # Query parameters are recorded as a flat dict when each name appears
        # once, which is how the generated parameter classes send them.
        self.params: Dict[str, Union[str, List[str]]] = {}
        for name, values in parse_qs(parts.query, keep_blank_values=True).items():
            if len(values) == 1:
                self.params[name] = values[0]
            else:
                self.params[name] = values

        return

    @property
    def form(self) -> Dict[str, Union[str, List[str]]]:
        """
            The body decoded as form fields.  The client sends dictionary bodies
            as ``application/x-www-form-urlencoded`` data.

            :returns: A dictionary of the decoded form fields, empty when there was no body.
        """

        fields: Dict[str, Union[str, List[str]]] = {}

        if self.body:
            raw = self.body
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            for name, values in parse_qs(raw, keep_blank_values=True).items():
                if len(values) == 1:
                    fields[name] = values[0]
                else:
                    fields[name] = values

        return fields

    def __repr__(self) -> str:
        rtnval = f"RecordedCall(method={self.method!r}, url={self.url!r}, params={self.params!r}, body={self.body!r})"
        return rtnval


def make_response(status: int, body: Any = None, headers: Optional[Dict[str, str]] = None,
                  url: Optional[str] = None) -> Response:
    """
        Build a real :class:`requests.Response` carrying a canned status, JSON
        body and headers.

        :param status: The HTTP status code.
        :param body: The JSON-serializable body, or ``None`` for an empty body.
        :param headers: Optional response headers.
        :param url: Optional URL to stamp on the response.

        :returns: The populated response object.
    """

    resp = Response()
    resp.status_code = status
    resp.encoding = "utf-8"
    resp.headers = CaseInsensitiveDict(headers or {})
    resp.url = url

    if body is None:
        resp._content = b""
    else:
        resp._content = json.dumps(body).encode("utf-8")
        if "Content-Type" not in resp.headers:
            resp.headers["Content-Type"] = "application/json"

    return resp


class FakeSession:
    """
        A stand-in for :class:`requests.Session` that records every call made
        through it and answers each call with the next canned response.

        Responses are ``(status, json, headers)`` tuples returned in order.  An
        entry may instead be an exception instance, which is raised when its
        turn comes, so a test can script a connection failure followed by a
        success.

        The GitLab :class:`RestClientBase` drives a session through
        :meth:`send` with a prepared request, and :meth:`authenticate` drives a
        fresh session through :meth:`post`; both are recorded the same way.
    """

    def __init__(self, responses: Sequence[Union[CannedResponse, BaseException]] = ()):
        """
            :param responses: The canned responses (or exceptions) to answer with, in order.
        """

        self._responses: List[Union[CannedResponse, BaseException]] = list(responses)
        self.calls: List[RecordedCall] = []
        self.verify: Any = None
        return

    @property
    def call_count(self) -> int:
        """
            The number of calls recorded so far.
        """
        return len(self.calls)

    @property
    def last_call(self) -> RecordedCall:
        """
            The most recent recorded call.
        """
        return self.calls[-1]

    @property
    def remaining(self) -> int:
        """
            The number of canned responses not yet consumed.
        """
        return len(self._responses)

    def send(self, request: PreparedRequest, timeout: Any = None, verify: Any = None, **kwargs) -> Response:
        """
            Answer a prepared request with the next canned response.

            :param request: The prepared request the client is sending.
            :param timeout: The timeout the client passed.
            :param verify: The certificate verification flag the client passed.

            :returns: The canned :class:`Response`.
        """

        call = RecordedCall(method=request.method, url=request.url, headers=request.headers,
                            body=request.body, timeout=timeout, verify=verify)
        self.calls.append(call)

        resp = self._next_response(call)

        return resp

    def post(self, url: str, headers: Optional[Dict[str, str]] = None, data: Any = None,
             verify: Any = None, timeout: Any = None, **kwargs) -> Response:
        """
            Answer a direct ``post`` (as used by ``authenticate``) with the next
            canned response.

            :param url: The URL being posted to.
            :param headers: The headers sent.
            :param data: The body sent.
            :param verify: The certificate verification flag the client passed.
            :param timeout: The timeout the client passed.

            :returns: The canned :class:`Response`.
        """

        call = RecordedCall(method="POST", url=url, headers=headers or {}, body=data,
                            timeout=timeout, verify=verify)
        self.calls.append(call)

        resp = self._next_response(call)

        return resp

    def _next_response(self, call: RecordedCall) -> Response:
        """
            Pop the next canned entry, raising it if it is an exception and
            otherwise building a response from it.
        """

        if len(self._responses) == 0:
            errmsg = f"FakeSession has no canned response left for call {call!r}"
            raise FakeSessionExhaustedError(errmsg)

        entry = self._responses.pop(0)

        if isinstance(entry, BaseException):
            raise entry

        status, body, headers = entry
        resp = make_response(status, body, headers, url=call.url)

        return resp


def paged(items: Sequence[Any], page_size: int) -> List[CannedResponse]:
    """
        Build the canned responses for a GitLab-style paged collection.

        GitLab paginates with the ``X-Page``, ``X-Per-Page``, ``X-Total``,
        ``X-Total-Pages``, ``X-Next-Page`` and ``X-Prev-Page`` headers.  One
        ``(200, page_items, headers)`` entry is produced per page.  An empty
        collection produces a single empty page whose ``X-Total`` is ``0``.

        :param items: The complete collection to split into pages.
        :param page_size: The number of items per page.

        :returns: The canned responses, first page first.
    """

    if page_size < 1:
        errmsg = f"page_size must be at least 1, got {page_size}"
        raise ValueError(errmsg)

    total = len(items)
    total_pages = max(1, (total + page_size - 1) // page_size)

    responses: List[CannedResponse] = []

    for page in range(1, total_pages + 1):
        start = (page - 1) * page_size
        page_items = list(items[start:start + page_size])

        headers = {
            "X-Page": str(page),
            "X-Per-Page": str(page_size),
            "X-Total": str(total),
            "X-Total-Pages": str(total_pages),
            "X-Next-Page": str(page + 1) if page < total_pages else "",
            "X-Prev-Page": str(page - 1) if page > 1 else "",
        }

        responses.append((200, page_items, headers))

    return responses


def format_expected_path(template: str, **path_values: Any) -> str:
    """
        Fill a generator path template such as ``/groups/{id}/badges/{badge_id}``
        with URL-encoded values, the way the client is expected to.

        :param template: The path template from the generated group method.
        :param path_values: The value for each placeholder.

        :returns: The expected request path.
    """

    expected = template
    for name, value in path_values.items():
        expected = expected.replace("{" + name + "}", quote(str(value), safe=""))

    return expected


def assert_call_path(call: RecordedCall, method: str, template: str, **path_values: Any) -> None:
    """
        Assert that a recorded call used ``method`` and hit the path produced by
        filling ``template`` with ``path_values``, so a test reads as "calling
        ``badges.getapiv4groupsidbadges(id=...)`` hits ``GET /groups/{id}/badges``".

        :param call: The recorded call to check.
        :param method: The expected HTTP method.
        :param template: The generator's path template.
        :param path_values: The value for each placeholder in the template.

        :raises AssertionError: When the method or the path differ.
    """

    expected_path = format_expected_path(template, **path_values)

    if call.method != method:
        errmsg = f"Expected method {method} but the call used {call.method} (url={call.url})"
        raise AssertionError(errmsg)

    if call.path != expected_path:
        errmsg = f"Expected path {expected_path} from template {template} but the call hit {call.path} (url={call.url})"
        raise AssertionError(errmsg)

    return
