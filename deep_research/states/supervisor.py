#***********************************************
#      Filename: state_supervisor.py
#   Description: Structured field definitions for the Supervisor agent
#***********************************************

"""
State definition for the multi-agent Supervisor.
This file defines the State object and tool field definitions used in the multi-agent Supervisor workflow.
"""

import operator
from typing_extensions import Annotated, Sequence, TypedDict, List

from langchain_core.messages import BaseMessage
from langchain_core.tools import tool
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

from deep_research.states.critique import Critique
from deep_research.states.quality import QualityMetric


class SupervisorState(TypedDict):
    """
    State definition for the multi-agent Supervisor.
    Coordinates the work between the Supervisor and Research Agents, tracking research progress and aggregating research results from multiple sub-agents.
    """
    # typed dict, so properties below are keys
    supervisor_messages: Annotated[Sequence[BaseMessage], add_messages] # Supervisor messages, used for coordination and passing information
    research_brief: str                                                 # Detailed research brief that guides the overall research direction
    notes: Annotated[list[str], operator.add] = []                      # Processed and structured notes that can be used to generate the final report
    research_iterations: int = 0                                        # Counter tracking the number of research iterations
    critique_nums: int = 0                                              # Counter tracking the number of red-team critiques
    raw_notes: Annotated[list[str], operator.add] = []                  # Raw, unprocessed research notes collected from sub-agent research
    draft_report: str                                                   # The draft report
    active_critiques: Annotated[List[Critique], operator.add]           # Holds critiques that are still active (not yet addressed)
    quality_history: Annotated[List[QualityMetric], operator.add]       # History of quality evaluations
    needs_quality_repair: bool                                          # Flag the evaluator can set to signal to the supervisor that the draft report quality is low

@tool
class ConductResearch(BaseModel):
    """Tool for delegating a research task to a specialized sub-agent."""
    research_topic: str = Field(
        description="The research topic. Each delegated task should cover a single topic, described in detail (at least one paragraph).",
    )

@tool
class ResearchComplete(BaseModel):
    """Tool for indicating that the research process is complete."""
    pass
