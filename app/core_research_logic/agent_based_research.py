import os
import uuid  # Keep for potential future use
import asyncio
from datetime import datetime
from dotenv import load_dotenv
import logging  # Using logging instead of print for backend logic

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
)

# Attempt to import from openai_agents.
# This will be added to requirements.txt in a later step.
try:
    from agents import (
        Agent,
        Runner,
        WebSearchTool,
        function_tool,
        handoff,
        trace,  # trace might be UI specific or SDK specific, need to check its usage
    )

    AGENTS_AVAILABLE = True
    logging.info("'agents' module successfully imported.")
except ImportError as e:
    AGENTS_AVAILABLE = False
    logging.error(
        f"Critical: 'agents' module not found. Error: {e}. Please ensure 'openai-agents' is installed for full functionality."
    )
    # For a backend service, it's often better to fail fast if a core dependency is missing.
    # Re-raising helps to signal this problem clearly during startup or deployment.
    raise ImportError(
        "Core 'agents' module (openai-agents) not found. Please install the required dependencies."
    ) from e

from pydantic import BaseModel

# load_dotenv() # Best called at application entry point, e.g., in FastAPI main.py or via Docker env vars


# --- Data models ---
class ResearchPlan(BaseModel):
    topic: str
    search_queries: list[str]
    focus_areas: list[str]


class ResearchReport(BaseModel):
    title: str
    outline: list[str]
    report: str
    sources: list[str]
    word_count: int
    error_message: str = None  # Optional error field
    collected_facts: list[dict] = []  # To store facts collected during research


