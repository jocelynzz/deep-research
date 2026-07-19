SUMMARIZE_PROMPT = """You are tasked with summarizing the raw content of a webpage retrieved from a web search. Your goal is to create a summary that preserves the 
most important information from the original webpage. This summary will be used by downstream researchers, so it is crucial to preserve all key details without 
losing essential information.

Here is the raw content of the webpage:                                                                                       
<webpage_content>
{webpage_content}
</webpage_content>

Please follow these guidelines to create your summary:
1. Identify and preserve the main topic or purpose of the webpage.                                                            
2. Preserve key facts, statistics, and data points that are central to the content's message.
3. Preserve important quotes from credible sources or experts.
4. Maintain the chronological order of events if the content is time-sensitive or historical.
5. Preserve any lists or step-by-step instructions if present.
6. Include relevant dates, names, and locations that are crucial to understanding the content.
7. Summarize lengthy explanations while keeping the core message intact.

When handling different types of content:
- News articles: focus on the who, what, when, where, why, and how.
- Scientific content: preserve methodology, results, and conclusions.
- Opinion pieces: preserve the main arguments and supporting points.
- Product pages: preserve key features, specifications, and unique selling points.

Your summary should be significantly shorter than the original content but comprehensive enough to stand alone as a source of information. Aim for about 25-30 
percent of the original length, unless the content is already concise.

Present your summary in the following format:

{{
    "summary": "Your summary here, structured with appropriate paragraphs or bullet points as needed",
    "key_excerpts": "First important quote or excerpt, Second important quote or excerpt, Third important quote or excerpt, ...Add more excerpts as needed, up to a
    maximum of 5"
}}

Here are two examples of good summaries:

Example 1 (for a news article):
```json
{{
    "summary": "On July 15, 2023, NASA successfully launched the Artemis II mission from Kennedy Space Center. This is the first crewed mission to the Moon since Apollo
    17 in 1972. The four-person crew, led by Commander Jane Smith, will orbit the Moon for 10 days before returning to Earth. The mission is a key step in NASA's plan to
    establish a permanent human presence on the Moon by 2030.",
    
    "key_excerpts": "NASA Administrator John Doe said the Artemis II mission marks the dawn of a new era of space exploration. Chief engineer Sarah Johnson explained
    that the mission will test critical systems needed for future long-term stays on the Moon. 'We're not just going back to the Moon, we're going forward to the Moon,'
    Commander Jane Smith said at the pre-launch press conference."
  }}

Example 2 (for a scientific article):
{{
    "summary": "A new study published in Nature Climate Change shows that global sea levels are rising faster than previously thought. Researchers analyzed satellite 
    data from 1993 to 2022 and found that the rate of sea level rise has accelerated by 0.08 mm/year² over the past three decades. This acceleration is mainly attributed
    2100, posing significant risks to coastal communities worldwide.",
    
    "key_excerpts": "Lead author Dr. Emily Brown said: 'Our findings show a clear acceleration in sea level rise, which has important implications for coastal planning 
    and adaptation strategies.' The study reports that the melting rate of the Greenland and Antarctic ice sheets has tripled since the 1990s. Co-author Professor 
    Michael Green warned that without immediate and substantial reductions in greenhouse gas emissions, we face catastrophic sea level rise by the end of this century."
}}

Remember, your goal is to create a summary that is easy for downstream researchers to understand and use, while preserving the most critical information from the
original webpage.

Today's date is {date}.
"""
