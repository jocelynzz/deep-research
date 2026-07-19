RESEARCH_BRIEF_PROMPT = """You will be given a set of messages exchanged so far between yourself and the user. Your job is to translate these messages into a more detailed and concrete research question that will be used to guide the research.
The messages exchanged so far between yourself and the user are as follows:
<messages>
{messages}
</messages>
IMPORTANT: Make sure the answer is written in the same language as the user's messages!
For example, if the user's messages are in English, be sure to reply in English. 
This is critical. The user can only understand the answer if it is written in the same language as their input.

Today's date is {date}.
You will return a single research question that will be used to guide the research.
Guidelines:
1. Maximize Specificity and Detail
- Include all known user preferences and explicitly list key attributes or dimensions to consider.
- It is important that all details from the user are included in the instructions.

2. Handle Unstated Dimensions Carefully
- When research quality requires considering additional dimensions that the user hasn't specified, acknowledge them as open considerations rather than assumed preferences.
- Example: instead of assuming "budget-friendly options," say "consider all price ranges unless cost constraints are specified."
- Only mention dimensions that are genuinely necessary for comprehensive research in that domain.

3. Avoid Unwarranted Assumptions
- Never invent specific user preferences, constraints, or requirements that the user hasn't stated.
- If the user hasn't provided a particular detail, explicitly note this lack of specification.
- Guide the researcher to treat unspecified aspects as flexible rather than making assumptions.

4. Distinguish Between Research Scope and User Preferences
- Research scope: what topics/dimensions should be investigated (can be broader than what the user explicitly mentioned)
- User preferences: specific constraints, requirements, or preferences (must only include what the user explicitly stated)
- Example: "Research coffee quality factors for coffee shops in San Francisco (including bean sourcing, roasting methods, brewing techniques), with primary focus on the taste preferences specified by the user."

5. Use the First Person
- Phrase the request from the user's perspective.

6. Sources
- If specific sources should be prioritized, specify them in the research question.
- For product and travel research, prefer linking directly to official or primary websites (e.g., official brand sites, manufacturer pages, or reputable e-commerce platforms like Amazon for user reviews) rather than aggregator sites or SEO-heavy blogs.
- For academic or scientific research, prefer linking directly to the original paper or official journal article rather than survey papers or secondhand summaries.
- For people, try linking directly to their Wikipedia/LinkedIn profile, or their personal website if they have one.
- If the query is in a specific language, prioritize sources published in that language.

Remember:
Make sure the research brief is written in the same language as the user's messages in the message history.
"""