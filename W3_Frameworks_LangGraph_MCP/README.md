# Week 3: frameworks – LangGraph, MCP and LLM

**🇬🇧 English** · [🇩🇪 Deutsch](README.de.md)

The factory scenario is rebuilt as a stateful LangGraph workflow. Telemetry is fetched through the Model Context Protocol (MCP), and the coordinator decision is made by an LLM.

## Notebooks (folders `en` and `de`)

| Notebook | Topic |
|---|---|
| `01_LangGraph_Agents_solution` | State graph, nodes, conditional edges; mapping Mesa → LangGraph; MCP concept |
| `02_MCP_LLM_solution` | MCP server (FastAPI, JSON-RPC 2.0) and client, LLM coordinator as **stub** (no API key), full integration LangGraph + MCP + LLM |
| `03_MCP_LLM_API_solution` | As 02, but with a **real LLM API** (OpenAI `gpt-4.1-mini`; Anthropic variant as comment). Needs `OPENAI_API_KEY` |

## Notes

- Notebooks 02 and 03 start the MCP server on port 8766 in a background thread. Restart the kernel before running one of them again.
- Never write an API key into a notebook. Set it as environment variable before you start Jupyter (`export OPENAI_API_KEY='sk-...'`).
