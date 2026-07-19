#***********************************************
#      Filename: critique.py
#   Description: Output of Critique Agent
#***********************************************

from pydantic import BaseModel, Field


class Critique(BaseModel):
    """Structured model for receiving adversarial feedback from the "Red Team" or other quality-control agents"""

    # Tracks which agent produced the critique (e.g., "Red Team", "Safety Filter") for accountability.
    author: str

    # The specific logical fallacy, bias, or factual error found in the draft report.
    concern: str

    # Flag tracking whether the critique has been addressed in a subsequent draft revision
    addressed: bool = Field(default=False, description="Has the supervisor fixed this?")
