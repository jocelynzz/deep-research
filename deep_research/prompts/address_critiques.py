"""Instruction for the supervisor to address red-team critiques.

Injected into the supervisor's conversation when the Red Team (RED_TEAM_PROMPT)
finds problems in the draft report. It presents the critiques and directs the
supervisor to the right tool for each kind of problem: ConductResearch for
missing information, think_tool for flawed logic, refine_draft_report for
draft quality.

Template variable: {critique_text} — the critiques produced by the Red Team.
"""

ADDRESS_CRITIQUES_PROMPT = """The adversarial team detected the following problems in your draft:
{critique_text}

You need to try to address these problems in your next step:
1. If a critique points out missing information, call "ConductResearch" to find and gather more information.
2. If a critique points out flawed logic, call "think_tool" to work out a repair plan.
3. If a critique points out that the draft report needs improvement, call "refine_draft_report" to refine the draft.
"""
