"""
Unit tests for VikunjaClient using respx to mock httpx calls.

Run with:
    pytest tests/test_client.py -v
"""
import json
import time
from unittest.mock import patch

import pytest
import respx
import httpx

# Add src/ to path so the import works without installing the package.
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from vikunja_client import VikunjaClient

API_URL = "http://vikunja-test"
USERNAME = "testuser"
PASSWORD = "testpass"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_jwt(exp: float) -> str:
    """Build a minimal (unsigned) JWT with the given exp claim."""
    import base64
    header = base64.urlsafe_b64encode(b'{"alg":"none"}').rstrip(b"=").decode()
    payload_bytes = json.dumps({"exp": exp, "sub": USERNAME}).encode()
    payload = base64.urlsafe_b64encode(payload_bytes).rstrip(b"=").decode()
    return f"{header}.{payload}.fakesig"


VALID_TOKEN = _make_jwt(time.time() + 7200)
EXPIRED_TOKEN = _make_jwt(time.time() - 1)

LOGIN_RESPONSE = {"token": VALID_TOKEN}

TASK_1 = {"id": 1, "title": "Test task", "done": False, "description": "", "project_id": 1}
TASK_2 = {"id": 2, "title": "Another task", "done": True, "description": "Desc", "project_id": 1}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    return VikunjaClient(API_URL, USERNAME, PASSWORD)


# ---------------------------------------------------------------------------
# Auth tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@respx.mock
async def test_login_sets_token(client):
    respx.post(f"{API_URL}/api/v1/login").mock(
        return_value=httpx.Response(200, json=LOGIN_RESPONSE)
    )
    respx.get(f"{API_URL}/api/v1/projects/1/tasks").mock(
        return_value=httpx.Response(200, json=[TASK_1])
    )

    await client.list_tasks(project_id=1)

    assert client._token == VALID_TOKEN
    assert client._token_expiry > time.time()


@pytest.mark.asyncio
@respx.mock
async def test_401_triggers_relogin(client):
    """On 401 the client re-logs in and retries the request."""
    login_calls = []

    def login_side_effect(request):
        login_calls.append(request)
        return httpx.Response(200, json=LOGIN_RESPONSE)

    respx.post(f"{API_URL}/api/v1/login").mock(side_effect=login_side_effect)

    call_count = [0]

    def tasks_side_effect(request):
        call_count[0] += 1
        if call_count[0] == 1:
            return httpx.Response(401, json={"message": "Unauthorized"})
        return httpx.Response(200, json=[TASK_1])

    respx.get(f"{API_URL}/api/v1/projects/1/tasks").mock(side_effect=tasks_side_effect)

    # Pre-set an expired token so _auth_headers logs in once on the first call.
    client._token = EXPIRED_TOKEN
    client._token_expiry = 0.0

    result = await client.list_tasks(project_id=1)
    assert result == [TASK_1]
    # Should have logged in twice: once for the expired token, once after the 401.
    assert len(login_calls) == 2


# ---------------------------------------------------------------------------
# list_tasks
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@respx.mock
async def test_list_tasks_returns_task_list(client):
    respx.post(f"{API_URL}/api/v1/login").mock(return_value=httpx.Response(200, json=LOGIN_RESPONSE))
    respx.get(f"{API_URL}/api/v1/projects/1/tasks").mock(
        return_value=httpx.Response(200, json=[TASK_1, TASK_2])
    )

    result = await client.list_tasks(project_id=1)

    assert len(result) == 2
    assert result[0]["title"] == "Test task"
    assert result[1]["done"] is True


# ---------------------------------------------------------------------------
# create_task
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@respx.mock
async def test_create_task_sends_put(client):
    respx.post(f"{API_URL}/api/v1/login").mock(return_value=httpx.Response(200, json=LOGIN_RESPONSE))

    created = {**TASK_1, "title": "New task", "description": "Details"}
    route = respx.put(f"{API_URL}/api/v1/projects/1/tasks").mock(
        return_value=httpx.Response(200, json=created)
    )

    result = await client.create_task(project_id=1, title="New task", description="Details")

    assert result["title"] == "New task"
    assert result["description"] == "Details"
    body = json.loads(route.calls[0].request.content)
    assert body["title"] == "New task"
    assert body["description"] == "Details"


@pytest.mark.asyncio
@respx.mock
async def test_create_task_with_bucket_id(client):
    respx.post(f"{API_URL}/api/v1/login").mock(return_value=httpx.Response(200, json=LOGIN_RESPONSE))

    created = {**TASK_1, "bucket_id": 42}
    route = respx.put(f"{API_URL}/api/v1/projects/1/tasks").mock(
        return_value=httpx.Response(200, json=created)
    )

    await client.create_task(project_id=1, title="Task", bucket_id=42)

    body = json.loads(route.calls[0].request.content)
    assert body["bucket_id"] == 42


@pytest.mark.asyncio
@respx.mock
async def test_create_task_omits_bucket_id_when_none(client):
    respx.post(f"{API_URL}/api/v1/login").mock(return_value=httpx.Response(200, json=LOGIN_RESPONSE))
    route = respx.put(f"{API_URL}/api/v1/projects/1/tasks").mock(
        return_value=httpx.Response(200, json=TASK_1)
    )

    await client.create_task(project_id=1, title="Task")

    body = json.loads(route.calls[0].request.content)
    assert "bucket_id" not in body


# ---------------------------------------------------------------------------
# update_task
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@respx.mock
async def test_update_task_sends_post(client):
    respx.post(f"{API_URL}/api/v1/login").mock(return_value=httpx.Response(200, json=LOGIN_RESPONSE))

    updated = {**TASK_1, "done": True}
    route = respx.post(f"{API_URL}/api/v1/tasks/1").mock(
        return_value=httpx.Response(200, json=updated)
    )

    result = await client.update_task(task_id=1, done=True)

    assert result["done"] is True
    body = json.loads(route.calls[0].request.content)
    assert body == {"done": True}


@pytest.mark.asyncio
@respx.mock
async def test_update_task_sends_only_provided_fields(client):
    respx.post(f"{API_URL}/api/v1/login").mock(return_value=httpx.Response(200, json=LOGIN_RESPONSE))

    route = respx.post(f"{API_URL}/api/v1/tasks/1").mock(
        return_value=httpx.Response(200, json={**TASK_1, "title": "Renamed"})
    )

    await client.update_task(task_id=1, title="Renamed")

    body = json.loads(route.calls[0].request.content)
    assert list(body.keys()) == ["title"]


# ---------------------------------------------------------------------------
# get_task
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@respx.mock
async def test_get_task_returns_task(client):
    respx.post(f"{API_URL}/api/v1/login").mock(return_value=httpx.Response(200, json=LOGIN_RESPONSE))
    respx.get(f"{API_URL}/api/v1/tasks/1").mock(return_value=httpx.Response(200, json=TASK_1))

    result = await client.get_task(task_id=1)

    assert result["id"] == 1
    assert result["title"] == "Test task"
