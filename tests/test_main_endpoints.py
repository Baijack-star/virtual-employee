import pytest
from httpx import AsyncClient

# Import your FastAPI app instance.
from app.main import app as fastapi_app

# Mark all tests in this module as asyncio
pytestmark = pytest.mark.asyncio


@pytest.fixture(scope="module")
async def client():
    async with AsyncClient(app=fastapi_app, base_url="http://127.0.0.1:8000") as ac:
        yield ac


async def test_read_root(client: AsyncClient):
    response = await client.get("/")
    assert response.status_code == 200
    assert "虚拟员工平台" in response.text


async def test_start_standard_agent(client: AsyncClient):
    agent_type = "writer"  # Example standard agent
    response = await client.post(f"/api/agent/start/{agent_type}")
    assert response.status_code == 200
    json_response = response.json()
    assert json_response["agent_type"] == agent_type
    assert "session_id" in json_response
    assert "message" in json_response


async def test_invoke_research_assistant_valid_request(client: AsyncClient):
    task_description = "Test research on FastAPI"
    request_payload = {"task_description": task_description}
    response = await client.post(
        "/api/agent/research_assistant/invoke", json=request_payload
    )
    assert response.status_code == 200
    json_response = response.json()
    assert "session_id" in json_response
    assert "summary" in json_response
    assert "details" in json_response
    assert json_response["status"] == "completed"  # Based on current simulated logic
    assert task_description in json_response["summary"]


async def test_invoke_research_assistant_missing_description(client: AsyncClient):
    response = await client.post(
        "/api/agent/research_assistant/invoke", json={}
    )  # Missing task_description
    assert response.status_code == 422  # HTTP 422 for Pydantic validation errors


async def test_agent_status_sse_endpoint_exists(client: AsyncClient):
    agent_type = "writer"  # Example agent type
    session_id = "test-session-123"
    # Corrected URL to include agent_type as per app/main.py
    url = f"/api/agent/status/{agent_type}/{session_id}"

    # Make a HEAD request first to check headers without consuming the body if not needed
    # However, for streaming, a GET is usually initiated directly.
    # We'll use client.stream for a brief interaction.
    try:
        async with client.stream("GET", url) as response:
            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]
            # Optionally, try to read a small piece of the stream to ensure it's working
            # This part can be tricky as it depends on timing and exact output.
            # For a simple check, just ensuring the connection opens and headers are right is often enough.
            # Example:
            # async for line in response.aiter_lines():
            #    assert "data:" in line # Check for SSE data format
            #    break # Only check the first line for this basic test
            await response.aclose()  # Ensure the stream is closed promptly
    except Exception as e:
        pytest.fail(f"SSE endpoint test failed: {e}")
