import logging

from typing_extensions import Annotated, Optional, Literal
from typing import List
from deep_research.llm import get_chat_model
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool, InjectedToolArg
from deep_research.utils import get_today_str
from deep_research.states import Summary
from deep_research.prompts import SUMMARIZE_PROMPT, REFINE_DRAFT_REPORT_PROMPT
from deep_research.tools.search_factory import SearchConfigError, get_search_client, get_search_provider, get_search_defaults

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
summarization_model = get_chat_model("researcher_summarizer")
writer_model = get_chat_model("writer")
MAX_CONTEXT_LENGTH = 250000
DEFAULT_MAX_CONTEXT = 1000
search_provider = None
search_client = None
search_defaults = None

# ==== Research Tools ==== #
def tavily_search(
        query: str,
        max_results: Annotated[Optional[int], InjectedToolArg] = None,
        topic: Annotated[Optional[Literal["general", "technology", "news", "finance"]], InjectedToolArg] = None):
    """Run a web search and return de-duplicated, summarized results.

    Args:
        query: Search query.
        max_results: Max number of results returned, default is 3.
        topic: Search topic, default is general.

    Returns:
        De-duplicated and cleaned search results.
    """
    _, _, defaults = _ensure_search_runtime()
    if defaults is None:
        raise SearchConfigError("Search defaults unavailable; search runtime not initialized")
    resolved_max_results = max_results if max_results is not None else defaults.get("max_results", 3)
    resolved_topic = topic if topic is not None else defaults.get("topic", "general")
    include_raw_content = defaults.get("include_raw_content", True)
    search_results = _tavily_search_multiple(
        [query],  # 转换成列表
        max_results=resolved_max_results,
        topic=resolved_topic,
        include_raw_content=include_raw_content,
    )
    # dedup the result
    unique_results = _deduplicate_search_results(search_results)

    # create summary for the results
    summarized_results = _process_search_results(unique_results)

    # format the search result
    return _format_search_output(summarized_results)
def think_tool(reflection: str) -> str:
    """Record a reflection on research progress to guide next steps.

    Args:
        reflection: The reflection or reasoning to record.

    Returns:
        Confirmation that the reflection was recorded.
    """
    return f"Reflection recorded: {reflection}"

def refine_draft_report(research_brief: Annotated[str, InjectedToolArg],
                        findings: Annotated[str, InjectedToolArg],
                        draft_report: Annotated[str, InjectedToolArg]):
    """Refine the draft report based on the research brief and findings.

    Args:
        research_brief: The research brief describing the research goal.
        findings: The accumulated research findings.
        draft_report: The current draft report to refine.

    Returns:
        The refined report content.
    """
    draft_report_prompt = REFINE_DRAFT_REPORT_PROMPT.format(
        research_brief=research_brief,
        findings=findings,
        draft_report=draft_report,
        date=get_today_str()
    )
    draft_report_obj = writer_model.invoke([HumanMessage(content=draft_report_prompt)])
    return getattr(draft_report_obj, "content", draft_report_obj)

# ==== Register Tools ==== #
tavily_search_tool = tool(parse_docstring=True)(tavily_search)
think_tool = tool(parse_docstring=True)(think_tool)
refine_draft_report_tool = tool(parse_docstring=True)(refine_draft_report)

# ==== Search functions ==== #
def _deduplicate_search_results(search_results: List[dict]) -> dict:
    unique_results = {}
    for response in search_results:
        for result in response['results']:
            url = result['url']
            if url not in unique_results:
                unique_results[url]=result
    return unique_results

def _process_search_results(unique_results: dict) -> dict:
    summarized_results = {}
    for url, result in unique_results.items():
        if not result.get("raw_content"):
            content = result['content']
        else:
            content = _summarize_webpage_content(result['raw_content'])
        summarized_results[url] = {
            'title': result['title'],
            'content': content
        }
    return summarized_results

def _summarize_webpage_content(webpage_content: str) -> str:
    try:
        structured_model = summarization_model.with_structured_output(Summary)
        summary = structured_model.invoke([
            HumanMessage(content=SUMMARIZE_PROMPT.format(
                webpage_content=webpage_content,
                date=get_today_str()
            ))
        ])

        formatted_summary = (
            f"<summary>\n{summary.summary}\n</summary>\n\n"
            f"<key_excerpts>\n{summary.key_excerpts}\n</key_excerpts>"
        )
        return formatted_summary
    except Exception as e:
        logger.error(f"Failed to summarize webpage: {str(e)}")
        return webpage_content[:DEFAULT_MAX_CONTEXT] + "..."

