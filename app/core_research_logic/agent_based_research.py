import os
import uuid  # Keep for potential future use
from datetime import datetime
import logging
from pydantic import BaseModel, Field

# Removed pydantic import from here, will be added after all std lib imports

# Configure basic logging - ensure this is done only once if multiple modules import it
# A common pattern is to get logger by name and let application entry point configure root logger.
logger = logging.getLogger(__name__)
if not logging.getLogger().hasHandlers():  # Check root logger
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
    )

# Correct Pydantic import location will be handled by the next step,
# ensuring it's after standard library imports and before other code.
# For now, just ensuring the problematic duplicate is managed.
# The logic below will re-add a single correct Pydantic import.

try:
    from agents import (
        Agent,
        Runner,
        WebSearchTool,
        function_tool,
        handoff,
        trace,
    )

    AGENTS_AVAILABLE = True
    logger.info("'agents' module successfully imported.")
except ImportError as e:
    AGENTS_AVAILABLE = False
    logger.error(
        f"Critical: 'agents' module not found. Error: {e}. Please ensure 'openai-agents' is installed for full functionality."
    )
    # This will halt execution if the module is critical at import time.
    raise ImportError(
        "Core 'agents' module (openai-agents) not found. Please install the required dependencies."
    ) from e


class ResearchPlan(BaseModel):
    topic: str
    search_queries: list[str]
    focus_areas: list[str]

    model_config = {"extra": "forbid"}


class ResearchReport(BaseModel):
    title: str
    outline: list[str]
    report: str
    sources: list[str]
    word_count: int
    error_message: str = None
    collected_facts: list[dict] = []

    model_config = {"extra": "forbid"}


class SaveFactToolContext(BaseModel):
    collected_facts_list: list = Field(default_factory=list)

    model_config = {"extra": "forbid"}


@function_tool
async def save_important_fact(
    fact: str, source: str = None, context: dict = None
) -> str:
    if context is None or not isinstance(context, SaveFactToolContext):
        logger.warning(
            "'context' with 'collected_facts_list' not provided to save_important_fact. Fact not saved."
        )
        return "Fact received, but no context or list provided to save it."

    collected_facts_list = context.collected_facts_list
    fact_data = {
        "fact": fact,
        "source": source or "Not specified",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }  # Closed brace

    if isinstance(context.collected_facts_list, list):  # Corrected check
        collected_facts_list.append(fact_data)
        logger.info(f"Fact saved: '{fact}' (Source: {source or 'N/A'})")
        return f"Fact saved: {fact}"
    else:
        # This case should ideally not be reached if context is validated as SaveFactToolContext
        # and SaveFactToolContext ensures collected_facts_list is a list.
        # However, as a safeguard on the list attribute itself:
        logger.error(
            f"Failed to save fact: 'collected_facts_list' attribute in context is not a list. Type: {type(context.collected_facts_list)}"
        )
        return "Failed to save fact: 'collected_facts_list' attribute in context is not a list."


research_agent_tools_list = []
if AGENTS_AVAILABLE:  # Only try to instantiate tools if SDK is available
    research_agent_tools_list = [WebSearchTool(), save_important_fact]

research_agent = (
    Agent(
        name="Research Agent",
        instructions=(
            "You are a research assistant. Given a search term, you search the web "
            "for that term and produce a concise summary of the results. The summary "
            "must be 2-3 paragraphs and less than 300 words. Capture the main points. "
            "Write succintly, no need to have complete sentences or good "  # Further broken
            "grammar. This will be consumed by someone synthesizing a report, so its "  # noqa: E501
            "vital you capture the essence and ignore any fluff. Do not include any "
            "additional commentary other than the summary itself."
        ),
        model="gpt-4o-mini",  # Ensure OPENAI_API_KEY is set in environment
        tools=research_agent_tools_list,
    )
    if AGENTS_AVAILABLE
    else None
)  # Correct conditional assignment

