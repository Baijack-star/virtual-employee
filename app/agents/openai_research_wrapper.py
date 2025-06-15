import os
import uuid
import logging
import functools  # For functools.partial

# Assuming ResearchReport and run_research are in the specified path
# and ResearchReport is the Pydantic model defined there.
from app.core_research_logic.agent_based_research import (
    run_research,
    ResearchReport,
    AGENTS_AVAILABLE,
)

# Removed ResearchPlan, research_agent, save_important_fact, WebSearchTool imports as they are not directly used in this wrapper
# but are used within run_research. AGENTS_AVAILABLE is used.

logger = logging.getLogger(__name__)
# Ensure logger is configured if not configured at app level
# BasicConfig should ideally be at the application entry point (main.py)
# This check is a fallback.
if not logger.handlers:  # Check if handlers are already configured
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
    )


async def execute_openai_research(topic: str, run_id: str = None) -> dict:
    """
    Wrapper function to execute the OpenAI-based research agent.
    Handles API key management, calls the core research logic, and formats the output.
    Returns a dictionary that should be compatible with the ResearchAssistantResponse Pydantic model.
    """
    if not run_id:
        run_id = str(uuid.uuid4())

    logger.info(
        f"[{run_id}] Attempting to execute OpenAI research for topic: '{topic}'"
    )

    if (
        not AGENTS_AVAILABLE
    ):  # Check if the core 'agents' module was imported successfully
        error_msg = "Core 'openai-agents' SDK is not available. Research functionality disabled."
        logger.critical(f"[{run_id}] {error_msg}")
        return {
            "session_id": run_id,
            "summary": "Error: Research Module Not Available",
            "details": [error_msg],
            "status": "error_configuration",
            "title": "Error",  # Added to match ResearchReport structure more closely for Pydantic conversion
            "outline": [],
            "report": error_msg,
            "sources": [],
            "word_count": 0,
            "collected_facts": [],
            "error_message": error_msg,
        }

    # API key check is handled within run_research in core_research_logic for this iteration
    # as per its current design. If OPENAI_API_KEY is not set, run_research returns a specific ResearchReport.
    # This wrapper could also check it here if we want to prevent calling run_research at all.
    # For now, let run_research handle it as it's already implemented there.

    try:
        logger.info(
            f"[{run_id}] Calling core research logic (run_research) for topic: '{topic}'"
        )
        # run_research is expected to return a ResearchReport Pydantic model instance
        report_obj: ResearchReport = await run_research(
            topic=topic, trace_group_id=run_id
        )

        if (
            not report_obj
        ):  # Should not happen if run_research always returns a ResearchReport
            logger.error(
                f"[{run_id}] Core research logic returned a None object, which is unexpected."
            )
            error_msg = (
                "Internal error: No report object received from core research logic."
            )
            return {
                "session_id": run_id,
                "summary": "Error: No Report Generated",
                "details": [error_msg],
                "status": "error_internal",
                "title": "Internal Error",
                "outline": [],
                "report": error_msg,
                "sources": [],
                "word_count": 0,
                "collected_facts": [],
                "error_message": error_msg,
            }

        logger.info(
            f"[{run_id}] Research logic completed. Report title: '{report_obj.title}'. Error: {report_obj.error_message or 'None'}"
        )

        # Map ResearchReport to the dictionary structure for ResearchAssistantResponse (FastAPI model)
        # ResearchAssistantResponse in main.py expects: session_id, summary, details, status.
        # We also add other fields from ResearchReport for potential use or if the Pydantic model is expanded.

        response_summary = (
            report_obj.title if report_obj.title else "Research Task Processed"
        )
        if report_obj.error_message:
            response_summary = f"Error in Research: {report_obj.title or topic}"
        elif (
            report_obj.report
        ):  # Add a snippet of the report to the summary if no error
            response_summary += (
                " - " + report_obj.report[:150].replace("\n", " ") + "..."
            )

        response_details = []
        if report_obj.outline:  # Outline might be empty in case of error
            response_details.append(f"Outline: {', '.join(report_obj.outline)}")

        # Add some collected facts to details if available, and no major error
        if report_obj.collected_facts and not report_obj.error_message:
            response_details.append("Key Facts Found:")
            for fact in report_obj.collected_facts[
                :3
            ]:  # Show first 3 facts as part of details
                response_details.append(
                    f"- {fact.get('fact')} (Source: {fact.get('source', 'N/A')})"
                )

        if not response_details and report_obj.report and not report_obj.error_message:
            response_details.append("Report generated (see full report for content).")
        elif not response_details and report_obj.error_message:
            response_details.append(f"Details of error: {report_obj.error_message}")
        elif not response_details:
            response_details.append(
                "No specific details to summarize here, check full report or error message."
            )

        return {
            "session_id": run_id,
            "summary": response_summary,
            "details": response_details,
            "status": (
                "completed" if not report_obj.error_message else "error_processing"
            ),
            # Pass through all fields from ResearchReport.
            # The Pydantic model in main.py (ResearchAssistantResponse) will pick what it needs.
            # If ResearchAssistantResponse is defined as  (or inherits), this is direct.
            # If it's a different model, only matching fields will be used.
            # Current main.py's ResearchAssistantResponse is: session_id, summary, details, status.
            # So, we are providing more data than it strictly consumes, which is fine.
            # For direct use of ResearchReport as the response model, this would be .
            "title": report_obj.title,
            "outline": report_obj.outline,
            "full_report_content": report_obj.report,  # Renamed to avoid conflict if 'report' is a method
            "sources": report_obj.sources,
            "word_count": report_obj.word_count,
            "collected_facts": report_obj.collected_facts,
            "error_message": report_obj.error_message,
        }

    except (
        ImportError
    ) as e:  # Catch potential ImportErrors if AGENTS_AVAILABLE was True but something specific failed later
        error_msg = f"Missing critical component for research: {e}. Research functionality may be impaired."
        logger.critical(f"[{run_id}] {error_msg}", exc_info=True)
        # Return structure consistent with other errors
        return {
            "session_id": run_id,
            "summary": "Error: Critical Component Missing",
            "details": [error_msg],
            "status": "error_configuration",
            "title": "Configuration Error",
            "outline": [],
            "report": error_msg,
            "sources": [],
            "word_count": 0,
            "collected_facts": [],
            "error_message": error_msg,
        }
    except Exception as e:
        logger.error(
            f"[{run_id}] Unhandled exception in execute_openai_research: {e}",
            exc_info=True,
        )
        error_msg = f"An unexpected error occurred during research: {str(e)}"
        return {
            "session_id": run_id,
            "summary": "Critical Error During Research",
            "details": [error_msg],
            "status": "error_uncaught_exception",
            "title": "Uncaught Exception",
            "outline": [],
            "report": error_msg,
            "sources": [],
            "word_count": 0,
            "collected_facts": [],
            "error_message": error_msg,
        }
