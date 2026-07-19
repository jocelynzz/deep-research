#***********************************************
#      Filename: state_draft.py
#***********************************************

"""Define the state of draft, including state management and the schemas of input and output
"""

import operator
from typing_extensions import Optional, Annotated, List, Sequence

from langchain_core.messages import BaseMessage
from langgraph.graph import MessagesState
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field


# ===== STATE DEFINITIONS =====

class AgentInputState(MessagesState):
    pass

class AgentState(MessagesState):
    research_brief: Optional[str] # written by write_research_brief
    supervisor_messages: Annotated[Sequence[BaseMessage], add_messages] #supervisor's own chat history
    raw_notes: Annotated[list[str], operator.add] = []
    notes: Annotated[list[str], operator.add] = [] # processed notes that can be used to generate the report
    draft_report: str
    final_report: str

# ===== STRUCTURED OUTPUT SCHEMAS =====
class ResearchBrief(BaseModel):
    research_brief: str = Field(description="A research question that will be used to guide the research.")

class DraftReport(BaseModel):
    draft_report: str = Field(description="A draft report that will be used to guide the research.",)