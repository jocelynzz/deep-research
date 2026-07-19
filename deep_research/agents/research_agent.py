#***********************************************
#      Filename: research_agent.py
#***********************************************

"""Research Agent
This file implements a Research Agent that performs iterative web searches and synthesis to answer complex research questions.
"""


import os
from typing_extensions import Literal
import logging
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage, filter_messages

from deep_research.llm import get_chat_model
from deep_research.states import ResearcherState, ResearcherOutputState
from deep_research.utils import get_today_str
from deep_research.tools import tavily_search_tool, think_tool
from deep_research.prompts import RESEARCH_AGENT_PROMPT, COMPRESS_RESEARCH_SYSTEM_PROMPT, COMPRESS_RESEARCH_FINAL_INSTRUCTION_PROMPT

logger = logging.getLogger(__name__)


# ===== CONFIGURATION =====

# Initialize tools
tools = [tavily_search_tool, think_tool]
tools_by_name = {tool.name: tool for tool in tools}

# Initialize models
model = get_chat_model("researcher_main")
model_with_tools = model.bind_tools(tools)
compress_model = get_chat_model("researcher_compressor")

# Hard cap across *all* tools (searches and reflections) for one delegated
# research topic. Override it per run with MAX_RESEARCH_TOOL_CALLS.
DEFAULT_MAX_RESEARCH_TOOL_CALLS = 3


def _max_research_tool_calls() -> int:
    raw_limit = os.getenv("MAX_RESEARCH_TOOL_CALLS", str(DEFAULT_MAX_RESEARCH_TOOL_CALLS))
    try:
        return max(1, int(raw_limit))
    except ValueError:
        logger.warning(
            "Invalid MAX_RESEARCH_TOOL_CALLS=%r; using default %d",
            raw_limit,
            DEFAULT_MAX_RESEARCH_TOOL_CALLS,
        )
        return DEFAULT_MAX_RESEARCH_TOOL_CALLS


# ===== AGENT NODES =====

def llm_call(state: ResearcherState):
    """Decide the next action based on the current state"""

    msg_count = len(state.get("researcher_messages", []))
    logger.debug("llm_call invoked with %d messages", msg_count)

    # Call the LLM
    response = model_with_tools.invoke(
        [SystemMessage(content=RESEARCH_AGENT_PROMPT)] + state["researcher_messages"]
    )

    logger.info(
        "llm_call produced response tool_calls=%s num_tool_calls=%d",
        bool(response.tool_calls),
        len(response.tool_calls or []),
    )
    return {
        "researcher_messages": [response]
    }

def tool_node(state: ResearcherState):
    """Execute all tool calls from the previous LLM response"""

    requested_tool_calls = state["researcher_messages"][-1].tool_calls or []
    calls_used = state.get("tool_call_iterations", 0)
    calls_remaining = max(0, _max_research_tool_calls() - calls_used)
    tool_calls = requested_tool_calls[:calls_remaining]
    logger.info(
        "tool_node executing %d of %d requested tool calls (used=%d, limit=%d)",
        len(tool_calls),
        len(requested_tool_calls),
        calls_used,
        _max_research_tool_calls(),
    )

    # Invoke the tools
    observations = []
    for tool_call in tool_calls:
        tool = tools_by_name[tool_call["name"]]
        logger.info("Invoking tool %s with args=%s", tool_call["name"], tool_call["args"])
        observations.append(tool.invoke(tool_call["args"]))

    # Collect the tool outputs. Every requested tool call needs a matching
    # ToolMessage, including calls skipped due to the budget, so the following
    # compression model receives a valid tool-call transcript.
    tool_outputs = [
        ToolMessage(
            content=observation,
            name=tool_call["name"],
            tool_call_id=tool_call["id"]
        ) for observation, tool_call in zip(observations, tool_calls)
    ]
    tool_outputs.extend(
        ToolMessage(
            content="Skipped: this research agent exhausted its tool-call budget.",
            name=tool_call["name"],
            tool_call_id=tool_call["id"],
        )
        for tool_call in requested_tool_calls[len(tool_calls):]
    )

    return {
        "researcher_messages": tool_outputs,
        "tool_call_iterations": calls_used + len(tool_calls),
    }

def compress_research(state: ResearcherState) -> dict:
    """Compress the research findings into a high-value summary, keeping only useful information."""

    # Assemble the prompt
    system_message = COMPRESS_RESEARCH_SYSTEM_PROMPT.format(date=get_today_str())
    messages = [SystemMessage(content=system_message)] + state.get("researcher_messages", []) +\
            [HumanMessage(content=COMPRESS_RESEARCH_FINAL_INSTRUCTION_PROMPT.format(research_topic=state.get("research_topic", "")))]
    logger.info("compress_research invoked with %d messages", len(messages))

    # Call the summarization model
    response = compress_model.invoke(messages)

    # Extract raw notes from the AI and tool messages
    raw_notes = [
        str(m.content) for m in filter_messages(
            state["researcher_messages"], 
            include_types=["tool", "ai"]
        )
    ]

    logger.debug("compress_research produced raw_notes_count=%d", len(raw_notes))
    return {
        "compressed_research": str(response.content),
        "raw_notes": ["\n".join(raw_notes)]
    }

# ===== ROUTING LOGIC =====

def should_continue(state: ResearcherState) -> Literal["tool_node", "compress_research"]:
    """Determine whether to continue research or provide final answer."""
    calls_used = state.get("tool_call_iterations", 0)
    if calls_used >= _max_research_tool_calls():
        logger.info(
            "should_continue decision=compress_research (tool-call budget exhausted: %d/%d)",
            calls_used,
            _max_research_tool_calls(),
        )
        return "compress_research"

    messages = state["researcher_messages"]
    last_message = messages[-1]

    decision = "tool_node" if last_message.tool_calls else "compress_research"
    logger.info("should_continue decision=%s (has_tool_calls=%s)", decision, bool(last_message.tool_calls))
    return decision


def should_continue_after_tools(state: ResearcherState) -> Literal["llm_call", "compress_research"]:
    """Stop immediately after the final allowed tool call."""
    calls_used = state.get("tool_call_iterations", 0)
    decision = "compress_research" if calls_used >= _max_research_tool_calls() else "llm_call"
    logger.info(
        "should_continue_after_tools decision=%s (used=%d, limit=%d)",
        decision,
        calls_used,
        _max_research_tool_calls(),
    )
    return decision


# ===== GRAPH CONSTRUCTION =====

# Build the agent
agent_builder = StateGraph(ResearcherState, output_schema=ResearcherOutputState)

# Add nodes to the graph
agent_builder.add_node("llm_call", llm_call)
agent_builder.add_node("tool_node", tool_node)
agent_builder.add_node("compress_research", compress_research)

# Add edges to connect nodes
agent_builder.add_edge(START, "llm_call")
agent_builder.add_conditional_edges(
    "llm_call",
    should_continue,
    {
        "tool_node": "tool_node", # Continue research loop
        "compress_research": "compress_research", # Return final answer
    },
)
agent_builder.add_conditional_edges(
    "tool_node",
    should_continue_after_tools,
    {
        "llm_call": "llm_call",
        "compress_research": "compress_research",
    },
)
agent_builder.add_edge("compress_research", END)

# Compile the agent
researcher_agent = agent_builder.compile()

if __name__ == "__main__":
    print(researcher_agent.get_graph().draw_ascii())
