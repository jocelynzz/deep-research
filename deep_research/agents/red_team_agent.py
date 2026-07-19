#***********************************************
#      Filename: red_team_agent.py
#   Description: Red Team agent
#***********************************************

import logging

from langchain_core.messages import SystemMessage, HumanMessage

from deep_research.prompts import RED_TEAM_PROMPT
from deep_research.llm import get_chat_model
from deep_research.states import SupervisorState, Critique

logger = logging.getLogger(__name__)


# Initialize the model
red_team_model = get_chat_model("red_team")

# CONSTANTS
MAX_CRITIC = 3           # Maximum number of red-team critiques, to prevent an endless loop chasing perfection
MIN_DRAFT_LEN = 50       # Drafts shorter than 50 characters are not judged; return immediately
MIN_CRITIC = 20          # If the red-team output is very short, treat it as "no defects found" (guards against the model outputting something other than exactly "PASS" due to imperfect instruction following)


async def red_team_node(state: SupervisorState) -> dict:
    """
    A red-team adversarial agent that finds logical flaws, gaps, and weaknesses in the report.
    """

    draft = state.get("draft_report", "")
    research_brief = state.get("research_brief", "")
    critique_nums = state.get("critique_nums", 0)

    # Enforce the maximum number of adversarial rounds
    if critique_nums >= MAX_CRITIC or not draft or len(draft) < MIN_DRAFT_LEN:
        return {}

    # Assemble the prompt
    prompt = RED_TEAM_PROMPT.format(research_brief=research_brief, draft_report=draft)

    # Call the red-team model to get adversarial feedback
    response = await red_team_model.ainvoke([HumanMessage(content=prompt)])
    content = response.content

    # If "PASS", return immediately
    if "PASS" in content or len(content) < MIN_CRITIC:
        return {}

    # Defects were found in the report; return a critique
    critique = Critique(
        author="Red Team Adversary",
        concern=content,
        addressed=False
    )
    logger.info(f"[RED TEAM] {content}")

    # Return active_critiques for dynamic context injection, and inject the feedback
    # into the Supervisor's message history as a System Message
    return {
        "active_critiques": [critique],
        "critique_nums": critique_nums + 1,
        "supervisor_messages": [
            SystemMessage(content=f"ADVERSARIAL FEEDBACK DETECTED: {content}")
        ]
    }
