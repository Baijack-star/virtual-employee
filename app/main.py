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

# Configure basic logging if not already configured at app level
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

# Updated ResearchAssistantResponse model to align with wrapper's output dict
class ResearchAssistantResponse(BaseModel):
    session_id: str
    summary: str
    details: list[str] = Field(default_factory=list)
    status: str
    # Fields from ResearchReport via the wrapper
    title: str = None # From ResearchReport.title
    outline: list[str] = Field(default_factory=list) # From ResearchReport.outline
    full_report_content: str = None # From ResearchReport.report (renamed in wrapper)
    sources: list[str] = Field(default_factory=list) # From ResearchReport.sources
    word_count: int = None # From ResearchReport.word_count
    collected_facts: list[dict] = Field(default_factory=list) # From ResearchReport.collected_facts
    error_message: str = None # From ResearchReport.error_message

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

# Corrected event_generator and SSE route from previous steps (maintaining agent_type)
async def event_generator(session_id: str, agent_type: str):
    logger.info(f"SSE connection established for session_id: {session_id}, agent_type: {agent_type}")
    yield f"data: Agent ({agent_type} - {session_id}): Initializing...

"
    await asyncio.sleep(1)
    yield f"data: Agent ({agent_type} - {session_id}): Configuration loading.

"
    await asyncio.sleep(1)
    yield f"data: Agent ({agent_type} - {session_id}): Resources allocation pending.

"
    await asyncio.sleep(2)
    yield f"data: Agent ({agent_type} - {session_id}): All systems nominal. Ready.

"
    await asyncio.sleep(1)
    yield f"data: Agent ({agent_type} - {session_id}): Monitoring activity... (Placeholder for actual work)

"
    logger.info(f"SSE stream placeholder work done for session_id: {session_id}, agent_type: {agent_type}")

@app.get("/api/agent/status/{agent_type}/{session_id}")
async def agent_status_sse(request: Request, agent_type: str, session_id: str):
    return StreamingResponse(event_generator(session_id, agent_type), media_type="text/event-stream")

# Updated Research Assistant Endpoint
@app.post("/api/agent/research_assistant/invoke", response_model=ResearchAssistantResponse)
async def invoke_research_assistant(request_data: ResearchTaskRequest):
    run_id = str(uuid.uuid4()) # Generate a unique ID for this research run
    logger.info(f"[{run_id}] Received research task via API: '{request_data.task_description}'")

    research_result_dict = await execute_openai_research(
        topic=request_data.task_description,
        run_id=run_id
    )

    try:
        # Pydantic will automatically pick fields from research_result_dict
        # that are defined in ResearchAssistantResponse. Extra fields will be ignored if not defined in the model.
        response_obj = ResearchAssistantResponse(**research_result_dict)
    except Exception as e:
        logger.error(f"[{run_id}] Error creating ResearchAssistantResponse Pydantic model from research_result_dict: {e}", exc_info=True)
        logger.error(f"[{run_id}] research_result_dict was: {research_result_dict}")
        # Fallback response if Pydantic model creation fails
        return ResearchAssistantResponse(
            session_id=run_id,
            summary="Internal Server Error: Failed to parse research results.",
            details=[f"Pydantic validation error: {str(e)}"],
            status="error_internal_parsing",
            error_message=f"Pydantic model creation error from dict: {str(e)}"
        )

    logger.info(f"[{run_id}] Successfully processed research task. Status: {response_obj.status}")
    return response_obj

# --- Main execution block ---
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv() # Load .env file for local development (e.g., OPENAI_API_KEY)
    logger.info("Starting Uvicorn server for main app with .env loaded.")
    uvicorn.run("app.main:app", app=None, host="0.0.0.0", port=8000, reload=True, use_colors=True) # Changed to string for reload

EOL

echo "Step 5: Updated FastAPI endpoint /api/agent/research_assistant/invoke in app/main.py."
echo "The endpoint now calls the execute_openai_research wrapper."
echo "ResearchAssistantResponse Pydantic model has been extended to match wrapper output."
echo "Added load_dotenv() to __main__ block for local development and corrected SSE endpoints."
# cat app/main.py # Optionally view file
