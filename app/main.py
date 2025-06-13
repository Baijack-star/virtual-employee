from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse # Added StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import uvicorn
import uuid
import asyncio # Added for asyncio.sleep

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

class StartAgentResponse(BaseModel):
    session_id: str
    message: str
    agent_type: str

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    agents = [
        {"id": "writer", "name": "文案策划员", "description": "擅长撰写各类营销文案、广告语、社交媒体内容等。"},
        {"id": "data_analyst", "name": "数据分析员", "description": "能够处理和分析数据，提取洞见，并生成报告。"},
        {"id": "video_producer", "name": "视频制作员", "description": "可以协助完成视频脚本编写、剪辑和后期制作。"}
    ]
    return templates.TemplateResponse("index.html", {"request": request, "agents": agents})

@app.post("/api/agent/start/{agent_type}", response_model=StartAgentResponse)
async def start_agent(agent_type: str):
    print(f"Received request to start agent of type: {agent_type}")
    session_id = str(uuid.uuid4())
    # Placeholder: In a real app, you'd associate this session_id with the agent process
    return StartAgentResponse(
        session_id=session_id,
        message=f"AI agent '{agent_type}' starting procedure initiated.",
        agent_type=agent_type
    )

async def event_generator(session_id: str, agent_type: str):
    # Simulate some status updates for the given session_id
    # In a real application, this would check actual agent status
    print(f"SSE connection established for session_id: {session_id}, agent_type: {agent_type}")
    yield f"data: Agent ({agent_type} - {session_id}): Initializing...

"
    await asyncio.sleep(1) # Shorter delay for faster feedback
    yield f"data: Agent ({agent_type} - {session_id}): Configuration loading.

"
    await asyncio.sleep(1)
    yield f"data: Agent ({agent_type} - {session_id}): Resources allocation pending.

"
    await asyncio.sleep(2)
    yield f"data: Agent ({agent_type} - {session_id}): All systems nominal. Ready.

"
    # Simulate completion or further updates
    # For this example, we'll send a final message.
    await asyncio.sleep(1)
    yield f"data: Agent ({agent_type} - {session_id}): Monitoring activity... (Placeholder for actual work)

"
    print(f"SSE stream placeholder work done for session_id: {session_id}")
    # If you want the stream to end, you can stop yielding.
    # If you want it to stay open and periodically send keep-alive or new events,
    # you'd have a loop here. For this example, it will naturally end after the last yield.

@app.get("/api/agent/status/{agent_type}/{session_id}") # Added agent_type to pass to generator
async def agent_status_sse(request: Request, agent_type: str, session_id: str):
    # Pass agent_type to event_generator if needed for context in messages
    return StreamingResponse(event_generator(session_id, agent_type), media_type="text/event-stream")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
