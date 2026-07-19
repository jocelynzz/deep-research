"""Final instruction for the research-compression step.

This prompt is appended as the LAST message of the compression call, after the
researcher agent's full transcript (searches, tool results, reflections). The
message order is:

    [SystemMessage: COMPRESS_RESEARCH_SYSTEM_PROMPT]   <- job description
    [...researcher transcript...]                       <- material to compress
    [HumanMessage: this prompt]                         <- "now do it, for THIS topic"

It is sent with the "user" role (LangChain's HumanMessage) because chat models
respond to the last user-role message — no actual human writes it. Its job is to
re-anchor the research topic and restate the must-not-lose-information rules
right before generation, where the model attends most reliably.

Template variable: {research_topic} — the topic delegated by the supervisor.
"""

COMPRESS_RESEARCH_FINAL_INSTRUCTION_PROMPT = """All of the above information concerns research conducted by an AI researcher on the following research topic:
Research topic: {research_topic}

Your task is to clean up these research findings while preserving all information relevant to answering this specific research question.

Critical requirements:
- Do NOT summarize or paraphrase the information - preserve it verbatim
- Do NOT omit any details, facts, names, numbers, or specific findings
- Do NOT filter out information that appears relevant to the research topic
- Organize the information in a cleaner format, but keep all of the substance
- Include all sources and citations found during the research
- Remember that this research was conducted to answer the specific question above

The cleaned-up findings will be used to generate the final report, so completeness is critical."""
