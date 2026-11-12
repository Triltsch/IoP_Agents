# Woche 3: Frameworks – LangGraph, MCP und LLM

[🇬🇧 English](README.md) · **🇩🇪 Deutsch**

Das Fabrikszenario wird als zustandsbehafteter LangGraph-Workflow neu aufgebaut. Die Telemetrie kommt über das Model Context Protocol (MCP), die Entscheidung des Koordinators trifft ein LLM.

## Notebooks (Ordner `en` und `de`)

| Notebook | Thema |
|---|---|
| `01_LangGraph_Agents_solution` | Zustandsgraph, Knoten, bedingte Kanten; Abbildung Mesa → LangGraph; MCP-Konzept |
| `02_MCP_LLM_solution` | MCP-Server (FastAPI, JSON-RPC 2.0) und -Client, LLM-Koordinator als **Stub** (ohne API-Key), Vollintegration LangGraph + MCP + LLM |
| `03_MCP_LLM_API_solution` | Wie 02, aber mit **echter LLM-API** (OpenAI `gpt-4.1-mini`; Anthropic-Variante als Kommentar). Benötigt `OPENAI_API_KEY` |

## Hinweise

- Die Notebooks 02 und 03 starten den MCP-Server auf Port 8766 in einem Hintergrund-Thread. Starten Sie den Kernel neu, bevor Sie eines davon erneut ausführen.
- Schreiben Sie nie einen API-Key in ein Notebook. Setzen Sie ihn als Umgebungsvariable, bevor Sie Jupyter starten (`export OPENAI_API_KEY='sk-...'`).
