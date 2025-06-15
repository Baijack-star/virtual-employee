import os
import uuid
import logging
# import functools # Not strictly needed in this corrected version unless used elsewhere

from app.core_research_logic.agent_based_research import run_research, ResearchReport, AGENTS_AVAILABLE

logger = logging.getLogger(__name__)
if not logger.handlers: # Check if handlers are already configured
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')

async def execute_openai_research(topic: str, run_id: str = None) -> dict:
    if not run_id:
        run_id = str(uuid.uuid4())
    logger.info(f"[{run_id}] Attempting to execute OpenAI research for topic: '{topic}'")

    if not AGENTS_AVAILABLE:
        error_msg = "Core 'openai-agents' SDK is not available. Research functionality disabled."
        logger.critical(f"[{run_id}] {error_msg}")
        # Ensure all fields expected by ResearchAssistantResponse are present
        return {
            "session_id": run_id, "summary": "Error: Research Module Not Available",
            "details": [error_msg], "status": "error_configuration",
            "title": "Error: Module Unavailable", "outline": [], "full_report_content": error_msg,
            "sources": [], "word_count": 0, "collected_facts": [], "error_message": error_msg
        }

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key: # Explicit API key check
        error_msg = "OPENAI_API_KEY environment variable is not set."
        logger.error(f"[{run_id}] Missing OPENAI_API_KEY: {error_msg}")
        return {
            "session_id": run_id, "summary": "Configuration Error: API Key Missing",
            "details": ["OpenAI API key is missing. Please configure the environment."],
            "status": "error_configuration",
            "title": "Config Error: API Key", "outline": [], "full_report_content": error_msg,
            "sources": [], "word_count": 0, "collected_facts": [], "error_message": error_msg
        }

    try:
        logger.info(f"[{run_id}] Calling core research logic (run_research) for topic: '{topic}'")
        report_obj: ResearchReport = await run_research(topic=topic, trace_group_id=run_id)

        if not report_obj: # Should ideally not happen if run_research always returns a ResearchReport
            logger.error(f"[{run_id}] Core research logic returned a None object, which is unexpected.")
            error_msg = "Internal error: No report object received from core research logic."
            return {
                "session_id": run_id, "summary": "Error: No Report Generated",
                "details": [error_msg], "status": "error_internal",
                "title": "Internal Error: No Report", "outline": [], "full_report_content": error_msg,
                "sources": [], "word_count": 0, "collected_facts": [], "error_message": error_msg
            }

        logger.info(f"[{run_id}] Research logic completed. Report title: '{report_obj.title}'. Error: {report_obj.error_message or 'None'}")

        # Constructing the response summary
        response_summary = report_obj.title if report_obj.title else "Research Task Processed"

        if report_obj.error_message:
            response_summary = f"Error in Research: {report_obj.title or topic}"
        elif report_obj.report: # If no error and report exists, append snippet
            # Corrected string replacement and concatenation:
            report_snippet = report_obj.report[:150].replace('\n', ' ').strip()
            response_summary += f" - {report_snippet}..." if report_snippet else ""


        response_details = []
        if report_obj.outline:
            response_details.append(f"Outline: {', '.join(report_obj.outline)}")

        if report_obj.collected_facts and not report_obj.error_message:
            response_details.append("Key Facts Found:")
            for fact in report_obj.collected_facts[:3]: # Show first 3 facts
                response_details.append(f"- {fact.get('fact')} (Source: {fact.get('source', 'N/A')})")

        if not response_details and report_obj.report and not report_obj.error_message:
             response_details.append("Report generated (see full report for content).")
        elif not response_details and report_obj.error_message:
            response_details.append(f"Details of error: {report_obj.error_message}")
        elif not response_details: # Fallback if no other details were added
            response_details.append("No specific details to summarize here.")

        return {
            "session_id": run_id,
            "summary": response_summary,
            "details": response_details,
            "status": "completed" if not report_obj.error_message else "error_processing",
            "title": report_obj.title,
            "outline": report_obj.outline,
            "full_report_content": report_obj.report, # Changed from 'report' to 'full_report_content'
            "sources": report_obj.sources,
            "word_count": report_obj.word_count,
            "collected_facts": report_obj.collected_facts,
            "error_message": report_obj.error_message
        }

    except ImportError as e: # Should be caught by AGENTS_AVAILABLE, but as a safeguard
        error_msg = f"Missing critical component for research during execution: {e}."
        logger.critical(f"[{run_id}] {error_msg}", exc_info=True)
        return {
            "session_id": run_id, "summary": "Error: Critical Component Missing at Runtime",
            "details": [error_msg], "status": "error_configuration",
            "title": "Runtime Configuration Error", "outline": [], "full_report_content": error_msg,
            "sources": [], "word_count": 0, "collected_facts": [], "error_message": error_msg
        }
    except Exception as e:
        logger.error(f"[{run_id}] Unhandled exception in execute_openai_research: {e}", exc_info=True)
        error_msg = f"An unexpected error occurred during research: {str(e)}"
        return {
            "session_id": run_id, "summary": "Critical Error During Research Execution",
            "details": [error_msg], "status": "error_uncaught_exception",
            "title": "Uncaught Exception During Execution", "outline": [], "full_report_content": error_msg,
            "sources": [], "word_count": 0, "collected_facts": [], "error_message": error_msg
        }
