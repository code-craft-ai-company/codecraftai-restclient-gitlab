"""
    Tests for :mod:`ccai.gitlab.rest.itemsresult`: unpaged and paged results,
    and page navigation driven through pre-canned requests over a
    :class:`FakeSession` that answers with GitLab pagination headers.
"""

from typing import Any, Dict, List, Optional

from requests import Response

from ccai.gitlab.rest.itemsresult import ItemsResult, Paging, PreCannedRequest

from testbase.testshared.clientfactory import make_gitlab_client
from testbase.testshared.fakesession import FakeSession, paged


BADGES_LEAF = "/projects/7/badges"


def _header_int(resp: Response, name: str) -> Optional[int]:
    """
        Read an integer pagination header, ``None`` when absent or blank.
    """
    raw = resp.headers.get(name, "")
    rtnval = int(raw) if raw != "" else None
    return rtnval


def _package_paged_result(client, resp: Response) -> ItemsResult[Dict[str, Any]]:
    """
        Package a badges list response into an :class:`ItemsResult`, wiring
        next and previous :class:`PreCannedRequest` objects from the GitLab
        ``X-Next-Page`` and ``X-Prev-Page`` headers.
    """

    items: List[Dict[str, Any]] = resp.json()

    page = _header_int(resp, "X-Page")
    per_page = _header_int(resp, "X-Per-Page")
    total_count = _header_int(resp, "X-Total")
    last_page = _header_int(resp, "X-Total-Pages")
    next_page = _header_int(resp, "X-Next-Page")
    prev_page = _header_int(resp, "X-Prev-Page")

    def make_request(target_page: int) -> PreCannedRequest:
        request = PreCannedRequest(
            leaf=BADGES_LEAF,
            method="GET",
            params={"page": str(target_page), "per_page": str(per_page)},
            body=None,
            exp_status=200,
            aspects=None,
            perform_call=client.perform_call,
            package_result=lambda next_resp: _package_paged_result(client, next_resp),
        )
        return request

    request_next = make_request(next_page) if next_page is not None else None
    request_prev = make_request(prev_page) if prev_page is not None else None

    paging = Paging(page=page, count=len(items), total_count=total_count, per_page=per_page,
                    first_page=1, last_page=last_page, request_next=request_next,
                    request_prev=request_prev)

    result = ItemsResult(items, paging)

    return result


def _first_page(session: FakeSession) -> ItemsResult[Dict[str, Any]]:
    """
        Perform the first page request against ``session`` through a client.
    """
    client = make_gitlab_client(session)

    resp = client.perform_call(leaf=BADGES_LEAF, method="GET", params={"page": "1", "per_page": "2"},
                               body=None, exp_status=200, aspects=None)
    result = _package_paged_result(client, resp)

    return result


def test_items_result_unpaged_reports_no_paging() -> None:
    """
        A result built without paging exposes its items and reports
        ``is_paged`` false with ``paging`` ``None``.
    """
    result = ItemsResult([{"id": 1}, {"id": 2}])

    assert result.is_paged is False
    assert result.paging is None
    assert result.items == [{"id": 1}, {"id": 2}]

    return


def test_paging_exposes_constructor_fields() -> None:
    """
        :class:`Paging` returns each value it was constructed with.
    """
    paging = Paging(page=2, count=5, total_count=11, per_page=5, first_page=1, last_page=3)

    assert paging.page == 2
    assert paging.count == 5
    assert paging.total_count == 11
    assert paging.per_page == 5
    assert paging.first_page == 1
    assert paging.last_page == 3
    assert paging.request_next is None
    assert paging.request_prev is None

    return


def test_paged_result_first_page_reads_gitlab_headers() -> None:
    """
        The first of two pages carries the first ``page_size`` items and paging
        that points forward but not back.
    """
    items = [{"id": n} for n in range(1, 4)]
    session = FakeSession(paged(items, page_size=2))

    first = _first_page(session)

    assert first.is_paged is True
    assert first.items == [{"id": 1}, {"id": 2}]
    assert first.paging.page == 1
    assert first.paging.last_page == 2
    assert first.paging.total_count == 3
    assert first.paging.request_next is not None
    assert first.paging.request_prev is None

    return


def test_next_page_result_performs_precanned_request_for_second_page() -> None:
    """
        ``next_page_result`` performs the stored request: the second call hits
        the same leaf with ``page=2`` and yields the remaining items.
    """
    items = [{"id": n} for n in range(1, 4)]
    session = FakeSession(paged(items, page_size=2))

    first = _first_page(session)
    second = first.next_page_result()

    assert second.items == [{"id": 3}]
    assert second.paging.page == 2
    assert session.call_count == 2
    assert session.last_call.path == BADGES_LEAF
    assert session.last_call.params == {"page": "2", "per_page": "2"}

    return


def test_next_page_result_returns_none_on_last_page() -> None:
    """
        On the last page there is no next request, so ``next_page_result``
        returns ``None`` without making a call.
    """
    items = [{"id": n} for n in range(1, 4)]
    session = FakeSession(paged(items, page_size=2))

    first = _first_page(session)
    second = first.next_page_result()
    third = second.next_page_result()

    assert third is None
    assert session.call_count == 2

    return


def test_prev_page_result_performs_precanned_request_for_previous_page() -> None:
    """
        From the second page, ``prev_page_result`` requests ``page=1`` again.
    """
    items = [{"id": n} for n in range(1, 4)]
    responses = paged(items, page_size=2)
    # Page one is served twice: once for the initial call, once for the walk back.
    session = FakeSession([responses[0], responses[1], responses[0]])

    first = _first_page(session)
    second = first.next_page_result()
    back = second.prev_page_result()

    assert back.items == [{"id": 1}, {"id": 2}]
    assert session.call_count == 3
    assert session.last_call.params == {"page": "1", "per_page": "2"}

    return


def test_prev_page_result_returns_none_on_first_page() -> None:
    """
        The first page has no previous request, so ``prev_page_result`` is
        ``None`` and no call is made.
    """
    items = [{"id": n} for n in range(1, 4)]
    session = FakeSession(paged(items, page_size=2))

    first = _first_page(session)
    back = first.prev_page_result()

    assert back is None
    assert session.call_count == 1

    return


def test_empty_page_yields_no_items_and_no_next_page() -> None:
    """
        An empty collection is a single page with no items, a total of zero
        and no next request.
    """
    session = FakeSession(paged([], page_size=2))

    first = _first_page(session)

    assert first.items == []
    assert first.paging.count == 0
    assert first.paging.total_count == 0
    assert first.paging.last_page == 1
    assert first.next_page_result() is None

    return


def test_precanned_request_passes_stored_call_details_to_perform_call() -> None:
    """
        ``PreCannedRequest.perform_call`` hands its stored leaf, method, params,
        body, expected status and aspects to the ``perform_call`` callable and
        packages the response with ``package_result``.
    """
    received: Dict[str, Any] = {}

    def fake_perform_call(**kwargs) -> str:
        received.update(kwargs)
        rtnval = "raw-response"
        return rtnval

    request = PreCannedRequest(leaf="/projects/7/badges", method="GET", params={"page": "3"},
                               body=None, exp_status=[200], aspects=None,
                               perform_call=fake_perform_call,
                               package_result=lambda resp: ItemsResult([resp]))

    result = request.perform_call()

    assert request.leaf == "/projects/7/badges"
    assert received == {"leaf": "/projects/7/badges", "method": "GET", "params": {"page": "3"},
                        "body": None, "exp_status": [200], "aspects": None}
    assert result.items == ["raw-response"]

    return
