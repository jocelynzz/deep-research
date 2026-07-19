# Deep Research

`Deep Research` is a personal, experimental multi-agent research workflow. It turns a broad question into a research brief, delegates focused web research, compresses evidence, challenges a draft with a red-team pass, evaluates report quality, and produces a final synthesis.

It is inspired by the broader wave of agentic research products, including [OpenAI deep research](https://openai.com/index/introducing-deep-research/), [Gemini Deep Research](https://blog.google/innovation-and-ai/models-and-research/gemini-models/next-generation-gemini-deep-research/), and [Perplexity Deep Research](https://research.perplexity.ai/articles/evaluating-deep-research-performance-in-the-wild-with-the-draco-benchmark). This is an independent personal project, not affiliated with or endorsed by any of those companies.

## What it does

1. Converts a user question into a structured research brief and initial draft.
2. Uses a supervisor to split the work into bounded, parallel research topics.
3. Searches the web through a pluggable search-provider layer (Tavily by default), summarizes long pages, and compresses the findings.
4. Refines the draft, runs an adversarial red-team critique, and scores completeness, accuracy, and coherence before the final writer produces the report.

The design follows the useful pattern behind modern deep-research systems: plan, search, assess sources, refine, synthesize, and make the output reviewable. It remains experimental—generated reports and their sources should always be checked by a person before they are used for important decisions.

## Architecture

```text
Question
  -> brief + draft
  -> supervisor
  -> parallel research agents -> web search -> page summaries -> compressed notes
  -> report refinement -> red-team critique + quality evaluation
  -> final report
```

## Setup

This project targets Python 3.11+.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
cp config.example.yml config.yml
```

Add your own values to the untracked `.env` file:

```dotenv
OPENAI_API_KEY=...
TAVILY_API_KEY=...
# Optional observability
LANGSMITH_API_KEY=...
```

`config.yml` and `.env` are intentionally ignored by Git. The checked-in templates contain placeholders only; `${OPENAI_API_KEY}` and `${TAVILY_API_KEY}` in the configuration are resolved from your environment. LangSmith tracing is optional; when `LANGSMITH_API_KEY` is set, the project enables tracing automatically.

## Running and extending

The compiled LangGraph workflow lives in `deep_research/tools/agent_builder.py`. The repository currently exposes the graph as a library component, making it straightforward to embed in a notebook, CLI, or web application. To inspect the graph:

```bash
python -m deep_research.tools.agent_builder
```

The default per-researcher tool budget is three calls. Adjust it in `.env` when experimenting:

```dotenv
MAX_RESEARCH_TOOL_CALLS=5
```

Search providers are extensible through `deep_research/providers/`; see `customsearch.py` for the expected interface.

## Security

Never commit API keys, access tokens, or generated reports containing sensitive information. If a secret is ever committed or exposed, revoke and rotate it with the provider immediately.

## Project status

This is a learning and experimentation project. APIs, prompts, models, and workflow behavior may change as the system evolves.