editor_agent = (
    Agent(
        name="Editor Agent",
        handoff_description="A senior researcher who writes comprehensive research reports",
        instructions=(
            "You are a senior researcher tasked with writing a cohesive report for a research query. "
            "You will be provided with the original query, and some initial research done by a research "
            "assistant (including collected facts).\n"  # Explicit newline
            "You should first come up with an outline for the report that describes the structure and "
            "flow of the report. Then, generate the report and return that as your final output.\n"
            "The final output should be in markdown format, and it should be lengthy and detailed. Aim "
            "for 5-10 pages of content, at least 1000 words. Incorporate the collected facts appropriately."
        ),
        model="gpt-4o-mini",
        output_type=ResearchReport,
    )
    if AGENTS_AVAILABLE
    else None
)  # Correct conditional assignment

triage_agent_handoffs = []
if AGENTS_AVAILABLE and research_agent and editor_agent:  # Ensure agents are defined
    triage_agent_handoffs = [handoff(research_agent), handoff(editor_agent)]

triage_agent = (
    Agent(
        name="Triage Agent",
        instructions=(
            "You are the coordinator of this research operation. Your job is to:\n"
            "    1. Understand the user's research topic\n"
            "    2. Create a research plan with the following elements:\n"
            "       - topic: A clear statement of the research topic\n"
            "       - search_queries: A list of 3-5 specific search queries that will help gather information\n"
            "       - focus_areas: A list of 3-5 key aspects of the topic to investigate\n"
            "    3. Hand off to the Research Agent to collect information. The Research Agent will use tools, including one to save important facts.\n"
            "    4. After research is complete, hand off to the Editor Agent who will write a comprehensive report using the research and collected facts.\n\n"
            "Make sure to return your plan in the expected structured format with topic, search_queries, and focus_areas."
        ),
        model="gpt-4o-mini",  # Added model back
        handoffs=triage_agent_handoffs,
        output_type=ResearchPlan,
    )
    if AGENTS_AVAILABLE
    else None
)  # Correct conditional assignment


