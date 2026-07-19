REFINE_DRAFT_REPORT_PROMPT = """Based on the completed research and the draft report, please write a comprehensive, well-structured answer to the following research 
  brief:

  <research_brief>
  {research_brief}
  </research_brief>

  IMPORTANT: Make sure the answer is written in the same language as the user's input!
  For example, if the user's input is in English, be sure to reply in English. If the user's input is in Chinese, be sure to reply in Chinese.
  This is critical. The user can only understand the answer if it is written in the same language as their input.

  Today's date is {date}.

  Here is the draft report:
  <draft_report>
  {draft_report}
  </draft_report>

  Here are the findings from the research you conducted:
  <findings>
  {findings}
  </findings>

  Please write a detailed report answering the overall research brief that:
  1. Is well-organized with proper headings (# for the title, ## for sections, ### for subsections)
  2. Includes specific facts and insights from the research
  3. Cites relevant sources using the [Title](URL) format
  4. Provides a balanced, comprehensive analysis. Be as comprehensive as possible, and include all information relevant to the overall research question. People expect
  deep research and want a detailed, comprehensive answer.
  5. Ends with a "Sources" section listing all cited links

  You can structure the report in many different ways. Here are some examples:

  To answer a question that asks you to compare two things, you might structure your report like this:
  1/ Introduction
  2/ Overview of Topic A
  3/ Overview of Topic B
  4/ Comparison of A and B
  5/ Conclusion

  To answer a question that asks you to produce a list of things, you might only need a single section containing the entire list.
  1/ A list or table of the things
  Alternatively, you could make each item in the list its own section of the report. When asked for a list, you don't need an introduction or conclusion.
  1/ Item 1
  2/ Item 2
  3/ Item 3

  To answer a question that asks you to summarize a topic, deliver a report, or give an overview, you might structure your report like this:
  1/ Overview of the topic
  2/ Concept 1
  3/ Concept 2
  4/ Concept 3
  5/ Conclusion

  If you think one section is enough to answer the question, you can do that too!
  1/ Answer

  Remember: sections are a very flexible and loose concept. You can structure the report however you judge best, including in ways not listed above!
  Make sure your sections flow logically and are easy for the reader to follow.

  For each section of the report, do the following:
  - Use clear and concise language
  - Preserve important details from the research findings
  - Use ## for each section heading (Markdown format)
  - Never refer to yourself as the author of the report. This is a professional report and should not contain any self-referential language.
  - Do not describe what you are doing in the report. Just write the report without any personal commentary.
  - Each section should be long enough to thoroughly answer the question with the information you've gathered. It is normal for sections to be fairly long and 
  detailed. You are writing an in-depth research report, and the reader expects a thorough answer.
  - Use bullet points where appropriate to list information, but default to writing in paragraph form.

  Remember:
  The brief and research materials may be in English, but you need to translate that information into the correct language when writing the final answer.
  Make sure the final report is written in the same language as the human messages in the message history.
  Format the report in clear Markdown with proper structure, and include references where appropriate.

  <citation_rules>
  - Assign each unique URL a citation number in the body text
  - End with "### Sources" listing each source with its corresponding number
  - IMPORTANT: Number the sources sequentially with no gaps (1, 2, 3, 4...), regardless of which sources you choose
  - Put each source on its own line so it renders as a list in Markdown
  - Example format:
  [1] Source Title: URL
  [2] Source Title: URL
  - Citations are extremely important. Always include citations and take care to get them right. Users often rely on them to find more information.
  </citation_rules>
  """
