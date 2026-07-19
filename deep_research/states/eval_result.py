#***********************************************
#      Filename: eval_result.py
#   Description: Structured output for report evaluation results
#***********************************************

from pydantic import BaseModel, Field

class EvaluationResult(BaseModel):

    # Comprehensiveness score: 0-10 measuring whether all aspects of the brief are covered
    comprehensiveness_score: int = Field(description="0-10 score on coverage")

    # Accuracy score: measures whether the report is factually grounded
    accuracy_score: int = Field(description="0-10 score on factual grounding")

    # Coherence score: measures whether the report has logical flaws, and whether it flows well and is readable
    coherence_score: int = Field(description="0-10 score on flow")

    # Reason for the scores, used to improve report quality
    reason: str = Field(
        description="Concise feedback for the researcher, written in the same language as the draft report"
    )