async def run_research(topic: str, trace_group_id: str = None) -> ResearchReport:
    run_id = trace_group_id or str(uuid.uuid4())
    logger.info(f"Starting research for topic: '{topic}' (Run ID: {run_id})")

    if (
        not AGENTS_AVAILABLE
        or not research_agent
        or not editor_agent
        or not triage_agent
    ):
        logger.error(  # Corrected logger call
            f"[{run_id}] Core agents are not available (AGENTS_AVAILABLE={AGENTS_AVAILABLE}). Cannot run research."
        )
        return ResearchReport(
            title=f"Agent Initialization Error for topic '{topic}'",
            report="Core research agents could not be initialized. Check 'openai-agents' installation.",
            error_message="Core agents not available.",
            outline=[],
            sources=[],
            word_count=0,
            collected_facts=[],
        )  # Added closing parenthesis

    if not os.getenv("OPENAI_API_KEY"):
        logger.error(f"[{run_id}] OPENAI_API_KEY environment variable is not set.")
        return ResearchReport(  # Corrected return
            title=f"Config Error for topic '{topic[:50]}{'...' if len(topic) > 50 else ''}'",  # noqa: E501
            report="OPENAI_API_KEY is not set.",  # noqa: E501
            error_message="OPENAI_API_KEY is not set.",
            outline=[],
            sources=[],
            word_count=0,
            collected_facts=[],
        )

    current_run_collected_facts = []
    tool_context = SaveFactToolContext(collected_facts_list=current_run_collected_facts)
    final_report_obj: ResearchReport = None
    trace_cm = None
    if "trace" in globals():  # Check if trace was successfully imported
        try:
            trace_cm = trace("Research Operation", group_id=run_id)
        except Exception as e:
            logger.warning(
                f"[{run_id}] Failed to initialize 'trace' context manager: {e}. Proceeding without it."
            )

    async def research_workflow():
        nonlocal final_report_obj  # Allow modification of outer scope variable
        logger.info(f"[{run_id}] Triage Agent: Planning research approach...")
        try:  # Added try for the whole workflow
            triage_result = await Runner.run(
                triage_agent,
                f"Research this topic thoroughly: {topic}. This research will be used to create a comprehensive research report.",
                context=tool_context,  # Assuming Runner.run or tools can access this context
            )  # Added closing parenthesis

            if not hasattr(triage_result, "final_output") or not isinstance(
                triage_result.final_output, ResearchPlan
            ):
                logger.error(
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
                )  # Added closing parenthesis
                return  # Exit workflow if plan is invalid

            research_plan = triage_result.final_output
            plan_dict_str = str(research_plan.dict(exclude_none=True))
            # Limit the length of what's logged for the plan if it's very long
            if len(plan_dict_str) > 200:  # Max 200 chars for log
                topic_log = (
                    research_plan.topic[:50] + "..."
                    if len(research_plan.topic) > 50
                    else research_plan.topic
                )
                queries_log = (
                    str(research_plan.search_queries[:1]) + "..."
                    if research_plan.search_queries
                    else "[]"
                )
                focus_log = (
                    str(research_plan.focus_areas[:1]) + "..."
                    if research_plan.focus_areas
                    else "[]"
                )
                plan_display_log = f"Topic='{topic_log}', Queries='{queries_log}', Focus='{focus_log}' (details omitted)"
            else:
                plan_display_log = plan_dict_str
            logger.info(
                f"[{run_id}] Research Plan generated: {plan_display_log}"  # noqa: E501
            )
            # Extract final report from the agent chain's history or final output
            if triage_result and hasattr(triage_result, "history"):
                editor_output_found = False
                for item in reversed(triage_result.history):
                    if (
                        hasattr(item, "agent_name")
                        and item.agent_name == "Editor Agent"
                        and hasattr(item, "output")
                        and isinstance(item.output, ResearchReport)
                    ):
                        final_report_obj = item.output
                        editor_output_found = True
                        logger.info(
                            f"[{run_id}] Editor Agent output successfully retrieved from history."
                        )
                        break
                if not editor_output_found and isinstance(
                    triage_result.final_output, ResearchReport
                ):
                    final_report_obj = triage_result.final_output
                    logger.info(
                        f"[{run_id}] Editor Agent output retrieved as final output of the chain."
                    )
                elif not editor_output_found:
                    logger.warning(
                        f"[{run_id}] Could not find ResearchReport from Editor Agent in history or final output."
                    )  # Added closing parenthesis
                    final_report_obj = ResearchReport(
                        title=f"Report Generation Incomplete for {topic}",
                        outline=[],
                        report="Editor agent did not produce a final report in the expected format.",
                        sources=[],
                        word_count=0,
                        error_message="Editor report not found.",
                        collected_facts=current_run_collected_facts,
                    )  # Added closing parenthesis
            else:
                logger.warning(
                    f"[{run_id}] Triage result has no history or unexpected structure."
                )  # Added closing parenthesis
                final_report_obj = ResearchReport(  # Added assignment
                    title=f"Processing Error for {topic}",
                    outline=[],  # Added outline
                    report="Could not determine final report due to processing error.",
                    sources=[],  # Added sources
                    word_count=0,  # Added word_count
                    error_message="Triage result processing error.",
                    collected_facts=current_run_collected_facts,  # Added collected_facts
                )  # Added closing parenthesis
            logger.info(f"[{run_id}] Research workflow complete for topic: '{topic}'.")
        except Exception as e:  # Catch exceptions from the workflow
            logger.error(
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
            )  # Added closing parenthesis

    if trace_cm:
        with trace_cm:
            await research_workflow()
    else:  # Corrected else indentation
        await research_workflow()

    if final_report_obj:
        # Ensure the collected facts from this run are on the final report object
        final_report_obj.collected_facts = current_run_collected_facts
    else:  # Should ideally not be reached if research_workflow always assigns
        final_report_obj = ResearchReport(
            title=f"Critical Error for {topic}",
            report="No report object was generated due to a critical failure.",
            outline=[],
            sources=[],
            word_count=0,  # Added outline, sources, word_count
            error_message="Critical: No report object generated.",
            collected_facts=current_run_collected_facts,
        )  # Added closing parenthesis
    return final_report_obj
