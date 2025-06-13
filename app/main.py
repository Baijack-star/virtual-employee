from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import uvicorn
import uuid
import asyncio

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

class StartAgentResponse(BaseModel):
    session_id: str
    message: str
    agent_type: str

class ResearchTaskRequest(BaseModel):
    task_description: str

class ResearchAssistantResponse(BaseModel):
    session_id: str
    summary: str
    details: list[str]
    status: str

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    agents = [
        {"id": "writer", "name": "文案策划员", "description": "擅长撰写各类营销文案、广告语、社交媒体内容等。", "type": "standard"},
        {"id": "data_analyst", "name": "数据分析员", "description": "能够处理和分析数据，提取洞见，并生成报告。", "type": "standard"},
        {"id": "video_producer", "name": "视频制作员", "description": "可以协助完成视频脚本编写、剪辑和后期制作。", "type": "standard"},
        {"id": "research_assistant", "name": "深度研究助理", "description": "输入研究主题或问题，获取模拟的研究摘要和详细发现。", "type": "research"} # Added research assistant
    ]
    return templates.TemplateResponse("index.html", {"request": request, "agents": agents})

@app.post("/api/agent/start/{agent_type}", response_model=StartAgentResponse)
async def start_agent(agent_type: str):
    print(f"Received request to start agent of type: {agent_type}")
    session_id = str(uuid.uuid4())
    return StartAgentResponse(
        session_id=session_id,
        message=f"AI agent '{agent_type}' starting procedure initiated.",
        agent_type=agent_type
    )

# Corrected event_generator from previous step (includes agent_type)
async def event_generator(session_id: str, agent_type: str): # agent_type IS used here
    print(f"SSE connection established for session_id: {session_id}, agent_type: {agent_type}")
    yield f"data: Agent ({agent_type} - {session_id}): Initializing...

"
    await asyncio.sleep(1)
    yield f"data: Agent ({agent_type} - {session_id}): Configuration loading.

"
    await asyncio.sleep(1)
    yield f"data: Agent ({agent_type} - {session_id}): Resources allocation pending.

"
    await asyncio.sleep(2) # Original sleep time here
    yield f"data: Agent ({agent_type} - {session_id}): All systems nominal. Ready.

"
    await asyncio.sleep(1)
    yield f"data: Agent ({agent_type} - {session_id}): Monitoring activity... (Placeholder for actual work)

"
    print(f"SSE stream placeholder work done for session_id: {session_id}")


@app.get("/api/agent/status/{agent_type}/{session_id}") # agent_type IS part of the path
async def agent_status_sse(request: Request, agent_type: str, session_id: str): # agent_type IS a parameter
    return StreamingResponse(event_generator(session_id, agent_type), media_type="text/event-stream")

async def run_simulated_research(task_description: str) -> dict:
    print(f"Starting simulated research for: {task_description}")
    await asyncio.sleep(2)
    summary = f"模拟研究摘要：关于“{task_description}”的研究已初步完成。"
    details = [
        f"发现点1：与“{task_description}”相关的第一个重要模拟发现。",
        f"发现点2：模拟数据显示“{task_description}”在某个方面表现突出。",
        "发现点3：进一步的模拟研究建议探索X、Y、Z方向。"
    ]
    await asyncio.sleep(1)
    status = "completed"
    print(f"Simulated research completed for: {task_description}")
    return {"summary": summary, "details": details, "status": status}

@app.post("/api/agent/research_assistant/invoke", response_model=ResearchAssistantResponse)
async def invoke_research_assistant(request_data: ResearchTaskRequest):
    session_id = str(uuid.uuid4())
    print(f"Received research task: '{request_data.task_description}' with session_id: {session_id}")
    research_results = await run_simulated_research(request_data.task_description)
    return ResearchAssistantResponse(
        session_id=session_id,
        summary=research_results["summary"],
        details=research_results["details"],
        status=research_results["status"]
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
