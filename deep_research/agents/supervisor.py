#***********************************************
#      Filename: supervisor_agent.py
#   Description: Supervisor agent
#***********************************************

"""Supervision for coordinating multiple sub-research agents. This module implements a supervisor pattern where:
1. The Supervisor Agent coordinates research activities and assigns tasks
2. Multiple sub-research agents work on specific sub-topics independently
3. Results are aggregated and compressed for the final report
The Supervisor Agent executes sub-agents in parallel for efficiency, while keeping an independent context window for each research topic.
"""


import asyncio
import logging
from typing_extensions import Literal
from langchain_core.messages import (
    HumanMessage, 
    BaseMessage, 
    SystemMessage, 
    ToolMessage,
    filter_messages
)
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command

from deep_research.llm import get_chat_model
from deep_research.prompts import ADDRESS_CRITIQUES_PROMPT, MULTI_STEP_DENOISE_PROMPT
from deep_research.agents.research_agent import researcher_agent
from deep_research.agents.red_team_agent import red_team_node
from deep_research.agents.evaluator_agent import evaluate_draft_quality 
from deep_research.states import (
    SupervisorState, 
    ConductResearch,
    ResearchComplete,
    QualityMetric
)
from deep_research.utils import get_today_str
from deep_research.tools import think_tool, refine_draft_report_tool

logger = logging.getLogger(__name__)


def get_notes_from_tool_calls(messages: list[BaseMessage]) -> list[str]:
    """Extract research notes from ToolMessage objects in the supervisor's message history.
    When the supervisor delegates research tasks to sub-agents via ConductResearch tool calls,
    each sub-agent returns its compressed research results as ToolMessage content.
    This function extracts all such ToolMessage contents to build the merged final research notes.

    Args:
        messages: List of messages from the supervisor's conversation history

    Returns:
        List of research note strings extracted from ToolMessage objects
    """
    return [tool_msg.content for tool_msg in filter_messages(messages, include_types="tool")]



# ===== CONFIGURATION =====

supervisor_tools = [ConductResearch, ResearchComplete, think_tool, refine_draft_report_tool]
supervisor_model = get_chat_model("supervisor")
supervisor_model_with_tools = supervisor_model.bind_tools(supervisor_tools)


# System constants (max iterations / max parallel sub-agents)
max_researcher_iterations = 15 # Calls to think_tool + ConductResearch + refine_draft_report
max_concurrent_researchers = 3 # Maximum number of parallel sub-agents
min_need_repair_score = 6.0    # If the evaluation score falls below this, trigger a repair reminder to the agent


# ===== SUPERVISOR NODES =====

async def supervisor(state: "SupervisorState") -> Command[Literal["supervisor_tools"]]:
    """Analyze the research brief and current progress.
    Decides:
        - Which topics need to be researched
        - Whether to run research in parallel
        - When the research is complete

    Args:
        state: Current supervisor state, including messages and progress

    Returns:
        Command that jumps to the supervisor_tools node and updates the state
    """
    supervisor_messages = state.get("supervisor_messages", []) # get with default value, messages that the supervisor should read
    iteration = state.get("research_iterations", 0)
    logger.info("[SUPERVISOR] supervisor invoked (iteration=%d, messages=%d)", iteration, len(supervisor_messages))
 
    # Assemble the system prompt
    system_message = MULTI_STEP_DENOISE_PROMPT.format(
        date=get_today_str(), 
        max_concurrent_research_units=max_concurrent_researchers,
        max_researcher_iterations=max_researcher_iterations
    )
    messages = [SystemMessage(content=system_message)] + supervisor_messages
 
    # Dynamic context injection: check for and inject any unaddressed adversarial feedback to enable self-correction.
    critiques = state.get("active_critiques", [])
    unaddressed = [c for c in critiques if not c.addressed]
    if unaddressed:
        critique_text = "\n".join([f"- {c.author} says: {c.concern}" for c in unaddressed])
        intervention = SystemMessage(content=ADDRESS_CRITIQUES_PROMPT.format(critique_text=critique_text))
        messages.append(intervention)

    # Remind the supervisor if the quality score was low in the previous iteration
    if state.get("needs_quality_repair"):
        messages.append(SystemMessage(content="The previous draft report scored low on quality (below 7/10). Please continue improving it."))

    # Decide which tool to call
    response = await supervisor_model_with_tools.ainvoke(messages)
    logger.info(
        "supervisor model produced tool_calls=%s num_tool_calls=%d",
        bool(response.tool_calls),
        len(response.tool_calls or []),
    )
 
    # Jump to supervisor_tools
    return Command(
        goto="supervisor_tools", # optional since we add the edge alerady
        update={
            "supervisor_messages": [response],
            "research_iterations": iteration + 1,
            "needs_quality_repair": False # Reset the repair flag after reminding the supervisor
        }
    )


