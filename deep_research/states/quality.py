#***********************************************
#      Filename: quality.py
#   Description: Structured output for quality control
#***********************************************

from typing_extensions import TypedDict, Annotated, List, Sequence

class QualityMetric(TypedDict):
    """A TypedDict storing a snapshot of the draft report's quality at a specific iteration"""

    # Quality score computed by our self-evolution evaluator
    score: float

    # Text feedback from the evaluator explaining the score
    feedback: str

    # The iteration at which this score was recorded, used to track progress over time
    iteration: int
