"""
    Wire tests for :class:`ccai.gitlab.rest.clients.groups.jobs.JobsApiGroup`
    over a :class:`FakeSession`.
"""

from ccai.gitlab.rest.clients.parameters import jobs as parameters

from testbase.testshared.clientfactory import make_gitlab_client
from testbase.testshared.fakesession import FakeSession, assert_call_path


def test_jobs_list_project_jobs_hits_get_projects_id_jobs_with_scope() -> None:
    """
        ``listprojectjobs(id, scope)`` hits ``GET /projects/{id}/jobs`` and
        sends every scope value as a repeated query parameter.
    """
    jobs = [{"id": 1, "status": "success"}, {"id": 2, "status": "failed"}]
    session = FakeSession([(200, jobs, None)])
    client = make_gitlab_client(session)

    params = parameters.JobsListprojectjobsParams(id="42", scope=["success", "failed"])
    result = client.jobs.listprojectjobs(params)

    assert_call_path(session.last_call, "GET", "/projects/{id}/jobs", id="42")
    assert session.last_call.params == {"scope": ["success", "failed"]}
    assert result.data == jobs

    return


def test_jobs_get_single_job_hits_get_projects_id_jobs_job_id() -> None:
    """
        ``getsinglejob(id, job_id)`` hits ``GET /projects/{id}/jobs/{job_id}``.
    """
    session = FakeSession([(200, {"id": 17, "status": "running"}, None)])
    client = make_gitlab_client(session)

    params = parameters.JobsGetsinglejobParams(id="42", job_id=17)
    result = client.jobs.getsinglejob(params)

    assert_call_path(session.last_call, "GET", "/projects/{id}/jobs/{job_id}", id="42", job_id=17)
    assert result.data["status"] == "running"

    return


def test_jobs_trigger_manual_job_posts_to_play() -> None:
    """
        ``triggermanualjob(id, job_id)`` hits ``POST /projects/{id}/jobs/{job_id}/play``.
    """
    session = FakeSession([(200, {"id": 17, "status": "pending"}, None)])
    client = make_gitlab_client(session)

    params = parameters.JobsTriggermanualjobParams(id="42", job_id=17)
    result = client.jobs.triggermanualjob(params)

    assert_call_path(session.last_call, "POST", "/projects/{id}/jobs/{job_id}/play", id="42", job_id=17)
    assert result.ok is True

    return