async def supervisor_tools(state: SupervisorState) -> Command[Literal["supervisor", "__end__"]]:
    """
    Execute the supervisor's decision — continue with another round of research or end the process.

    Responsibilities:
        - Execute think_tool calls for reflection
        - Launch research agents for different topics in parallel
        - Aggregate research results
        - Determine when the research is complete

    Args:
        state: Contains the supervisor messages and iteration count

    Returns:
        Command to continue with the next supervisor round or end the process
    """
    supervisor_messages = state.get("supervisor_messages", [])
    research_iterations = state.get("research_iterations", 0)
    most_recent_message = supervisor_messages[-1]

    # Check whether we reached the max iterations or whether the supervisor produced tool calls
    exceeded_iterations = research_iterations >= max_researcher_iterations
    no_tool_calls = not most_recent_message.tool_calls
    research_complete = any(
        tool_call["name"] == "ResearchComplete" 
        for tool_call in most_recent_message.tool_calls
    )

    # Exit if any termination condition is met
    if exceeded_iterations or no_tool_calls or research_complete:
        # When the exit conditions are met, prepare the final, curated notes.
        # Prefer the structured knowledge base, but fall back to raw notes if it is empty.
        final_notes = get_notes_from_tool_calls(state.get("supervisor_messages", []))
        logger.info("[REPORT] The research is complete, writing the final report.")

        # Return END to finish this subgraph and pass the final notes along.
        return Command(
                goto=END,
                update={
                    "notes": final_notes,
                    "research_brief": state.get("research_brief", "")
        })

    else:
        # Initialize variables
        tool_messages = []
        all_raw_notes = []
        draft_report = state.get("draft_report", "")
        updates = {}
        next_step = "supervisor"

        # Execute all tool calls
        try:
            think_tool_calls = [
                tool_call for tool_call in most_recent_message.tool_calls 
                if tool_call["name"] == "think_tool"
            ]

            conduct_research_calls = [
                tool_call for tool_call in most_recent_message.tool_calls 
                if tool_call["name"] == "ConductResearch"
            ]

            refine_report_calls = [
                tool_call for tool_call in most_recent_message.tool_calls 
                if tool_call["name"] == "refine_draft_report"
            ]

            logger.info(
                "[SUPERVISOR] supervisor_tools executing think=%d conduct=%d refine=%d",
                len(think_tool_calls),
                len(conduct_research_calls),
                len(refine_report_calls),
            )

            # Invoke the think tool (reflection results must be obtained before calling other tools) (synchronous)
            for tool_call in think_tool_calls:
                observation = think_tool.invoke(tool_call["args"])
                tool_messages.append(
                    ToolMessage(
                        content=observation,
                        name=tool_call["name"],
                        tool_call_id=tool_call["id"]
                    )
                )

            # Invoke the ConductResearch tool (asynchronous)
            if conduct_research_calls:
                # Launch multiple research agents in parallel
                coros = [
                    researcher_agent.ainvoke({
                        "researcher_messages": [
                            HumanMessage(content=tool_call["args"]["research_topic"])
                        ],
                        "research_topic": tool_call["args"]["research_topic"]
                    }) 
                    for tool_call in conduct_research_calls
                ]

                # Wait for all research agents to return their results
                tool_results = await asyncio.gather(*coros)

                # Format the research results as tool messages
                # Each research agent returns its compressed research in result["compressed_research"]
                # We write these compressed results into the ToolMessage content so that
                # the supervisor agent can retrieve them via get_notes_from_tool_calls()
                research_tool_messages = [
                    ToolMessage(
                        content=result.get("compressed_research", "Error synthesizing research report"),
                        name=tool_call["name"],
                        tool_call_id=tool_call["id"]
                    ) for result, tool_call in zip(tool_results, conduct_research_calls)
                ]

                tool_messages.extend(research_tool_messages)

                # Aggregate all raw notes
                all_raw_notes = [
                    "\n".join(result.get("raw_notes", [])) 
                    for result in tool_results
                ]

            # Call the LLM to revise the research report using the information gathered so far
            for tool_call in refine_report_calls: 
                findings = "\n".join(get_notes_from_tool_calls(state.get("supervisor_messages", [])))

                new_draft = refine_draft_report_tool.invoke({
                    "research_brief": state.get("research_brief", ""),
                    "findings": findings,
                    "draft_report": state.get("draft_report", "")
                })
                
                # Critical step: run the self-evolution evaluation
                eval_result = evaluate_draft_quality(
                        research_brief=state.get("research_brief", ""),
                        draft_report=new_draft
                )
                logger.info(
                    "[EVALUATOR] comprehensive score=%f, accuracy score=%f, coherence score=%f",
                    eval_result.comprehensiveness_score,
                    eval_result.accuracy_score,
                    eval_result.coherence_score
                )
                logger.info(f"[EVALUATOR] scoing reason: {eval_result.reason}") 

                # Report quality score: (comprehensiveness + accuracy + coherence) / 3
                avg_score = (eval_result.comprehensiveness_score + eval_result.accuracy_score + eval_result.coherence_score) / 3
                
                # Append the quality score to the tool message for the supervisor agent's reference
                tool_messages.append(ToolMessage(
                    content=f"Draft Updated.\nQuality Score: {avg_score}/10.\nJudge Feedback: {eval_result.reason}",
                    name=tool_call["name"],
                    tool_call_id=tool_call["id"]
                ))

                draft_report = new_draft
                updates["draft_report"] = draft_report
                
                # Record the quality score; if it is below min_need_repair_score, set the repair flag to true
                updates["quality_history"] = [QualityMetric(
                    score=avg_score,
                    feedback=eval_result.reason,
                    iteration=state.get("research_iterations", 0))
                ]

                if avg_score < min_need_repair_score:
                    updates["needs_quality_repair"] = True

                # Jump to the self-correction node (Red Team)
                next_step = "red_team"

            # Update the state for this iteration
            updates["supervisor_messages"] = tool_messages
            updates["raw_notes"] = all_raw_notes
            
            return Command(goto=next_step, update=updates)

        except Exception as e:
            return Command(
                goto=END,
                update={
                    "notes": get_notes_from_tool_calls(supervisor_messages),
                    "research_brief": state.get("research_brief", "")
                }
            )



# ===== GRAPH CONSTRUCTION =====

supervisor_builder = StateGraph(SupervisorState)
supervisor_builder.add_node("supervisor", supervisor)
supervisor_builder.add_node("supervisor_tools", supervisor_tools)
supervisor_builder.add_node("red_team", red_team_node)

supervisor_builder.add_edge(START, "supervisor")
supervisor_builder.add_edge("supervisor", "supervisor_tools")
supervisor_builder.add_edge("red_team", "supervisor")

supervisor_agent = supervisor_builder.compile()


if __name__ == "__main__":
    print(supervisor_agent.get_graph().draw_ascii())
