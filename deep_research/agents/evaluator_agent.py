#***********************************************
#      Filename: evaluator_agent.py
#   Description: Report evaluation agent
#***********************************************

from langchain_core.messages import HumanMessage

from deep_research.llm import get_chat_model
from deep_research.states import EvaluationResult
from deep_research.prompts import DRAFT_EVALUATOR_PROMPT


# Initialize the judge model
judge_model = get_chat_model("evaluator")


def evaluate_draft_quality(research_brief: str, draft_report: str) -> EvaluationResult:
    """
    Implements the "self-evolution" scoring mechanism: uses another LLM as a judge to
    evaluate the quality of the draft report against the original brief.
    The scores and their reasons are returned to the supervisor agent.
    """

    # Assemble the prompt
    eval_prompt = DRAFT_EVALUATOR_PROMPT.format(
            research_brief = research_brief,
            draft_report = draft_report
    )

    # Get structured score results (multi-dimensional scoring)
    structured_judge = judge_model.with_structured_output(EvaluationResult)

    return structured_judge.invoke([HumanMessage(content=eval_prompt)])