# --- Custom tool modification ---
@function_tool
async def save_important_fact(
    fact: str, source: str = None, context: dict = None
) -> str:
    """Save an important fact discovered during research.
    Appends to 'collected_facts_list' within the provided 'context' dictionary.
    """
    if context is None or "collected_facts_list" not in context:
        logging.warning(
            "'context' with 'collected_facts_list' not provided to save_important_fact. Fact not saved."
        )
        return "Fact received, but no context or list provided to save it."

    collected_facts_list = context["collected_facts_list"]
    fact_data = {
        "fact": fact,
        "source": source or "Not specified",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    if isinstance(collected_facts_list, list):
        collected_facts_list.append(fact_data)
        logging.info(f"Fact saved: '{fact}' (Source: {source or 'N/A'})")
        return f"Fact saved: {fact}"
    else:
        logging.error(
            f"Failed to save fact: 'collected_facts_list' in context is not a list. Type: {type(collected_facts_list)}"
        )
        return "Failed to save fact: 'collected_facts_list' in context is not a list."


# --- Agent definitions ---
research_agent_tools_list = [WebSearchTool(), save_important_fact]

research_agent = Agent(
    name="Research Agent",
    instructions="You are a research assistant. Given a search term, you search the web for that term and "
    "produce a concise summary of the results. The summary must 2-3 paragraphs and less than 300 "
    "words. Capture the main points. Write succintly, no need to have complete sentences or good "
    "grammar. This will be consumed by someone synthesizing a report, so its vital you capture the "
    "essence and ignore any fluff. Do not include any additional commentary other than the summary "
    "itself.",
    model="gpt-4o-mini",  # Ensure OPENAI_API_KEY is set in environment
    tools=research_agent_tools_list,
)

editor_agent = Agent(
    name="Editor Agent",
    handoff_description="A senior researcher who writes comprehensive research reports",
    instructions=(
        "You are a senior researcher tasked with writing a cohesive report for a research query. "
        "You will be provided with the original query, and some initial research done by a research "
        "assistant (including collected facts). "
        "You should first come up with an outline for the report that describes the structure and "
        "flow of the report. Then, generate the report and return that as your final output. "
        "The final output should be in markdown format, and it should be lengthy and detailed. Aim "
        "for 5-10 pages of content, at least 1000 words. Incorporate the collected facts appropriately."
    ),
    model="gpt-4o-mini",
    output_type=ResearchReport,
)

triage_agent = Agent(
    name="Triage Agent",
    instructions="""You are the coordinator of this research operation. Your job is to:
    1. Understand the user's research topic
    2. Create a research plan with the following elements:
       - topic: A clear statement of the research topic
       - search_queries: A list of 3-5 specific search queries that will help gather information
       - focus_areas: A list of 3-5 key aspects of the topic to investigate
    3. Hand off to the Research Agent to collect information. The Research Agent will use tools, including one to save important facts.
    4. After research is complete, hand off to the Editor Agent who will write a comprehensive report using the research and collected facts.

    Make sure to return your plan in the expected structured format with topic, search_queries, and focus_areas.
    """,
    handoffs=[handoff(research_agent), handoff(editor_agent)],
    model="gpt-4o-mini",
    output_type=ResearchPlan,
)


# --- Main research function (modified) ---
async def run_research(topic: str, trace_group_id: str = None) -> ResearchReport:
    """
    Main research function, adapted for backend use.
    Facts are collected into a list specific to this run, passed via context to tools.
    `trace_group_id` is an optional ID for tracing/logging.
    """
    run_id = trace_group_id or str(uuid.uuid4())
    logging.info(f"Starting research for topic: '{topic}' (Run ID: {run_id})")

    # Ensure OPENAI_API_KEY is available
    if not os.getenv("OPENAI_API_KEY"):
        logging.error(f"[{run_id}] OPENAI_API_KEY environment variable is not set.")
        return ResearchReport(
            title=f"Configuration Error for topic '{topic}'",
            report="OPENAI_API_KEY is not set.",
            error_message="OPENAI_API_KEY is not set.",
            outline=[],
            sources=[],
            word_count=0,
        )

    # List to store facts collected during this specific research run
    current_run_collected_facts = []

    # Context to be passed to the Runner, making collected_facts_list available to tools
    # The exact mechanism for tools to access this context depends on the 'openai-agents' SDK.
    # Assuming Runner or Agent can take a 'context' dict that tools can access.
    # If the SDK's `function_tool` decorator or `Runner.run` supports passing such context,
    # `save_important_fact` will use it.
    tool_context = {"collected_facts_list": current_run_collected_facts}

    final_report_obj: ResearchReport = None

    # The 'trace' context manager from 'openai-agents' SDK.
    # If it's not suitable for backend (e.g., writes to files unexpectedly),
    # it should be replaced with custom logging or another tracing solution.
    trace_cm = None
    if AGENTS_AVAILABLE and "trace" in globals():
        try:
            trace_cm = trace("Research Operation", group_id=run_id)
        except Exception as e:
            logging.warning(
                f"[{run_id}] Failed to initialize 'trace' context manager: {e}. Proceeding without it."
            )

    async def research_workflow():
        nonlocal final_report_obj  # Allow modification of outer scope variable
        logging.info(f"[{run_id}] Triage Agent: Planning research approach...")

        try:
            # The critical part is how `tool_context` (containing `current_run_collected_facts`)
            # is made available to `save_important_fact` when it's executed by the `research_agent`.
            # This might involve:
            # 1. Runner.run(..., tool_context=tool_context) if the SDK supports it.
            # 2. research_agent.with_tool_context(tool_context) if agents can be configured per run.
            # 3. Modifying tools list for research_agent dynamically (e.g., using functools.partial).
            # This step assumes the SDK has a mechanism. If not, Step 4 (wrapper) must address this.

            triage_result = await Runner.run(
                triage_agent,
                f"Research this topic thoroughly: {topic}. This research will be used to create a comprehensive research report.",
                # If Runner.run supports a context argument for tools:
                context=tool_context,  # This is an assumption about openai-agents SDK
            )

            if not hasattr(triage_result, "final_output") or not isinstance(
                triage_result.final_output, ResearchPlan
            ):
                logging.error(
                    f"[{run_id}] Triage agent did not return a valid ResearchPlan. Output: {triage_result.final_output}"
                )
                final_report_obj = ResearchReport(
                    title=f"Triage Error for {topic}",
                    outline=[],
                    report="Triage agent output was not a valid ResearchPlan.",
                    sources=[],
                    word_count=0,
                    error_message="Triage agent output was not a valid ResearchPlan.",
                    collected_facts=current_run_collected_facts,
                )
                return

            research_plan = triage_result.final_output
            logging.info(
                f"[{run_id}] Research Plan generated: {research_plan.dict(exclude_none=True)}"
            )

            # After triage_agent (which includes handoffs to research_agent and editor_agent) runs,
            # the final output should ideally be from the editor_agent.
            # We need to correctly extract the ResearchReport from the execution history or final output.
            if triage_result and hasattr(triage_result, "history"):
                editor_output_found = False
                for item in reversed(triage_result.history):  # Check from the end
                    if (
                        hasattr(item, "agent_name")
                        and item.agent_name == "Editor Agent"
                        and hasattr(item, "output")
                        and isinstance(item.output, ResearchReport)
                    ):
                        final_report_obj = item.output
                        editor_output_found = True
                        logging.info(
                            f"[{run_id}] Editor Agent output successfully retrieved from history."
                        )
                        break
                if not editor_output_found and isinstance(
                    triage_result.final_output, ResearchReport
                ):
                    # If not found in history, check if the chain's final output is the report
                    final_report_obj = triage_result.final_output
                    logging.info(
                        f"[{run_id}] Editor Agent output retrieved as final output of the chain."
                    )
                elif not editor_output_found:
                    logging.warning(
                        f"[{run_id}] Could not find ResearchReport from Editor Agent in history or final output."
                    )
                    final_report_obj = ResearchReport(
                        title=f"Report Generation Incomplete for {topic}",
                        outline=[],
                        report="Editor agent did not produce a final report in the expected format.",
                        sources=[],
                        word_count=0,
                        error_message="Editor report not found.",
                        collected_facts=current_run_collected_facts,
                    )
            else:  # Fallback if no history or unexpected triage_result structure
                logging.warning(
                    f"[{run_id}] Triage result has no history or unexpected structure."
                )
                final_report_obj = ResearchReport(
                    title=f"Processing Error for {topic}",
                    outline=[],
                    report="Could not determine final report due to processing error.",
                    sources=[],
                    word_count=0,
                    error_message="Triage result processing error.",
                    collected_facts=current_run_collected_facts,
                )

            logging.info(f"[{run_id}] Research workflow complete for topic: '{topic}'.")

        except Exception as e:
            logging.error(
                f"[{run_id}] Error during research workflow execution: {e}",
                exc_info=True,
            )
            final_report_obj = ResearchReport(
                title=f"Error during research for {topic}",
                outline=[],
                report=f"An unexpected error occurred: {str(e)}",
                sources=[],
                word_count=0,
                error_message=f"Workflow Error: {str(e)}",
                collected_facts=current_run_collected_facts,
            )

    if trace_cm:
        with trace_cm:
            await research_workflow()
    else:
        await research_workflow()

    # Ensure collected facts are part of the returned report object
    if final_report_obj:
        final_report_obj.collected_facts = current_run_collected_facts
    else:  # Should not happen if workflow always assigns to final_report_obj
        final_report_obj = ResearchReport(
            title=f"Critical Error for {topic}",
            report="No report object generated.",
            outline=[],
            sources=[],
            word_count=0,
            error_message="Critical: No report object generated.",
            collected_facts=current_run_collected_facts,
        )

    return final_report_obj


# Module-level test function (commented out for subtask)
# async def main_test_module():
#     load_dotenv()
#     if not os.getenv("OPENAI_API_KEY"):
#         logging.error("OPENAI_API_KEY not set. Please set it to run the test.")
#         return
#
#     test_topic = "Impact of Quantum Computing on Cybersecurity"
#     report = await run_research(test_topic, trace_group_id="test-qc-cyber-001")
#
#     logging.info(f"--- Test Report for '{test_topic}' ---")
#     if report.error_message:
#         logging.error(f"Error in report generation: {report.error_message}")
#     logging.info(f"Title: {report.title}")
#     logging.info(f"Word Count: {report.word_count}")
#     # logging.info(f"Report Preview: {report.report[:300]}...")
#     # logging.info(f"Collected Facts: {report.collected_facts}")

# if __name__ == "__main__":
#     asyncio.run(main_test_module())