def _format_search_output(summarized_results: dict) -> str:
    if not summarized_results:
        return "No valid search results found. Please try different search queries or use a different search API."

    formatted_output = "Search results: \n\n"

    for i, (url, result) in enumerate(summarized_results.items(), 1):
        formatted_output += f"\n\n--- SOURCE {i}: {result['title']} ---\n"
        formatted_output += f"URL: {url}\n\n"
        formatted_output += f"SUMMARY:\n{result['content']}\n\n"
        formatted_output += "-" * 80 + "\n"

    return formatted_output

def _tavily_search_multiple(
        search_queries: List[str],
        max_results: Optional[int] = 3,
        topic: Optional[Literal["general", "news", "finance"]]="general",
        include_raw_content: Optional[bool]=True,
        client=None,
        provider=None,
        defaults=None,
        timeout_seconds: Optional[int] = None,
) -> List[dict]:
    provider, client, defaults_paramaters = _resolve_search_runtime(client, provider, defaults)
    if provider is None or client is None or defaults_paramaters is None:
        logger.error(
            "Search runtime not initialized (provider=%s, client=%s, defaults=%s)",
            bool(provider),
            bool(client),
            bool(defaults_paramaters),
        )
        raise SearchConfigError("Search runtime unavailable: provider/client/defaults could not be resolved")

    effective_max_results = max_results if max_results is not None else defaults_paramaters.get("max_results", 3)
    effective_topic = topic if topic is not None else defaults_paramaters.get("topic", "general")
    effective_include_raw = include_raw_content if include_raw_content is not None else True
    effective_timeout = timeout_seconds if timeout_seconds is not None else defaults_paramaters.get("timeout_seconds")

    search_docs = []
    for query in search_queries:
        try:
            result = provider.search(
                client,
                query,
                max_results=effective_max_results,
                include_raw_content=effective_include_raw,
                topic=effective_topic,
                timeout_seconds=effective_timeout,
            )
        except _TIMEOUT_EXCEPTIONS as exc:
            logger.error(
                "Search timeout for query='%s' topic='%s' timeout=%s: %s",
                query,
                effective_topic,
                effective_timeout,
                exc,
            )
            raise
        except Exception as exc:
            logger.error(
                "Search execution failed for query='%s' backend topic='%s': %s",
                query,
                effective_topic,
                exc,
            )
            raise

        search_docs.append(result)

    return search_docs

def _resolve_search_runtime(client=None, provider=None, defaults=None, *, raise_on_error: bool = True):
    runtime_provider, runtime_client, runtime_defaults = _ensure_search_runtime(raise_on_error=raise_on_error)
    resolved_provider = provider or runtime_provider
    resolved_client = client or runtime_client
    resolved_defaults = defaults or runtime_defaults

    return resolved_provider, resolved_client, resolved_defaults

def _ensure_search_runtime(raise_on_error: bool=True):
    global search_provider, search_client, search_defaults
    try:
        if search_provider is None:
            logger.debug("Resolving search provider")
            search_provider = get_search_provider()
        if search_client is None:
            logger.debug("Resolving search client")
            search_client = get_search_client()
        if search_defaults is None:
            logger.debug("Resolving search defaults")
            search_defaults = get_search_defaults()
    except SearchConfigError as e:
        logger.error(f"Search runtime initialization failed '{e}'")
        if raise_on_error:
            raise
    except Exception as exception:
        logger.error(f"Unexpected error during search runtime init '{exception}'")
        if raise_on_error:
            raise
    return search_provider, search_client, search_defaults

try:
    import requests
    _REQUESTS_TIMEOUT_EXC = (requests.exceptions.Timeout,)
except Exception:
    _REQUESTS_TIMEOUT_EXC = tuple()

try:
    import httpx
    _HTTPX_TIMEOUT_EXC = (httpx.TimeoutException,)
except Exception:
    _HTTPX_TIMEOUT_EXC = tuple()

_TIMEOUT_EXCEPTIONS = (TimeoutError,) + _REQUESTS_TIMEOUT_EXC + _HTTPX_TIMEOUT_EXC
