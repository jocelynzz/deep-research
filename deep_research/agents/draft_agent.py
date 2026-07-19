#***********************************************
#      Filename: draft_agent.py
#   Description: Generate a draft report based on the user's request
#***********************************************


"""This file's purpose is to clarify the user's question and generate a research brief.
  It contains the following 3 modules:
  1. User question clarification: determine whether a follow-up question is necessary
  2. Outline definition: generate a research brief based on the question
  3. Report draft: generate a preliminary draft of the report
"""

import logging
from typing_extensions import Literal
from rich.markdown import Markdown
from rich.console import Console

from langchain_core.messages import HumanMessage, get_buffer_string
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command

from deep_research.llm import get_chat_model
from deep_research.prompts import RESEARCH_BRIEF_PROMPT, DRAFT_REPORT_PROMPT
from deep_research.states import AgentState, ResearchBrief, AgentInputState, DraftReport
from deep_research.utils import get_today_str

logger = logging.getLogger(__name__)

draft_model = get_chat_model("draft")

# ===== Langgraph nodes =====

def write_research_brief(state: AgentState) -> Command[Literal["write_draft_report"]]:
    """Generate a research outline based on the user's query, covering which aspects need to be investigated, points to note, etc."""
    # get all messages between the agent and the user
    logger.debug("write_research_brief invoked with %d messages", len(state.get("messages", [])))
    # Generate Messages, and send it to the supervisor
    prompt = RESEARCH_BRIEF_PROMPT.format(
        messages=get_buffer_string(state.get("messages", [])),
        date=get_today_str()
    )
    logger.debug("write_research_brief invoking structured_output_model with prompt_length=%d", len(prompt))
    # the model returns JSON like {"research_brief": "Research the latest NVIDIA GPUs, covering..."}.
    structured_output_model = draft_model.with_structured_output(ResearchBrief)
    response = structured_output_model.invoke([HumanMessage(content=prompt)])
    logger.debug("write_research_brief produced research_brief length=%d", len(response.research_brief))
    # Command is a LangGraph type that lets a node do two things in one return value: update the state and decide where the graph goes next
    return Command(
        goto="write_draft_report",
        update={"research_brief": response.research_brief} # defined in AgentState
    )

def write_draft_report(state: AgentState) -> Command[Literal["__end__"]]:
    """Generate a draft research report from the research brief"""

    logger.debug(
        "write_draft_report invoked with research_brief present=%s",
        bool(state.get("research_brief")),
    )

    research_brief = state.get("research_brief", "")
    draft_report_prompt = DRAFT_REPORT_PROMPT.format(
        research_brief=research_brief,
        date=get_today_str()
    )

    structured_output_model = draft_model.with_structured_output(DraftReport)
    response = structured_output_model.invoke([HumanMessage(content=draft_report_prompt)])
    logger.debug("write_draft_report produced draft_report length=%d", len(response.draft_report))

    return {
        "research_brief": research_brief,
        "draft_report": response.draft_report,
        "supervisor_messages": ["Here is the draft report: " + response.draft_report, research_brief]
    }


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    # Build raph
    deep_researcher_builder = StateGraph(AgentState, input_schema=AgentInputState)

    # Add notes
    deep_researcher_builder.add_node("write_research_brief", write_research_brief)
    deep_researcher_builder.add_node("write_draft_report", write_draft_report)

    # Add edges
    deep_researcher_builder.add_edge(START, "write_research_brief")
    deep_researcher_builder.add_edge("write_research_brief", "write_draft_report")
    deep_researcher_builder.add_edge("write_draft_report", END)

    draft_agent = deep_researcher_builder.compile()

    print(draft_agent.get_graph().draw_ascii())

    # Test
    thread = {"configurable": {"thread_id": "1", "recursion_limit": 50}}
    result = draft_agent.invoke({"messages": [HumanMessage(content="Can you write me a research report of Google TPU in English")]}, config=thread)

    # Output
    console = Console()
    print("=====  Research Brief ====")
    console.print(Markdown(result["research_brief"]))
    print()

    print("=====  Draft Report ====")
    console.print(Markdown(result["draft_report"]))

