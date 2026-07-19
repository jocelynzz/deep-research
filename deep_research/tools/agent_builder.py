#***********************************************
#      Filename: agent_builder.py
#   Description: Multi-agent deep research builder
#***********************************************


from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END

from deep_research.utils import get_today_str
from deep_research.states import AgentState, AgentInputState
from deep_research.prompts import FINAL_REPORT_PROMPT
from deep_research.agents.draft_agent import write_research_brief, write_draft_report
from deep_research.agents import supervisor_agent
from deep_research.llm import get_chat_model


# ===== Config =====

writer_model = get_chat_model("writer")


# ===== FINAL REPORT GENERATION =====

async def final_report_generation(state: AgentState):
    """Generate the final report: user query, research brief, findings, draft report => report
    """

    # Collect all the notes
    notes = state.get("notes", [])
    findings = "\n".join(notes)

    # Assemble the prompt
    final_report_prompt = FINAL_REPORT_PROMPT.format(
        research_brief=state.get("research_brief", ""),
        findings=findings,
        date=get_today_str(),
        draft_report=state.get("draft_report", "")
    )

    # Generate the final report
    final_report = await writer_model.ainvoke([HumanMessage(content=final_report_prompt)])

    return {
        "final_report": final_report.content,
        "messages": ["Final report: " + final_report.content],
    }


# ===== GRAPH CONSTRUCTION =====

# Build the deep-research workflow
deep_researcher_builder = StateGraph(AgentState, input_schema=AgentInputState)

# Add nodes
deep_researcher_builder.add_node("write_research_brief", write_research_brief)
deep_researcher_builder.add_node("write_draft_report", write_draft_report)
deep_researcher_builder.add_node("supervisor_subgraph", supervisor_agent)
deep_researcher_builder.add_node("final_report_generation", final_report_generation)

# Add edges
deep_researcher_builder.add_edge(START, "write_research_brief")
deep_researcher_builder.add_edge("write_research_brief", "write_draft_report")
deep_researcher_builder.add_edge("write_draft_report", "supervisor_subgraph")
deep_researcher_builder.add_edge("supervisor_subgraph", "final_report_generation")
deep_researcher_builder.add_edge("final_report_generation", END)

# Compile the graph
agent = deep_researcher_builder.compile()


if __name__ == "__main__":
    print(agent.get_graph(xray=True).draw_ascii())
