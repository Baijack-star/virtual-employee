from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field # Added Field for default_factory
import uvicorn
import uuid
import asyncio
import logging # Added logging

# Assuming the wrapper is in app.agents.openai_research_wrapper
from app.agents.openai_research_wrapper import execute_openai_research

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# --- Pydantic Models ---
class StartAgentResponse(BaseModel):
    session_id: str
    message: str
    agent_type: str

class ResearchTaskRequest(BaseModel):
    task_description: str

class ResearchAssistantResponse(BaseModel):
    session_id: str
    summary: str
    details: list[str] = Field(default_factory=list)
    status: str
    title: str = None
    outline: list[str] = Field(default_factory=list)
    full_report_content: str = None # Matches wrapper's output key
    sources: list[str] = Field(default_factory=list)
    word_count: int = None
    collected_facts: list[dict] = Field(default_factory=list)
    error_message: str = None

# --- Endpoints ---
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    agents = [
        {"id": "writer", "name": "文案策划员", "description": "擅长撰写各类营销文案、广告语、社交媒体内容等。", "type": "standard"},
        {"id": "data_analyst", "name": "数据分析员", "description": "能够处理和分析数据，提取洞见，并生成报告。", "type": "standard"},
        {"id": "video_producer", "name": "视频制作员", "description": "可以协助完成视频脚本编写、剪辑和后期制作。", "type": "standard"},
        {"id": "research_assistant", "name": "深度研究助理", "description": "输入研究主题或问题，获取由AI驱动的研究报告。", "type": "research"}
    ]
    return templates.TemplateResponse("index.html", {"request": request, "agents": agents})

@app.post("/api/agent/start/{agent_type}", response_model=StartAgentResponse)
async def start_agent(agent_type: str):
    logger.info(f"Received request to start agent of type: {agent_type}")
    session_id = str(uuid.uuid4())
    return StartAgentResponse(
        session_id=session_id,
        message=f"AI agent '{agent_type}' starting procedure initiated.",
        agent_type=agent_type
    )

# Corrected event_generator
async def event_generator(session_id: str, agent_type: str):
    logger.info(f"SSE connection established for session_id: {session_id}, agent_type: {agent_type}")
    yield f"data: Agent ({agent_type} - {session_id}): Initializing...\n\n"
    await asyncio.sleep(1)
    yield f"data: Agent ({agent_type} - {session_id}): Configuration loading...\n\n"
    await asyncio.sleep(1)
    yield f"data: Agent ({agent_type} - {session_id}): Resources allocation pending...\n\n"
    await asyncio.sleep(2)
    yield f"data: Agent ({agent_type} - {session_id}): All systems nominal. Ready.\n\n"
    await asyncio.sleep(1)
    yield f"data: Agent ({agent_type} - {session_id}): Monitoring activity... (Placeholder for actual work)\n\n"
    logger.info(f"SSE stream placeholder work done for session_id: {session_id}, agent_type: {agent_type}")
    # Example: yield f"data: Agent ({agent_type} - {session_id}): Process complete.\n\n"

@app.get("/api/agent/status/{agent_type}/{session_id}")
async def agent_status_sse(request: Request, agent_type: str, session_id: str):
    return StreamingResponse(event_generator(session_id, agent_type), media_type="text/event-stream")

@app.post("/api/agent/research_assistant/invoke", response_model=ResearchAssistantResponse)
async def invoke_research_assistant(request_data: ResearchTaskRequest):
    run_id = str(uuid.uuid4())
    logger.info(f"[{run_id}] Received research task via API: '{request_data.task_description}'")

    research_result_dict = await execute_openai_research(
        topic=request_data.task_description,
        run_id=run_id
    )

    try:
        response_obj = ResearchAssistantResponse(**research_result_dict)
    except Exception as e:
        logger.error(f"[{run_id}] Error creating ResearchAssistantResponse Pydantic model from research_result_dict: {e}", exc_info=True)
        logger.error(f"[{run_id}] research_result_dict was: {research_result_dict}")
        return ResearchAssistantResponse(
            session_id=run_id,
            summary="Internal Server Error: Failed to parse research results.",
            details=[f"Pydantic validation error: {str(e)}"], # Make sure details is a list of strings
            status="error_internal_parsing",
            error_message=f"Pydantic model creation error from dict: {str(e)}"
            # Ensure all required fields of ResearchAssistantResponse have defaults or are provided
        )

    logger.info(f"[{run_id}] Successfully processed research task. Status: {response_obj.status}")
    return response_obj

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    logger.info("Starting Uvicorn server for main app with .env loaded.")
    uvicorn.run("app.main:app", app=None, host="0.0.0.0", port=8000, reload=True, use_colors=True)

EOL

echo "Step 1: Corrected syntax error in event_generator in app/main.py."
echo "Ensured all yielded f-strings are properly quoted and end with double newlines."
